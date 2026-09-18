"""
Password hashing + JWT ใช้ร่วมกันทั้ง UserAccount และ AdminAccount
โดยฝัง role (user / admin) ไว้ใน token
"""

from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

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
    payload = {"sub": str(subject_id), "role": role, "exp": expire}
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


class TokenPayload:
    def __init__(self, subject_id: UUID, role: Role):
        self.subject_id = subject_id
        self.role = role


def decode_access_token(token: str) -> TokenPayload | None:
    """คืนค่า None ถ้า token ไม่ถูกต้อง/หมดอายุ ให้ผู้เรียกตัดสินใจว่าจะ 401 หรือปล่อยผ่าน"""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return TokenPayload(subject_id=UUID(payload["sub"]), role=payload["role"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
