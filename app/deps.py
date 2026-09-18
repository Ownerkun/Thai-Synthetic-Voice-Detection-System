from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.admin import AdminAccount
from app.models.user import UserAccount

DbSession = Annotated[Session, Depends(get_db)]


def _extract_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_optional_user_id(authorization: Annotated[str | None, Header()] = None) -> UUID | None:
    """ใช้กับ /predict ตรวจสอบได้ทั้งแบบ login และไม่ login (token ไม่มีก็ผ่าน, มีแต่ผิดก็ถือว่าไม่ login)"""
    token = _extract_token(authorization)
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None or payload.role != "user":
        return None
    return payload.subject_id


def get_current_user(db: DbSession, authorization: Annotated[str | None, Header()] = None) -> UserAccount:
    """ใช้กับ /history บังคับต้องมี token ที่ถูกต้อง"""
    token = _extract_token(authorization)
    payload = decode_access_token(token) if token else None
    if payload is None or payload.role != "user":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = db.get(UserAccount, payload.subject_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or suspended account")
    return user


def get_current_admin(db: DbSession, authorization: Annotated[str | None, Header()] = None) -> AdminAccount:
    """ใช้กับ /admin/* บังคับต้องมี token ผู้ดูแล"""
    token = _extract_token(authorization)
    payload = decode_access_token(token) if token else None
    if payload is None or payload.role != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Insufficient permissions")
    admin = db.get(AdminAccount, payload.subject_id)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Insufficient permissions")
    return admin
