"""Autenticación basada en sesión firmada y autorización por rol."""

import secrets
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, Header, HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

import database
import models
from config import get_settings

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="northstar-session")


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_session(response: Response, user: models.User, csrf_token: str | None = None) -> str:
    csrf = csrf_token or new_csrf_token()
    value = _serializer().dumps({"user_id": user.id, "role": user.role, "csrf": csrf})
    response.set_cookie(
        "northstar_session",
        value,
        max_age=get_settings().session_max_age,
        httponly=True,
        secure=get_settings().session_cookie_secure,
        samesite="lax",
    )
    return csrf


def clear_session(response: Response) -> None:
    response.delete_cookie("northstar_session")


def current_user(
    request: Request,
    db: Annotated[Session, Depends(database.get_db)],
) -> models.User:
    raw = request.cookies.get("northstar_session")
    if not raw:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    try:
        session = _serializer().loads(raw, max_age=get_settings().session_max_age)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada") from None
    user = db.query(models.User).filter(models.User.id == session.get("user_id")).first()
    if not user or not user.is_active or not user.password_hash:
        raise HTTPException(status_code=401, detail="Cuenta inactiva o inválida")
    request.state.session = session
    return user


def require_csrf(
    request: Request,
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> None:
    session = getattr(request.state, "session", None)
    if not session or not x_csrf_token or not secrets.compare_digest(x_csrf_token, session.get("csrf", "")):
        raise HTTPException(status_code=403, detail="Token CSRF inválido")


def require_admin(user: Annotated[models.User, Depends(current_user)]) -> models.User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Permisos de administrador requeridos")
    return user


CurrentUser = Annotated[models.User, Depends(current_user)]
AdminUser = Annotated[models.User, Depends(require_admin)]
Csrf = Annotated[None, Depends(require_csrf)]
