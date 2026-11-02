from collections import Counter

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas, database

app = FastAPI()

DISCOUNT_THRESHOLD = 100
DISCOUNT_RATE = 0.10


models.Base.metadata.create_all(bind=database.engine)

def apply_discount(price: float) -> float:
    """Aplica un 10 % de descuento a los productos que cuestan más de 100."""
    if price > DISCOUNT_THRESHOLD:
        return round(price * (1 - DISCOUNT_RATE), 2)
    return price

@app.post("/users/")
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    U = models.User(name=user.name, email=user.email)
    db.add(U)
    db.commit()
    db.refresh(U)
    return U

@app.get("/products/")
def get_products(db: Session = Depends(database.get_db)):
    return db.query(models.Product).all()

@app.post("/orders/")
def process_order(order: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == order.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    quantities = Counter(order.product_ids)
    # FOR UPDATE bloquea las filas hasta el commit para que dos pedidos simultáneos
    # no descuenten el mismo stock; ordenar por id evita interbloqueos entre pedidos.
    products = (
        db.query(models.Product)
        .filter(models.Product.id.in_(list(quantities)))
        .order_by(models.Product.id)
        .with_for_update()
        .all()
    )
    products_by_id = {prod.id: prod for prod in products}
    for pid in quantities:
        if pid not in products_by_id:
            raise HTTPException(status_code=400, detail=f"Producto {pid} no existe")

    total = 0
    items = []
    for prod in products:
        quantity = quantities[prod.id]
        if prod.stock < quantity:
            raise HTTPException(status_code=409, detail=f"Stock insuficiente para el producto {prod.id}")

        final_price = apply_discount(prod.price)
        total += final_price * quantity
        prod.stock -= quantity
        items.append(models.OrderItem(product_id=prod.id, quantity=quantity, unit_price=final_price))

    new_order = models.Order(user_id=order.user_id, total_price=total, items=items)
    db.add(new_order)
    db.commit()
    return {"status": "ok", "order_id": new_order.id, "total": total}
