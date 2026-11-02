from pydantic import BaseModel, EmailStr, Field
from typing import List


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    email: EmailStr


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    stock: int = Field(ge=0)


class OrderItem(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, default=1)


class OrderCreate(BaseModel):
    user_id: int = Field(gt=0)
    items: List[OrderItem] = Field(min_length=1)


