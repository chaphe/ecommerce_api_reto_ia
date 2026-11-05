"""Administración protegida de usuarios e importación masiva."""

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from openpyxl import load_workbook
from sqlalchemy.orm import Session

import auth
import crud
import database
import models
import schemas

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("/", response_model=schemas.UserListOut)
def users(
    admin: auth.AdminUser,
    db: Session = Depends(database.get_db),
    search: str | None = None,
    role: str | None = Query(default=None, pattern="^(admin|buyer)$"),
    is_active: bool | None = None,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_users(db, search, role, is_active, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/", response_model=schemas.UserOut, status_code=201)
def create(payload: schemas.AdminUserCreate, admin: auth.AdminUser, csrf: auth.Csrf, db: Session = Depends(database.get_db)):
    try:
        return crud.create_authenticated_user(db, payload)
    except crud.EmailAlreadyRegisteredError:
        raise HTTPException(status_code=409, detail="El email ya está registrado") from None


@router.patch("/{user_id}", response_model=schemas.UserOut)
def update(user_id: int, payload: schemas.AdminUserUpdate, admin: auth.AdminUser, csrf: auth.Csrf, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == admin.id and (payload.is_active is False or payload.role == "buyer"):
        active_admins = db.query(models.User).filter(models.User.role == "admin", models.User.is_active.is_(True)).count()
        if active_admins <= 1:
            raise HTTPException(status_code=400, detail="Debe existir al menos un administrador activo")
    return crud.update_user(db, user, payload)


def _read_rows(filename: str, content: bytes) -> list[dict]:
    if filename.lower().endswith(".csv"):
        return list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    if filename.lower().endswith(".xlsx"):
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(value or "").strip() for value in rows[0]]
        return [dict(zip(headers, row)) for row in rows[1:]]
    raise HTTPException(status_code=400, detail="El archivo debe ser CSV o XLSX")


def _validate_rows(db: Session, rows: list[dict]) -> schemas.ImportPreviewOut:
    valid, errors, duplicates = [], [], []
    seen = set()
    existing = {email for (email,) in db.query(models.User.email).all()}
    for index, row in enumerate(rows, start=2):
        try:
            item = schemas.ImportUserRow(
                name=str(row.get("name", "")).strip(),
                email=str(row.get("email", "")).strip().lower(),
                password=str(row.get("password", "")),
                role=str(row.get("role") or "buyer").strip().lower(),
            )
            if item.email in seen or item.email in existing:
                duplicates.append(f"Fila {index}: {item.email}")
            else:
                seen.add(item.email)
                valid.append(item)
        except Exception as exc:
            errors.append(f"Fila {index}: datos inválidos ({exc})")
    return schemas.ImportPreviewOut(valid_rows=valid, errors=errors, duplicates=duplicates)


@router.post("/import/preview", response_model=schemas.ImportPreviewOut)
def preview(file: Annotated[UploadFile, File(...)], admin: auth.AdminUser, db: Session = Depends(database.get_db)):
    return _validate_rows(db, _read_rows(file.filename or "", file.file.read()))


@router.post("/import/confirm", response_model=list[schemas.UserOut], status_code=201)
def confirm(rows: list[schemas.ImportUserRow], admin: auth.AdminUser, csrf: auth.Csrf, db: Session = Depends(database.get_db)):
    if not rows:
        raise HTTPException(status_code=400, detail="No hay filas válidas para importar")
    preview_result = _validate_rows(db, [row.model_dump() for row in rows])
    if preview_result.errors or preview_result.duplicates:
        raise HTTPException(status_code=409, detail={"errors": preview_result.errors, "duplicates": preview_result.duplicates})
    try:
        created_count = crud.create_authenticated_users_bulk(db, rows)
    except crud.EmailAlreadyRegisteredError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Un email ya fue registrado") from None
    return [
        db.query(models.User).filter(models.User.email == row.email).first()
        for row in rows
    ]
