"""
raw token อยู่แค่ในอีเมลที่ส่งออกไป ฐานข้อมูลเก็บเฉพาะ SHA-256
การใช้งาน: ผู้เรียกเป็นคน commit เอง เพื่อให้ "ใช้โทเคน + เปลี่ยนข้อมูลผู้ใช้" สำเร็จหรือล้มเหลวพร้อมกัน
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.email_token import RESET_PASSWORD, VERIFY_EMAIL, EmailToken
from app.models.user import UserAccount
from app.core.timeutil import as_utc


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _ttl(purpose: str) -> timedelta:
    settings = get_settings()
    minutes = settings.verify_email_ttl_minutes if purpose == VERIFY_EMAIL else settings.reset_password_ttl_minutes
    return timedelta(minutes=minutes)


def issue_token(db: Session, user: UserAccount, purpose: str) -> str | None:
    now = datetime.now(timezone.utc)
    db.query(EmailToken).filter(EmailToken.user_id == user.id, EmailToken.expires_at < now).delete()

    cooldown = timedelta(seconds=get_settings().email_token_cooldown_seconds)
    latest = (
        db.query(func.max(EmailToken.created_at))
        .filter(EmailToken.user_id == user.id, EmailToken.purpose == purpose)
        .scalar()
    )
    if latest is not None and now - as_utc(latest) < cooldown:
        db.commit()
        return None

    raw_token = secrets.token_urlsafe(32)
    db.add(EmailToken(user_id=user.id, purpose=purpose, token_hash=_hash(raw_token), expires_at=now + _ttl(purpose)))
    db.commit()
    return raw_token


def consume_token(db: Session, raw_token: str, purpose: str) -> UserAccount | None:
    row = db.query(EmailToken).filter(EmailToken.token_hash == _hash(raw_token), EmailToken.purpose == purpose).first()
    if row is None:
        return None
    expired = as_utc(row.expires_at) <= datetime.now(timezone.utc)
    claimed = db.query(EmailToken).filter(EmailToken.id == row.id).delete() == 1
    if expired or not claimed:
        db.commit()
        return None
    return db.get(UserAccount, row.user_id)


def delete_tokens(db: Session, user_id: UUID, purpose: str) -> None:
    db.query(EmailToken).filter(EmailToken.user_id == user_id, EmailToken.purpose == purpose).delete()
