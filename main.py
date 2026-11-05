"""Composición de la API y de la interfaz web."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import database
import models
import auth
from config import get_settings
from routers import admin_users, auth as auth_router, categories, orders, products, users, web

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
    {"name": "auth", "description": "Registro y sesiones protegidas."},
    {"name": "admin-users", "description": "Gestión e importación masiva de usuarios para administradores."},
    {"name": "categories", "description": "Categorías y subcategorías persistentes del catálogo."},
    {"name": "products-admin", "description": "Gestión comercial, importación y exportación de productos."},
    {"name": "orders-admin", "description": "Operación y estados de órdenes comerciales."},
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


def _bootstrap_admin() -> None:
    settings = get_settings()
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return
    with database.SessionLocal() as db:
        if db.query(models.User).filter(models.User.role == "admin").first():
            return
        db.add(
            models.User(
                name="Initial administrator",
                email=settings.bootstrap_admin_email.strip().lower(),
                password_hash=auth.hash_password(settings.bootstrap_admin_password),
                role="admin",
                is_active=True,
            )
        )
        db.commit()


_bootstrap_admin()

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(users.router)
app.include_router(auth_router.router)
app.include_router(admin_users.router)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(web.router)
