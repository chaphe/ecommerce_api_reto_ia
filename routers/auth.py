"""Registro, inicio y cierre de sesión."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

import auth
import crud
import database
import schemas

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.RegisterIn, response: Response, db: Session = Depends(database.get_db)):
    try:
        user = crud.create_authenticated_user(db, payload)
    except crud.EmailAlreadyRegisteredError:
        raise HTTPException(status_code=409, detail="El email ya está registrado") from None
    auth.set_session(response, user)
    return user


@router.post("/login", response_model=schemas.UserOut)
def login(payload: schemas.LoginIn, response: Response, db: Session = Depends(database.get_db)):
    user = crud.find_user_by_email(db, payload.email)
    if not user or not user.is_active or not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    auth.set_session(response, user)
    return user


@router.post("/logout", status_code=204)
def logout(response: Response, user: auth.CurrentUser, csrf: auth.Csrf):
    auth.clear_session(response)


@router.get("/me", response_model=schemas.UserOut)
def me(user: auth.CurrentUser):
    return user


@router.get("/csrf")
def csrf(request_user: auth.CurrentUser, request: Request):
    session = getattr(request.state, "session", None)
    return {"csrf_token": session["csrf"]}
