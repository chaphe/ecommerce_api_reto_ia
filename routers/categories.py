"""Categorías persistentes del catálogo."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import auth
import crud
import database
import models
import schemas

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=schemas.CategoryListOut)
def list_categories(
    db: Session = Depends(database.get_db),
    search: str | None = None,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_categories(db, search, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{category_id}/products", response_model=schemas.ProductListOut)
def category_products(
    category_id: int,
    db: Session = Depends(database.get_db),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_products_admin(db, None, category_id, False, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/", response_model=schemas.CategoryOut, status_code=201)
def create_category(payload: schemas.CategoryCreate, admin: auth.AdminUser, csrf: auth.Csrf, db: Session = Depends(database.get_db)):
    try:
        return crud.create_category(db, payload)
    except crud.DuplicateProductError:
        raise HTTPException(status_code=409, detail="El slug de categoría ya existe") from None


@router.patch("/{category_id}", response_model=schemas.CategoryOut)
def update_category(category_id: int, payload: schemas.CategoryUpdate, admin: auth.AdminUser, csrf: auth.Csrf, db: Session = Depends(database.get_db)):
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    try:
        return crud.update_category(db, category, payload)
    except crud.DuplicateProductError:
        raise HTTPException(status_code=409, detail="El slug de categoría ya existe") from None
