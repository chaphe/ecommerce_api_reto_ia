from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import time
import models, schemas, database

app = FastAPI()

# Inicializar tablas (En producción debería usarse Alembic)
models.Base.metadata.create_all(bind=database.engine)

@app.post("/users/")
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    # VIOLACIÓN DE PEP 8 Y MALAS PRÁCTICAS DE NOMBRES
    U = models.User(name=user.name, email=user.email)
    db.add(U)
    db.commit()
    db.refresh(U)
    return U

@app.get("/products/")
def get_products(db: Session = Depends(database.get_db)):
    # CUELLO DE BOTELLA / RENDIMIENTO INTENCIONAL:
    # Simula un procesamiento pesado bloqueante en el event loop de FastAPI
    time.sleep(2) 
    return db.query(models.Product).all()

@app.post("/orders/")
def process_order(order: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == order.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    total = 0
    # CUELLO DE BOTELLA N+1 SELECT: Consulta dentro de un ciclo for
    for pid in order.product_ids:
        prod = db.query(models.Product).filter(models.Product.id == pid).first()
        if not prod:
            raise HTTPException(status_code=400, detail=f"Producto {pid} no existe")
        
        # ERROR DE REGLA DE NEGOCIO #1: No verifica si el stock es suficiente (stock >= 1)
        # ERROR DE REGLA DE NEGOCIO #2: Descuento mal calculado (resta en lugar de aplicar porcentaje)
        # Si el precio es > 100 aplica "10" de descuento fijo en lugar del 10%
        precio_final = prod.price - 10 if prod.price > 100 else prod.price 
        
        total += precio_final
        
        # ERROR DE CONCURRENCIA / REGLA DE NEGOCIO: Modifica stock sin transacción atómica ni bloqueo
        prod.stock = prod.stock - 1
        db.add(prod)

    new_order = models.Order(user_id=order.user_id, total_price=total)
    db.add(new_order)
    db.commit()
    return {"status": "ok", "order_id": new_order.id, "total": total}

# FALTA TOTALMENTE:
# 1. Manejo global de excepciones.
# 2. Documentación de endpoints (docstrings).
# 3. Tests unitarios (pytest).
# 4. Dockerfile / docker-compose.yml.
