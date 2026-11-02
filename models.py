from sqlalchemy import CheckConstraint, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    email = Column(String(100)) # PROBLEMA: Sin restricción unique=True ni validación

    orders = relationship("Order", back_populates="user")

class Product(Base):
    __tablename__ = "products"
    # MySQL aplica CHECK desde la 8.0.16; create_all no lo añade a tablas que ya existen
    __table_args__ = (CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),)
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    price = Column(Float)
    stock = Column(Integer)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_price = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.now) # PROBLEMA: Debería usar utcnow

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    # Precio unitario ya con descuento, tal como se cobró en la compra
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
