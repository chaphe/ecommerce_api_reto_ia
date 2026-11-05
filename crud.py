"""Acceso a datos. Las rutas no ejecutan SQL directo."""

from collections import OrderedDict
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

import models
import schemas
import auth
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


class DuplicateProductError(Exception):
    """SKU already exists."""


def create_authenticated_user(
    db: Session, payload: schemas.RegisterIn | schemas.AdminUserCreate, role: str = "buyer"
) -> models.User:
    entity = models.User(
        name=payload.name,
        email=payload.email.strip().lower(),
        password_hash=auth.hash_password(payload.password),
        role=getattr(payload, "role", role),
        is_active=True,
    )
    db.add(entity)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise EmailAlreadyRegisteredError() from None
    db.refresh(entity)
    return entity


def create_authenticated_users_bulk(db: Session, payloads: list[schemas.ImportUserRow]) -> int:
    entities = [
        models.User(
            name=payload.name,
            email=payload.email.strip().lower(),
            password_hash=auth.hash_password(payload.password),
            role=payload.role,
            is_active=True,
        )
        for payload in payloads
    ]
    db.add_all(entities)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise EmailAlreadyRegisteredError() from None
    return len(entities)


def find_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email.strip().lower()).first()


def list_users(db: Session, search: str | None, role: str | None, is_active: bool | None, limit: int, offset: int):
    query = db.query(models.User)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter((models.User.name.ilike(term)) | (models.User.email.ilike(term)))
    if role:
        query = query.filter(models.User.role == role)
    if is_active is not None:
        query = query.filter(models.User.is_active == is_active)
    total = query.count()
    return total, query.order_by(models.User.id.desc()).offset(offset).limit(limit).all()


def update_user(db: Session, user: models.User, payload: schemas.AdminUserUpdate) -> models.User:
    values = payload.model_dump(exclude_unset=True)
    if "email" in values:
        values["email"] = values["email"].strip().lower()
    for key, value in values.items():
        setattr(user, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise EmailAlreadyRegisteredError() from None
    db.refresh(user)
    return user


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
        name=payload.name,
        sku=payload.sku,
        description=payload.description,
        image_url=payload.image_url,
        price=payload.price,
        stock=payload.stock,
        category_id=payload.category_id,
    )
    db.add(entity)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateProductError() from None
    db.refresh(entity)
    return entity


def create_products_bulk(
    db: Session,
    payloads: list[schemas.ProductCreate],
) -> int:
    entities = [models.Product(**payload.model_dump()) for payload in payloads]
    db.add_all(entities)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateProductError() from None
    return len(entities)


def list_products_admin(
    db: Session,
    search: str | None,
    category_id: int | None,
    include_archived: bool,
    limit: int,
    offset: int,
):
    query = db.query(models.Product)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (models.Product.name.ilike(term)) | (models.Product.sku.ilike(term))
        )
    if category_id is not None:
        query = query.filter(models.Product.category_id == category_id)
    if not include_archived:
        query = query.filter(models.Product.is_archived.is_(False))
    total = query.count()
    return total, query.order_by(models.Product.id.desc()).offset(offset).limit(limit).all()


def update_product(db: Session, product: models.Product, payload: schemas.ProductUpdate) -> models.Product:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateProductError() from None
    db.refresh(product)
    return product


def duplicate_product(db: Session, product: models.Product, sku: str | None = None) -> models.Product:
    copy = models.Product(
        name=f"{product.name} (copia)",
        sku=sku,
        description=product.description,
        image_url=product.image_url,
        price=product.price,
        stock=product.stock,
        category_id=product.category_id,
    )
    db.add(copy)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateProductError() from None
    db.refresh(copy)
    return copy


def bulk_update_products(db: Session, payload: schemas.BulkProductChange) -> int:
    products = (
        db.query(models.Product)
        .filter(models.Product.id.in_(payload.product_ids))
        .with_for_update()
        .all()
    )
    if len(products) != len(set(payload.product_ids)):
        raise MissingProductsError(sorted(set(payload.product_ids) - {p.id for p in products}))
    for product in products:
        if payload.price is not None:
            product.price = payload.price
        if payload.stock_delta is not None:
            next_stock = product.stock + payload.stock_delta
            if next_stock < 0:
                raise InsufficientStockError(product.name, product.stock, abs(payload.stock_delta))
            product.stock = next_stock
        if payload.category_id is not None:
            product.category_id = payload.category_id
        if payload.is_archived is not None:
            product.is_archived = payload.is_archived
    db.commit()
    return len(products)


