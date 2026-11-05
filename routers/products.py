"""Rutas de catálogo."""

import asyncio

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import crud
import database
import schemas

router = APIRouter(prefix="/products", tags=["products"])


@router.post(
    "/",
    response_model=schemas.ProductOut,
    summary="Dar de alta un producto",
    response_description="SKU creado con stock y precio de lista",
    tags=["products"],
    responses=schemas.OPENAPI_ERROR_RESPONSES,
)
def create_product(
    product: schemas.ProductCreate, db: Session = Depends(database.get_db)
):
    """Registra un producto en el catálogo.

    `price` debe ser mayor que cero y `stock` no negativo. El identificador
    lo asigna la base de datos.
    """
    return crud.create_product(db, product)


@router.get(
    "/",
    response_model=list[schemas.ProductOut],
    summary="Listar productos paginados",
    response_description="Página del catálogo según limit y offset",
    tags=["products"],
    responses=schemas.OPENAPI_ERROR_RESPONSES,
)
def get_products(
    db: Session = Depends(database.get_db),
    limit: int = Query(10, ge=1, le=100, description="Tamaño de página (máx. 100)"),
    offset: int = Query(0, ge=0, description="Registros a saltar"),
):
    """Lista el catálogo con paginación SQL (`LIMIT` / `OFFSET`)."""
    return crud.list_products(db, limit=limit, offset=offset)
