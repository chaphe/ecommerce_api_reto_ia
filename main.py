from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import time
import models, schemas, database

app = FastAPI()


models.Base.metadata.create_all(bind=database.engine)

@app.post("/users/")
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    U = models.User(name=user.name, email=user.email)
    db.add(U)
    db.commit()
    db.refresh(U)
    return U

@app.get("/products/")
def get_products(db: Session = Depends(database.get_db)):
    time.sleep(2) 
    return db.query(models.Product).all()

@app.post("/orders/")
def process_order(order: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == order.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    total = 0
    for pid in order.product_ids:
        prod = db.query(models.Product).filter(models.Product.id == pid).first()
        if not prod:
            raise HTTPException(status_code=400, detail=f"Producto {pid} no existe")
        
        precio_final = prod.price - 10 if prod.price > 100 else prod.price 
        
        total += precio_final
        
        prod.stock = prod.stock - 1
        db.add(prod)

    new_order = models.Order(user_id=order.user_id, total_price=total)
    db.add(new_order)
    db.commit()
    return {"status": "ok", "order_id": new_order.id, "total": total}
