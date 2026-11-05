"""Rutas de catálogo."""

import asyncio
import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook
from sqlalchemy.orm import Session

import crud
import auth
import database
import models
import schemas

router = APIRouter(prefix="/products", tags=["products"])


def _spreadsheet_safe(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


@router.post(
    "/",
    response_model=schemas.ProductOut,
    summary="Dar de alta un producto",
    response_description="SKU creado con stock y precio de lista",
    tags=["products"],
    responses=schemas.OPENAPI_ERROR_RESPONSES,
)
def create_product(
    product: schemas.ProductCreate,
    admin: auth.AdminUser,
    csrf: auth.Csrf,
    db: Session = Depends(database.get_db),
):
    """Registra un producto en el catálogo.

    `price` debe ser mayor que cero y `stock` no negativo. El identificador
    lo asigna la base de datos.
    """
    try:
        return crud.create_product(db, product)
    except crud.DuplicateProductError:
        raise HTTPException(status_code=409, detail="El SKU ya está registrado") from None


@router.get("/admin", response_model=schemas.ProductListOut, tags=["products-admin"])
def admin_products(
    admin: auth.AdminUser,
    db: Session = Depends(database.get_db),
    search: str | None = None,
    category_id: int | None = Query(default=None, gt=0),
    include_archived: bool = False,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_products_admin(db, search, category_id, include_archived, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.patch("/{product_id}", response_model=schemas.ProductOut, tags=["products-admin"])
def update_product(
    product_id: int,
    payload: schemas.ProductUpdate,
    admin: auth.AdminUser,
    csrf: auth.Csrf,
    db: Session = Depends(database.get_db),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    try:
        return crud.update_product(db, product, payload)
    except crud.DuplicateProductError:
        raise HTTPException(status_code=409, detail="El SKU ya está registrado") from None


@router.post("/{product_id}/duplicate", response_model=schemas.ProductOut, tags=["products-admin"])
def duplicate_product(
    product_id: int,
    admin: auth.AdminUser,
    csrf: auth.Csrf,
    db: Session = Depends(database.get_db),
    sku: str | None = Query(default=None, min_length=1, max_length=64),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    try:
        return crud.duplicate_product(db, product, sku)
    except crud.DuplicateProductError:
        raise HTTPException(status_code=409, detail="El SKU ya está registrado") from None


@router.post("/bulk", tags=["products-admin"])
def bulk_products(
    payload: schemas.BulkProductChange,
    admin: auth.AdminUser,
    csrf: auth.Csrf,
    db: Session = Depends(database.get_db),
):
    try:
        return {"updated": crud.bulk_update_products(db, payload)}
    except crud.MissingProductsError as exc:
        raise HTTPException(status_code=404, detail=f"Productos inexistentes: {exc.product_ids}") from None
    except crud.InsufficientStockError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Stock insuficiente para '{exc.product_name}'") from None


def _read_product_rows(filename: str, content: bytes) -> list[dict]:
    if filename.lower().endswith(".csv"):
        return list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    if filename.lower().endswith(".xlsx"):
        rows = list(load_workbook(io.BytesIO(content), read_only=True, data_only=True).active.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(value or "").strip() for value in rows[0]]
        return [dict(zip(headers, row)) for row in rows[1:]]
    raise HTTPException(status_code=400, detail="El archivo debe ser CSV o XLSX")


def _preview_products(db: Session, rows: list[dict]) -> schemas.ProductImportPreviewOut:
    valid, errors, duplicates = [], [], []
    seen = set()
    existing = {sku for (sku,) in db.query(models.Product.sku).filter(models.Product.sku.isnot(None)).all()}
    for index, row in enumerate(rows, start=2):
        try:
            item = schemas.ProductImportRow(
                name=str(row.get("name", "")).strip(),
                sku=str(row.get("sku", "")).strip(),
                price=float(row.get("price")),
                stock=int(row.get("stock")),
                description=row.get("description"),
                image_url=row.get("image_url"),
                category_slug=row.get("category_slug"),
            )
            if item.sku in seen or item.sku in existing:
                duplicates.append(f"Fila {index}: {item.sku}")
            else:
                seen.add(item.sku)
                valid.append(item)
        except (TypeError, ValueError) as exc:
            errors.append(f"Fila {index}: datos inválidos ({exc})")
        except Exception as exc:
            errors.append(f"Fila {index}: datos inválidos ({exc})")
    return schemas.ProductImportPreviewOut(valid_rows=valid, errors=errors, duplicates=duplicates)


@router.post("/import/preview", response_model=schemas.ProductImportPreviewOut, tags=["products-admin"])
def preview_products(admin: auth.AdminUser, file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    return _preview_products(db, _read_product_rows(file.filename or "", file.file.read()))


@router.post("/import/confirm", response_model=schemas.ImportResultOut, status_code=201, tags=["products-admin"])
def confirm_products(
    rows: list[schemas.ProductImportRow],
    admin: auth.AdminUser,
    csrf: auth.Csrf,
    db: Session = Depends(database.get_db),
):
    preview = _preview_products(db, [row.model_dump() for row in rows])
    if preview.errors or preview.duplicates:
        raise HTTPException(status_code=409, detail={"errors": preview.errors, "duplicates": preview.duplicates})
    categories = {category.slug: category.id for category in db.query(models.Category).all()}
    errors = [
        f"Categoría inexistente: {row.category_slug}"
        for row in rows
        if row.category_slug and row.category_slug not in categories
    ]
    if errors:
        return {"created": 0, "updated": 0, "errors": errors, "duplicates": []}
    payloads = [
        schemas.ProductCreate(
            **row.model_dump(exclude={"category_slug"}),
            category_id=categories.get(row.category_slug),
        )
        for row in rows
    ]
    try:
        created = crud.create_products_bulk(db, payloads)
    except crud.DuplicateProductError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Un SKU ya fue registrado") from None
    return {"created": created, "updated": 0, "errors": errors, "duplicates": []}


@router.get("/export", tags=["products-admin"])
def export_products(
    admin: auth.AdminUser,
    db: Session = Depends(database.get_db),
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
):
    products = db.query(models.Product).order_by(models.Product.id.asc()).all()
    headers = ["id", "name", "sku", "price", "stock", "description", "image_url", "category_id", "is_archived"]
    if format == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(headers)
        for product in products:
            writer.writerow([_spreadsheet_safe(getattr(product, header)) for header in headers])
        return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=products.csv"})
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for product in products:
        sheet.append([_spreadsheet_safe(getattr(product, header)) for header in headers])
    stream = io.BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return StreamingResponse(iter([stream.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=products.xlsx"})


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
