"""Composición de la API y de la interfaz web."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import database
import models
from routers import orders, products, users, web

BASE_DIR = Path(__file__).resolve().parent

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

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(users.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(web.router)
