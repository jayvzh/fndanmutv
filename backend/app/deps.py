from typing import Optional

from fastapi import Header, HTTPException, Request

from app.config import settings


def require_token(authorization: Optional[str] = Header(None)) -> None:
    if not settings.token:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证 Token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.token:
        raise HTTPException(status_code=403, detail="Token 无效")


def get_service(request: Request):
    return request.app.state.svc
