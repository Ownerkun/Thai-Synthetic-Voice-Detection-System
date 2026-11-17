import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import Settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.timeutil import as_utc
from app.models.email_token import RESET_PASSWORD, VERIFY_EMAIL, EmailToken
from app.models.user import UserAccount
from app.services import email_token_service as svc


def _user(db) -> UserAccount:
    user = UserAccount(email=f"{uuid.uuid4().hex[:12]}@example.com", password_hash=hash_password("Password1234"))
    db.add(user)
    db.commit()
    return user


def test_issued_token_is_consumed_exactly_once(client):
    with SessionLocal() as db:
        user = _user(db)
        raw = svc.issue_token(db, user, VERIFY_EMAIL)

        assert svc.consume_token(db, raw, VERIFY_EMAIL).id == user.id
        db.commit()
        assert svc.consume_token(db, raw, VERIFY_EMAIL) is None  # ใช้ซ้ำไม่ได้


def test_token_is_bound_to_its_purpose(client):
    with SessionLocal() as db:
        user = _user(db)
        raw = svc.issue_token(db, user, RESET_PASSWORD)
        assert svc.consume_token(db, raw, VERIFY_EMAIL) is None
        assert svc.consume_token(db, raw, RESET_PASSWORD) is not None


def test_each_token_is_different_and_long_enough(client):
    with SessionLocal() as db:
        user = _user(db)
        tokens = {svc.issue_token(db, user, VERIFY_EMAIL) for _ in range(5)}
        assert len(tokens) == 5
        assert all(len(t) >= 40 for t in tokens)  # token_urlsafe(32) = 43 ตัวอักษร (256 บิต)


def test_cooldown_returns_none_per_user_and_purpose(client, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: Settings(email_token_cooldown_seconds=60))
    with SessionLocal() as db:
        user, other = _user(db), _user(db)
        assert svc.issue_token(db, user, VERIFY_EMAIL) is not None
        assert svc.issue_token(db, user, VERIFY_EMAIL) is None  # ซ้ำใน 60 วินาที
        assert svc.issue_token(db, user, RESET_PASSWORD) is not None  # คนละประเภทไม่ถูกบล็อก
        assert svc.issue_token(db, other, VERIFY_EMAIL) is not None  # คนละผู้ใช้ไม่ถูกบล็อก


def test_issuing_deletes_that_users_expired_tokens(client):
    with SessionLocal() as db:
        user = _user(db)
        db.add(EmailToken(user_id=user.id, purpose=VERIFY_EMAIL, token_hash=uuid.uuid4().hex * 2,
                          expires_at=datetime.now(timezone.utc) - timedelta(hours=1)))
        db.commit()
        svc.issue_token(db, user, VERIFY_EMAIL)
        assert db.query(EmailToken).filter(EmailToken.user_id == user.id).count() == 1


def test_ttl_follows_settings(client, monkeypatch):
    monkeypatch.setattr(svc, "get_settings", lambda: Settings(verify_email_ttl_minutes=10, reset_password_ttl_minutes=5,
                                                              email_token_cooldown_seconds=0))
    with SessionLocal() as db:
        user = _user(db)
        svc.issue_token(db, user, VERIFY_EMAIL)
        svc.issue_token(db, user, RESET_PASSWORD)
        now = datetime.now(timezone.utc)
        rows = {r.purpose: as_utc(r.expires_at) for r in db.query(EmailToken).filter(EmailToken.user_id == user.id)}
        assert timedelta(minutes=9) < rows[VERIFY_EMAIL] - now <= timedelta(minutes=10)
        assert timedelta(minutes=4) < rows[RESET_PASSWORD] - now <= timedelta(minutes=5)
