from pydantic import BaseModel
from typing import List, Optional

class UserCreate(BaseModel):
    name: str
    email: str

class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int

class OrderCreate(BaseModel):
    user_id: int
    product_ids: List[int] # PROBLEMA: No permite especificar cantidades por producto
