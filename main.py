from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import time

import models
import schemas
import database
from config import settings

app = FastAPI()


if settings.environment == "dev" and settings.create_tables:
    models.Base.metadata.create_all(bind=database.engine)


@app.post("/users/")
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email ya registrado")
    
    try:
        db_user = models.User(name=user.name, email=user.email)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear usuario")


@app.get("/products/")
def get_products(db: Session = Depends(database.get_db)):
    return db.query(models.Product).all()


@app.post("/orders/")
def process_order(order: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == order.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    try:
        product_ids = [item.product_id for item in order.items]
        products = db.query(models.Product).filter(models.Product.id.in_(product_ids)).all()
        products_map = {prod.id: prod for prod in products}
        
        for item in order.items:
            if item.product_id not in products_map:
                raise HTTPException(status_code=400, detail=f"Producto {item.product_id} no existe")
            
            prod = products_map[item.product_id]
            if prod.stock < item.quantity:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente para producto {item.product_id}")
        
        total = 0
        for item in order.items:
            prod = products_map[item.product_id]
            precio_final = prod.price - 10 if prod.price > 100 else prod.price
            total += precio_final * item.quantity
            prod.stock = prod.stock - item.quantity
        
        new_order = models.Order(user_id=order.user_id, total_price=total)
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        return {"status": "ok", "order_id": new_order.id, "total": total}
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar orden")


