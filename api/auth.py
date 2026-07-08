"""Session issuing/verification for the two roles: manager and cadet.

Manager: real password, checked against a hash in manager_users.
Cadet: no password -- a cadet "logs in" with just their personal_number,
which must already exist in the roster (added by the manager). This is a
deliberate, accepted tradeoff for a small trusted unit, not an oversight.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_session
from db.models import ManagerUser, CadetAccount

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24 * 7
COOKIE_NAME = "kambatztron_session"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_token(claims: dict) -> str:
    to_encode = dict(claims)
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session")


def _set_session_cookie(response: Response, claims: dict) -> None:
    token = create_token(claims)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=TOKEN_EXPIRE_HOURS * 3600,
    )


class ManagerLoginRequest(BaseModel):
    username: str
    password: str


class CadetLoginRequest(BaseModel):
    personal_number: str


@router.post("/manager/login")
def manager_login(body: ManagerLoginRequest, response: Response, session: Session = Depends(get_session)):
    user = session.query(ManagerUser).filter_by(username=body.username).first()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    _set_session_cookie(response, {"role": "manager", "username": user.username})
    return {"role": "manager", "username": user.username}


@router.post("/cadet/login")
def cadet_login(body: CadetLoginRequest, response: Response, session: Session = Depends(get_session)):
    cadet = session.query(CadetAccount).filter_by(personal_number=body.personal_number).first()
    if cadet is None:
        raise HTTPException(status_code=404, detail="No cadet with that personal number. Ask your manager to add you to the roster.")
    _set_session_cookie(response, {"role": "cadet", "personal_number": cadet.personal_number, "cadet_id": cadet.id})
    return {"role": "cadet", "personal_number": cadet.personal_number, "name": cadet.name}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"status": "logged out"}
