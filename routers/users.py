"""Rutas de usuarios e historial de pedidos."""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

import crud
import auth
import database
import schemas

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    response_model=schemas.UserOut,
    summary="Registrar un usuario",
    response_description="Usuario persistido con identificador asignado",
    tags=["users"],
    responses={
        **schemas.OPENAPI_ERROR_RESPONSES,
        409: {
            "model": schemas.ErrorResponse,
            "description": "El email ya está registrado (unique constraint)",
        },
    },
    status_code=200,
)
def create_user(
    user: schemas.AdminUserCreate,
    admin: auth.AdminUser,
    csrf: auth.Csrf,
    db: Session = Depends(database.get_db),
):
    """Crea un cliente con email único.

    Valida el payload con Pydantic v2 y persiste en `users`. Un email
    duplicado se traduce en HTTP 409 para no filtrar detalles del motor SQL.
    """
    try:
        return crud.create_authenticated_user(db, user)
    except crud.EmailAlreadyRegisteredError:
        raise HTTPException(status_code=409, detail="El email ya está registrado")


@router.get("/me", response_model=schemas.UserOut)
def get_me(user: auth.CurrentUser):
    return user


@router.patch("/me", response_model=schemas.UserOut)
def update_me(
    payload: schemas.UserProfileUpdate,
    user: auth.CurrentUser,
    csrf: auth.Csrf,
    db: Session = Depends(database.get_db),
):
    return crud.update_user(db, user, schemas.AdminUserUpdate(**payload.model_dump()))


@router.get(
    "/{user_id}/orders",
    response_model=list[schemas.UserOrderHistoryOut],
    summary="Historial de pedidos de un usuario",
    response_description="Lista de órdenes con nombres exactos de productos comprados",
    tags=["users"],
    responses=schemas.OPENAPI_ERROR_RESPONSES,
)
def get_user_orders(
    current: auth.CurrentUser,
    user_id: int = Path(..., gt=0, description="Identificador del usuario"),
    db: Session = Depends(database.get_db),
):
    """Devuelve el historial de compras del usuario.

    La consulta SQLAlchemy hace JOIN entre `users`, `orders`, `order_items`
    y `products`. Cada elemento incluye `product_names`. Si el `user_id` no
    existe responde 404; si existe sin pedidos, una lista vacía.
    """
    if current.role != "admin" and current.id != user_id:
        raise HTTPException(status_code=403, detail="No puedes consultar pedidos de otro usuario")
    history = crud.get_user_order_history(db, user_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return history
