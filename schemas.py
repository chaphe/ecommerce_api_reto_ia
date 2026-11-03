"""Contratos Pydantic de entrada, salida y errores OpenAPI."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=100)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    stock: int = Field(ge=0)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: float
    stock: int


class OrderItemIn(BaseModel):
    """Una línea del carrito: producto + cantidad (ya no un id suelto)."""

    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItemIn] = Field(min_length=1)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    quantity: int
    unit_price: float


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    total_price: float
    created_at: datetime
    items: List[OrderItemOut]


class ErrorResponse(BaseModel):
    """Cuerpo estándar de error HTTP documentado en Swagger."""

    detail: str = Field(..., description="Mensaje de error interpretable por el cliente")


class ErrorResponse400(ErrorResponse):
    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "Productos inexistentes: [99]"}}
    )


class ErrorResponse404(ErrorResponse):
    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "Usuario no encontrado"}}
    )


class ErrorResponse500(ErrorResponse):
    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "Error al procesar la orden"}}
    )


OPENAPI_ERROR_RESPONSES = {
    400: {
        "model": ErrorResponse400,
        "description": "Solicitud inválida o recurso relacionado inexistente",
    },
    404: {
        "model": ErrorResponse404,
        "description": "El recurso solicitado no existe",
    },
    500: {
        "model": ErrorResponse500,
        "description": "Fallo interno no controlado; la transacción se revierte",
    },
}


class UserOrderHistoryOut(BaseModel):
    """Historial de un pedido: metadatos + nombres exactos de productos."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    total_price: float = Field(ge=0)
    created_at: datetime
    product_names: List[str] = Field(min_length=0)
