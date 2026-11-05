"""Rutas de checkout."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, selectinload

import crud
import auth
import database
import schemas
import models

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_out(order: models.Order) -> models.Order:
    return order


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
    order: schemas.OrderCreate,
    user: auth.CurrentUser,
    csrf: auth.Csrf,
    db: Session = Depends(database.get_db),
):
    """Ejecuta el checkout en una sola transacción.

    Bloquea filas de producto (`SELECT … FOR UPDATE`), aplica descuento
    porcentual si el precio supera el umbral y descuenta stock por cantidad.
    Cualquier error dispara `rollback` para no dejar stock ni totales a medias.
    """
    try:
        if order.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="No puedes crear pedidos para otro usuario")
        return crud.create_order(db, order, user_id=user.id)
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


@router.post("/guest", response_model=schemas.OrderOut)
def process_guest_order(order: schemas.GuestOrderCreate, db: Session = Depends(database.get_db)):
    try:
        return crud.create_order(db, order)
    except crud.MissingProductsError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Productos inexistentes: {exc.product_ids}") from None
    except crud.InsufficientStockError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Stock insuficiente para '{exc.product_name}'") from None
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar la orden") from None


@router.get("/mine", response_model=schemas.OrderListOut)
def my_orders(
    user: auth.CurrentUser,
    db: Session = Depends(database.get_db),
    status: str | None = Query(default=None, pattern="^(confirmed|processing|shipped|completed|cancelled)$"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_orders(db, None, status, False, user.id, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/admin", response_model=schemas.OrderListOut, tags=["orders-admin"])
def admin_orders(
    admin: auth.AdminUser,
    db: Session = Depends(database.get_db),
    search: str | None = None,
    status: str | None = Query(default=None, pattern="^(confirmed|processing|shipped|completed|cancelled)$"),
    include_archived: bool = False,
    user_id: int | None = Query(default=None, gt=0),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_orders(db, search, status, include_archived, user_id, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{order_id}", response_model=schemas.OrderOut)
def order_detail(order_id: int, user: auth.CurrentUser, db: Session = Depends(database.get_db)):
    order = db.query(models.Order).options(
        joinedload(models.Order.user),
        selectinload(models.Order.items),
    ).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if user.role != "admin" and order.user_id != user.id:
        raise HTTPException(status_code=403, detail="No puedes consultar esta orden")
    return order


@router.patch("/{order_id}", response_model=schemas.OrderOut, tags=["orders-admin"])
def update_order(
    order_id: int,
    payload: schemas.OrderUpdate,
    admin: auth.AdminUser,
    csrf: auth.Csrf,
    db: Session = Depends(database.get_db),
):
    order = (
        db.query(models.Order)
        .filter(models.Order.id == order_id)
        .with_for_update()
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if order.status == "cancelled" and payload.status not in (None, "cancelled"):
        raise HTTPException(status_code=409, detail="Una orden cancelada no puede reactivarse")
    if payload.status == "cancelled" and order.status in ("shipped", "completed"):
        raise HTTPException(status_code=409, detail="Una orden enviada o completada no puede cancelarse")
    return crud.update_order(db, order, payload)
