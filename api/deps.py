"""FastAPI dependencies for role-gated routes."""
from fastapi import Depends, HTTPException, Request

from api.auth import COOKIE_NAME, decode_token


def get_current_claims(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_token(token)


def require_manager(claims: dict = Depends(get_current_claims)) -> dict:
    if claims.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Manager access required")
    return claims


def require_cadet(claims: dict = Depends(get_current_claims)) -> dict:
    if claims.get("role") != "cadet":
        raise HTTPException(status_code=403, detail="Cadet access required")
    return claims
