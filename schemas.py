"""Contratos Pydantic de entrada, salida y errores OpenAPI."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ===== Usuarios =====
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=100)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str = "buyer"
    is_active: bool = True


class UserListOut(BaseModel):
    items: List[UserOut]
    total: int
    limit: int
    offset: int


class RegisterIn(UserCreate):
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class AdminUserCreate(UserCreate):
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="buyer", pattern="^(admin|buyer)$")


class AdminUserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    email: Optional[str] = Field(default=None, min_length=3, max_length=100)
    role: Optional[str] = Field(default=None, pattern="^(admin|buyer)$")
    is_active: Optional[bool] = None


class UserProfileUpdate(BaseModel):
    """Edicion de perfil propio. Se mapea a AdminUserUpdate(**payload.model_dump())."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    email: Optional[str] = Field(default=None, min_length=3, max_length=100)


class ImportUserRow(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="buyer", pattern="^(admin|buyer)$")


class ImportPreviewOut(BaseModel):
    valid_rows: List[ImportUserRow]
    errors: List[str]
    duplicates: List[str]


class ImportResultOut(BaseModel):
    created: int = 0
    skipped: int = 0
    errors: List[str] = Field(default_factory=list)


# ===== Productos =====
class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sku: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    image_url: Optional[str] = Field(default=None, max_length=500)
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    category_id: Optional[int] = Field(default=None, gt=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    sku: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    image_url: Optional[str] = Field(default=None, max_length=500)
    price: Optional[float] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)
    category_id: Optional[int] = None
    is_archived: Optional[bool] = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    sku: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    price: float
    stock: int
    category_id: Optional[int] = None
    is_archived: bool = False


class ProductListOut(BaseModel):
    items: List[ProductOut]
    total: int
    limit: int
    offset: int


class BulkProductChange(BaseModel):
    product_ids: List[int] = Field(min_length=1)
    price: Optional[float] = Field(default=None, gt=0)
    stock_delta: Optional[int] = None
    category_id: Optional[int] = None
    is_archived: Optional[bool] = None


class ProductImportRow(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sku: Optional[str] = Field(default="", max_length=64)
    price: float = Field(gt=0)
    stock: int = Field(default=0, ge=0)
    description: Optional[str] = None
    image_url: Optional[str] = Field(default=None, max_length=500)
    category_slug: Optional[str] = Field(default=None, max_length=80)


class ProductImportPreviewOut(BaseModel):
    valid_rows: List[ProductImportRow]
    errors: List[str]
    duplicates: List[str]


# ===== Categorias =====
class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    slug: str = Field(min_length=1, max_length=80)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    slug: Optional[str] = Field(default=None, min_length=1, max_length=80)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str


class CategoryListOut(BaseModel):
    items: List[CategoryOut]
    total: int
    limit: int
    offset: int


# ===== Ordenes =====
class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItemIn] = Field(min_length=1)


class GuestOrderCreate(BaseModel):
    items: List[OrderItemIn] = Field(min_length=1)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    quantity: int
    unit_price: float
    product_name: Optional[str] = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: Optional[int] = None
    total_price: float
    created_at: datetime
    items: List[OrderItemOut]
    status: str = "confirmed"
    is_archived: bool = False
    cancelled_at: Optional[datetime] = None


class OrderListOut(BaseModel):
    items: List[OrderOut]
    total: int
    limit: int
    offset: int


class OrderUpdate(BaseModel):
    status: Optional[str] = Field(
        default=None,
        pattern="^(confirmed|processing|shipped|completed|cancelled)$",
    )
    is_archived: Optional[bool] = None
    cancellation_reason: Optional[str] = Field(default=None, max_length=255)


# ===== Errores =====
class ErrorResponse(BaseModel):
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
    400: {"model": ErrorResponse400, "description": "Solicitud invalida o recurso relacionado inexistente"},
    404: {"model": ErrorResponse404, "description": "El recurso solicitado no existe"},
    500: {"model": ErrorResponse500, "description": "Fallo interno no controlado; la transaccion se revierte"},
}


# ===== Historial =====
class UserOrderHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
    id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    total_price: float = Field(ge=0)
    created_at: datetime
    product_names: List[str] = Field(min_length=0)