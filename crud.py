"""Acceso a datos. Las rutas no ejecutan SQL directo."""

from collections import OrderedDict
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

import models
import schemas
from config import get_settings


class EmailAlreadyRegisteredError(Exception):
    """Email único violado a nivel de motor."""


class InsufficientStockError(Exception):
    def __init__(self, product_name: str, available: int, requested: int):
        self.product_name = product_name
        self.available = available
        self.requested = requested


class MissingProductsError(Exception):
    def __init__(self, product_ids: list[int]):
        self.product_ids = product_ids


def unit_price_with_discount(list_price: float) -> float:
    """Descuento porcentual si el precio supera el umbral configurado."""
    settings = get_settings()
    if list_price > settings.discount_threshold:
        discounted = list_price * (1 - settings.discount_rate)
        return round(max(discounted, 0.0), 2)
    return round(list_price, 2)


def create_user(db: Session, payload: schemas.UserCreate) -> models.User:
    entity = models.User(name=payload.name, email=payload.email)
    db.add(entity)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise EmailAlreadyRegisteredError() from None
    db.refresh(entity)
    return entity


def create_product(db: Session, payload: schemas.ProductCreate) -> models.Product:
    entity = models.Product(
        name=payload.name, price=payload.price, stock=payload.stock
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def list_products(db: Session, limit: int, offset: int) -> list[models.Product]:
    """Catálogo paginado: OFFSET/LIMIT se aplican en SQL, no en memoria."""
    return (
        db.query(models.Product)
        .order_by(models.Product.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_admin_snapshot(db: Session) -> dict:
    """Construye los indicadores administrativos desde datos persistidos."""
    recent_orders = (
        db.query(models.Order)
        .options(joinedload(models.Order.user), selectinload(models.Order.items))
        .order_by(models.Order.created_at.desc(), models.Order.id.desc())
        .limit(6)
        .all()
    )
    return {
        "users_count": db.query(func.count(models.User.id)).scalar() or 0,
        "products_count": db.query(func.count(models.Product.id)).scalar() or 0,
        "orders_count": db.query(func.count(models.Order.id)).scalar() or 0,
        "revenue": db.query(func.coalesce(func.sum(models.Order.total_price), 0.0)).scalar() or 0.0,
        "stock_units": db.query(func.coalesce(func.sum(models.Product.stock), 0)).scalar() or 0,
        "low_stock_count": db.query(func.count(models.Product.id)).filter(models.Product.stock <= 5).scalar() or 0,
        "users": db.query(models.User).order_by(models.User.id.desc()).limit(8).all(),
        "products": db.query(models.Product).order_by(models.Product.id.desc()).limit(8).all(),
        "recent_orders": recent_orders,
    }


def get_user_order_history(
    db: Session, user_id: int
) -> Optional[list[schemas.UserOrderHistoryOut]]:
    """Historial con JOIN explícito User → Order → OrderItem → Product.

    Si el usuario no existe el JOIN no produce filas y se devuelve None (404).
    Si existe pero no tiene pedidos, el LEFT JOIN entrega una fila con Order nulo.
    """
    rows = (
        db.query(models.User, models.Order, models.Product.name)
        .select_from(models.User)
        .join(models.Order, models.Order.user_id == models.User.id, isouter=True)
        .join(
            models.OrderItem,
            models.OrderItem.order_id == models.Order.id,
            isouter=True,
        )
        .join(
            models.Product,
            models.Product.id == models.OrderItem.product_id,
            isouter=True,
        )
        .filter(models.User.id == user_id)
        .order_by(models.Order.created_at.desc(), models.Order.id.asc())
        .all()
    )

    if not rows:
        return None

    grouped: OrderedDict[int, schemas.UserOrderHistoryOut] = OrderedDict()
    for _user, order, product_name in rows:
        if order is None:
            continue
        if order.id not in grouped:
            grouped[order.id] = schemas.UserOrderHistoryOut(
                id=order.id,
                user_id=order.user_id,
                total_price=order.total_price,
                created_at=order.created_at,
                product_names=[],
            )
        if product_name is not None:
            grouped[order.id].product_names.append(product_name)

    return list(grouped.values())


def create_order(db: Session, payload: schemas.OrderCreate) -> models.Order:
    """Checkout con lock de stock, descuento y rollback en el caller HTTP."""
    user = (
        db.query(models.User)
        .options(joinedload(models.User.orders))
        .filter(models.User.id == payload.user_id)
        .first()
    )
    if not user:
        raise LookupError("user")

    product_ids = {item.product_id for item in payload.items}
    products = (
        db.query(models.Product)
        .filter(models.Product.id.in_(product_ids))
        .with_for_update()
        .all()
    )
    products_by_id = {product.id: product for product in products}

    missing = product_ids - products_by_id.keys()
    if missing:
        raise MissingProductsError(sorted(missing))

    new_order = models.Order(user_id=user.id, total_price=0.0)
    db.add(new_order)
    db.flush()

    total = 0.0
    for line in payload.items:
        product = products_by_id[line.product_id]
        if product.stock < line.quantity:
            raise InsufficientStockError(
                product.name, product.stock, line.quantity
            )

        unit_price = unit_price_with_discount(product.price)
        total += unit_price * line.quantity
        product.stock -= line.quantity
        db.add(
            models.OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=line.quantity,
                unit_price=unit_price,
            )
        )

    new_order.total_price = round(total, 2)
    db.commit()

    return (
        db.query(models.Order)
        .options(
            joinedload(models.Order.user),
            selectinload(models.Order.items).joinedload(models.OrderItem.product),
        )
        .filter(models.Order.id == new_order.id)
        .one()
    )
