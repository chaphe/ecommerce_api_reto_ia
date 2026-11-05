"""Vistas server-rendered para el storefront."""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import crud
import auth
import database
from config import get_settings

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


@router.get("/", include_in_schema=False)
def catalog(request: Request, db: Session = Depends(database.get_db)):
    settings = get_settings()
    products = crud.list_products(db, limit=100, offset=0)
    return templates.TemplateResponse(
        "catalog.html",
        {
            "request": request,
            "products": products,
            "discount_threshold": settings.discount_threshold,
            "discount_rate": settings.discount_rate,
        },
    )


@router.get("/orders", include_in_schema=False)
def orders_history(request: Request):
    return templates.TemplateResponse("orders.html", {"request": request})


@router.get("/login", include_in_schema=False)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "mode": "login"})


@router.get("/register", include_in_schema=False)
def register_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "mode": "register"})


@router.get("/profile", include_in_schema=False)
def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})


@router.get("/admin", include_in_schema=False)
def admin_dashboard(request: Request, admin: auth.AdminUser, db: Session = Depends(database.get_db)):
    snapshot = crud.get_admin_snapshot(db)
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, **snapshot},
    )
