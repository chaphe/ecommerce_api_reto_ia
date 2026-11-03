"""Rutas de checkout."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import crud
import database
import schemas

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "/",
    response_model=schemas.OrderOut,
    summary="Procesar una orden de compra",
    response_description="Orden confirmada con líneas, precios unitarios y total",
    tags=["orders"],
    responses={
        **schemas.OPENAPI_ERROR_RESPONSES,
        409: {
            "model": schemas.ErrorResponse,
            "description": "Stock insuficiente para alguna línea del carrito",
        },
    },
)
def process_order(
    order: schemas.OrderCreate, db: Session = Depends(database.get_db)
):
    """Ejecuta el checkout en una sola transacción.

    Bloquea filas de producto (`SELECT … FOR UPDATE`), aplica descuento
    porcentual si el precio supera el umbral y descuenta stock por cantidad.
    Cualquier error dispara `rollback` para no dejar stock ni totales a medias.
    """
    try:
        return crud.create_order(db, order)
    except LookupError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except crud.MissingProductsError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Productos inexistentes: {exc.product_ids}",
        )
    except crud.InsufficientStockError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                f"Stock insuficiente para '{exc.product_name}' "
                f"(disponible={exc.available}, solicitado={exc.requested})"
            ),
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar la orden")
