"""Composición de la API. La lógica vive en routers y crud."""

from fastapi import FastAPI

import database
import models
from routers import orders, products, users

OPENAPI_TAGS = [
    {
        "name": "users",
        "description": "Alta de clientes e historial de pedidos por usuario.",
    },
    {
        "name": "products",
        "description": "Catálogo paginado y alta de SKUs (precio y stock).",
    },
    {
        "name": "orders",
        "description": "Checkout transaccional: descuento, lock de stock y rollback.",
    },
]

app = FastAPI(
    title="Ecommerce API",
    description=(
        "API REST de comercio electrónico: usuarios, catálogo y órdenes. "
        "Documentación interactiva en `/docs` (Swagger UI) y `/redoc` (ReDoc). "
        "El esquema OpenAPI está en `/openapi.json`."
    ),
    version="1.0.0",
    contact={"name": "Ecommerce API — Ingeniería de Software"},
    openapi_tags=OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
)

models.Base.metadata.create_all(bind=database.engine)

app.include_router(users.router)
app.include_router(products.router)
app.include_router(orders.router)
