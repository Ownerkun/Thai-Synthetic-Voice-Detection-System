"""
Password hashing + JWT ใช้ร่วมกันทั้ง UserAccount และ AdminAccount
โดยฝัง role (user / admin) ไว้ใน token
"""

from datetime import datetime, timedelta, timezone
import time
from typing import Literal
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.services.email_token_service import as_utc

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Role = Literal["user", "admin"]


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject_id: UUID, role: Role) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(subject_id), "role": role, "exp": expire, "iat": time.time()}
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


class TokenPayload:
    def __init__(self, subject_id: UUID, role: Role, issued_at: float | None = None):
        self.subject_id = subject_id
        self.role = role
        self.issued_at = issued_at  # None = token รุ่นเก่าที่ไม่มี iat


def decode_access_token(token: str) -> TokenPayload | None:
    """คืนค่า None ถ้า token ไม่ถูกต้อง/หมดอายุ ให้ผู้เรียกตัดสินใจว่าจะ 401 หรือปล่อยผ่าน"""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return TokenPayload(subject_id=UUID(payload["sub"]), role=payload["role"], issued_at=payload.get("iat"))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None

def is_session_revoked(payload: TokenPayload, password_changed_at: datetime | None) -> bool:
    """token ที่ออกก่อนการรีเซ็ตรหัสผ่านใช้ไม่ได้อีก (ถ้ารหัสผ่านไม่เคยถูกรีเซ็ตก็ไม่มีอะไรถูกเพิกถอน)"""
    if password_changed_at is None:
        return False
    return payload.issued_at is None or payload.issued_at < as_utc(password_changed_at).timestamp()