def list_categories(db: Session, search: str | None, limit: int, offset: int):
    query = db.query(models.Category)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (models.Category.name.ilike(term)) | (models.Category.slug.ilike(term))
        )
    total = query.count()
    return total, query.order_by(models.Category.name.asc()).offset(offset).limit(limit).all()


def create_category(db: Session, payload: schemas.CategoryCreate) -> models.Category:
    category = models.Category(**payload.model_dump())
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateProductError() from None
    db.refresh(category)
    return category


def update_category(db: Session, category: models.Category, payload: schemas.CategoryUpdate) -> models.Category:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateProductError() from None
    db.refresh(category)
    return category


def list_orders(
    db: Session,
    search: str | None,
    status: str | None,
    include_archived: bool,
    user_id: int | None,
    limit: int,
    offset: int,
):
    query = db.query(models.Order).options(
        joinedload(models.Order.user),
        selectinload(models.Order.items),
    )
    if search and search.isdigit():
        query = query.filter(models.Order.id == int(search))
    if status:
        query = query.filter(models.Order.status == status)
    if not include_archived:
        query = query.filter(models.Order.is_archived.is_(False))
    if user_id is not None:
        query = query.filter(models.Order.user_id == user_id)
    total = query.count()
    return total, query.order_by(models.Order.created_at.desc()).offset(offset).limit(limit).all()


def update_order(db: Session, order: models.Order, payload: schemas.OrderUpdate) -> models.Order:
    values = payload.model_dump(exclude_unset=True)
    if values.get("status") == "cancelled" and order.status != "cancelled":
        products = {
            product.id: product
            for product in db.query(models.Product)
            .filter(models.Product.id.in_([item.product_id for item in order.items]))
            .with_for_update()
            .all()
        }
        for item in order.items:
            if item.product_id in products:
                products[item.product_id].stock += item.quantity
    if values.get("status") == "cancelled":
        order.cancelled_at = order.cancelled_at or models._utc_now()
    for key, value in values.items():
        setattr(order, key, value)
    db.commit()
    db.refresh(order)
    return order


def list_products(db: Session, limit: int, offset: int) -> list[models.Product]:
    """Catálogo paginado: OFFSET/LIMIT se aplican en SQL, no en memoria."""
    return (
        db.query(models.Product)
        .filter(models.Product.is_archived.is_(False))
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
        "orders_count": db.query(func.count(models.Order.id)).filter(
            models.Order.status != "cancelled", models.Order.is_archived.is_(False)
        ).scalar() or 0,
        "revenue": db.query(func.coalesce(func.sum(models.Order.total_price), 0.0)).filter(
            models.Order.status != "cancelled", models.Order.is_archived.is_(False)
        ).scalar() or 0.0,
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
        db.query(models.User, models.Order, models.OrderItem.product_name, models.Product.name)
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
    for _user, order, snapshot_name, product_name in rows:
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
        resolved_name = snapshot_name or product_name
        if resolved_name is not None:
            grouped[order.id].product_names.append(resolved_name)

    return list(grouped.values())


def create_order(db: Session, payload: schemas.OrderCreate | schemas.GuestOrderCreate, user_id: int | None = None) -> models.Order:
    """Checkout con lock de stock, descuento y rollback en el caller HTTP."""
    user = (
        db.query(models.User)
        .options(joinedload(models.User.orders))
        .filter(models.User.id == (user_id if user_id is not None else getattr(payload, "user_id", None)))
        .first()
    ) if user_id is not None or hasattr(payload, "user_id") else None
    if hasattr(payload, "user_id") and not user:
        raise LookupError("user")

    product_ids = {item.product_id for item in payload.items}
    products = (
        db.query(models.Product)
        .filter(models.Product.id.in_(product_ids), models.Product.is_archived.is_(False))
        .with_for_update()
        .all()
    )
    products_by_id = {product.id: product for product in products}

    missing = product_ids - products_by_id.keys()
    if missing:
        raise MissingProductsError(sorted(missing))

    new_order = models.Order(user_id=user.id if user else None, total_price=0.0)
    db.add(new_order)
    db.flush()

    total = 0.0
    quantities: dict[int, int] = {}
    for line in payload.items:
        quantities[line.product_id] = quantities.get(line.product_id, 0) + line.quantity

    for product_id, quantity in quantities.items():
        product = products_by_id[product_id]
        if product.stock < quantity:
            raise InsufficientStockError(
                product.name, product.stock, quantity
            )

        unit_price = unit_price_with_discount(product.price)
        total += unit_price * quantity
        product.stock -= quantity
        db.add(
            models.OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                product_name=product.name,
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
