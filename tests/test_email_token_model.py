import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.database import Base, SessionLocal
from app.core.security import hash_password
from app.models.email_token import RESET_PASSWORD, VERIFY_EMAIL, EmailToken
from app.models.user import UserAccount


def _new_user(db) -> UserAccount:
    user = UserAccount(email=f"{uuid.uuid4().hex[:12]}@example.com", password_hash=hash_password("Password1234"))
    db.add(user)
    db.commit()
    return user


def _token(user_id, token_hash: str, purpose: str = VERIFY_EMAIL) -> EmailToken:
    return EmailToken(
        user_id=user_id,
        purpose=purpose,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )


def test_new_user_is_not_verified_and_has_no_password_change_time(client):
    with SessionLocal() as db:
        user = _new_user(db)
        assert user.email_verified_at is None
        assert user.email_verified is False
        assert user.password_changed_at is None

        user.email_verified_at = datetime.now(timezone.utc)
        db.commit()
        assert user.email_verified is True


def test_email_token_is_stored_with_a_creation_time(client):
    with SessionLocal() as db:
        user = _new_user(db)
        token = _token(user.id, uuid.uuid4().hex + uuid.uuid4().hex, RESET_PASSWORD)
        db.add(token)
        db.commit()
        db.refresh(token)
        assert token.purpose == RESET_PASSWORD
        assert token.created_at is not None
        assert token.expires_at is not None


def test_token_hash_must_be_unique(client):
    same_hash = uuid.uuid4().hex + uuid.uuid4().hex
    with SessionLocal() as db:
        user = _new_user(db)
        db.add(_token(user.id, same_hash))
        db.commit()
        db.add(_token(user.id, same_hash))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def _alembic(db_url: str, *args: str) -> None:
    # รันเป็น process แยก ให้ใช้ฐานข้อมูลชั่วคราว ไม่แตะฐานข้อมูลของชุดเทสต์
    env = {**os.environ, "DATABASE_URL": db_url}
    result = subprocess.run([sys.executable, "-m", "alembic", *args], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_migration_marks_existing_users_as_verified_and_can_downgrade(tmp_path):
    # migration ชุดเก่ามีคำสั่งที่ SQLite ไม่รองรับ (ALTER COLUMN) จึงรันทั้งสายบน SQLite ไม่ได้
    # สร้างโครงสร้างจากโมเดลแล้วถอดส่วนใหม่ออก ให้เหมือนฐานข้อมูลก่อนมีฟีเจอร์นี้ (ต้องใช้ SQLite >= 3.35)
    db_url = f"sqlite:///{tmp_path / 'migration.db'}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE email_token"))
        conn.execute(text("ALTER TABLE user_account DROP COLUMN email_verified_at"))
        conn.execute(text("ALTER TABLE user_account DROP COLUMN password_changed_at"))
        conn.execute(
            text("INSERT INTO user_account (id, email, password_hash, is_active) VALUES (:id, :email, 'x', 1)"),
            {"id": str(uuid.uuid4()), "email": "old-user@example.com"},
        )
    _alembic(db_url, "stamp", "b7c3e1f4a9d2")

    _alembic(db_url, "upgrade", "head")
    with engine.connect() as conn:
        verified_at = conn.execute(text("SELECT email_verified_at FROM user_account")).scalar_one()
        assert verified_at is not None  # ผู้ใช้เดิมไม่ถูกล็อก
        assert conn.execute(text("SELECT password_changed_at FROM user_account")).scalar_one() is None
    assert "email_token" in inspect(engine).get_table_names()

    _alembic(db_url, "downgrade", "b7c3e1f4a9d2")
    inspector = inspect(create_engine(db_url))
    assert "email_token" not in inspector.get_table_names()
    assert "email_verified_at" not in {c["name"] for c in inspector.get_columns("user_account")}
