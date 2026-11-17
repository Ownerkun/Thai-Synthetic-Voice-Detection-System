import hashlib
import smtplib
import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import Settings
from app.core.database import SessionLocal
from app.models.email_token import RESET_PASSWORD, VERIFY_EMAIL, EmailToken
from app.models.user import UserAccount
from app.services import email_token_service, mail_service
from app.services.mail_service import OUTBOX
from tests.conftest import token_from_outbox

PASSWORD = "Password1234"


def _email() -> str:
    return f"{uuid.uuid4().hex[:12]}@example.com"


def _register(client, email: str | None = None, **extra) -> str:
    email = email or _email()
    res = client.post("/auth/register", json={"email": email, "password": PASSWORD, **extra})
    assert res.status_code == 201, res.text
    return email


def _mails_to(email: str) -> list:
    return [m for m in OUTBOX if m.to == email]


def _user(email: str) -> UserAccount:
    with SessionLocal() as db:
        return db.query(UserAccount).filter(UserAccount.email == email).one()


def _tokens(email: str, purpose: str | None = None) -> list[EmailToken]:
    with SessionLocal() as db:
        user = db.query(UserAccount).filter(UserAccount.email == email).one()
        query = db.query(EmailToken).filter(EmailToken.user_id == user.id)
        if purpose:
            query = query.filter(EmailToken.purpose == purpose)
        return query.all()


# ---------- POST /auth/register ----------


def test_register_returns_no_token_and_sends_a_verification_email(client):
    email = _email()
    res = client.post("/auth/register", json={"email": email, "password": PASSWORD, "display_name": "สมชาย"})
    assert res.status_code == 201
    assert res.json()["email"] == email
    assert "access_token" not in res.json()

    (mail,) = _mails_to(email)
    assert "/verify-email?token=" in mail.text
    assert mail.text.startswith("สวัสดีคุณ สมชาย")
    assert _user(email).email_verified_at is None


def test_only_the_hash_of_the_token_is_stored(client):
    email = _register(client)
    raw = token_from_outbox(email, "verify-email")
    (row,) = _tokens(email, VERIFY_EMAIL)
    assert row.token_hash == hashlib.sha256(raw.encode()).hexdigest()
    assert raw not in row.token_hash
    assert row.expires_at is not None


def test_register_with_a_used_email_is_409_and_sends_nothing(client):
    email = _register(client)
    before = len(_mails_to(email))
    res = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert res.status_code == 409
    assert len(_mails_to(email)) == before


def test_invalid_registration_sends_no_email(client):
    email = _email()
    res = client.post("/auth/register", json={"email": email, "password": "short"})
    assert res.status_code == 422
    assert _mails_to(email) == []


def test_register_still_succeeds_when_the_mail_server_is_down(client, monkeypatch):
    def refuse(*args, **kwargs):
        raise ConnectionRefusedError("smtp is down")

    monkeypatch.setattr(smtplib, "SMTP", refuse)
    monkeypatch.setattr(mail_service, "get_settings", lambda: Settings(mail_backend="smtp", smtp_host="smtp.test"))
    email = _email()
    res = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert res.status_code == 201  # ส่งอีเมลล้มเหลวไม่ทำให้สมัครล้ม ผู้ใช้กดขอลิงก์ใหม่ได้
    assert _user(email).email_verified_at is None


def test_register_sends_no_email_when_no_token_was_issued(client, monkeypatch):
    from app.features.auth import router as auth_router

    monkeypatch.setattr(auth_router, "issue_token", lambda db, user, purpose: None)
    email = _email()
    assert client.post("/auth/register", json={"email": email, "password": PASSWORD}).status_code == 201
    assert _mails_to(email) == []  # ต้องไม่มีอีเมลที่ลิงก์เป็น token=None


# ---------- POST /auth/login ----------


def test_login_is_blocked_until_the_email_is_verified(client):
    email = _register(client)
    res = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 403
    assert res.json()["detail"] == "Email not verified"


def test_wrong_password_on_an_unverified_account_is_still_401(client):
    email = _register(client)
    res = client.post("/auth/login", json={"email": email, "password": "WrongPassword1"})
    assert res.status_code == 401  # คนที่ไม่รู้รหัสผ่านไม่ควรรู้ว่าบัญชีนี้ยังไม่ยืนยัน


def test_suspended_takes_precedence_over_unverified(client):
    email = _register(client)
    with SessionLocal() as db:
        db.query(UserAccount).filter(UserAccount.email == email).update({"is_active": False})
        db.commit()
    res = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert (res.status_code, res.json()["detail"]) == (403, "Account suspended")


def test_a_user_created_before_this_feature_can_log_in(client):
    # migration ตั้ง email_verified_at ให้ผู้ใช้เดิมทุกคน (ดู test_email_token_model)
    email = _register(client)
    with SessionLocal() as db:
        db.query(UserAccount).filter(UserAccount.email == email).update({"email_verified_at": datetime.now(timezone.utc)})
        db.commit()
    assert client.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200


# ---------- POST /auth/verify-email ----------


def test_verify_email_marks_the_account_verified_and_logs_the_user_in(client):
    email = _register(client)
    token = token_from_outbox(email, "verify-email")

    res = client.post("/auth/verify-email", json={"token": token})
    assert res.status_code == 200
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    assert client.get("/users/me", headers=headers).json()["email"] == email

    user = _user(email)
    assert user.email_verified_at is not None
    assert user.last_login_at is None  # ยืนยันอีเมลไม่นับเป็นการ login ครั้งแรก (เหมือนตอนสมัครเดิมที่ได้ token ทันที)
    assert client.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200


def test_verification_link_works_only_once(client):
    email = _register(client)
    token = token_from_outbox(email, "verify-email")
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200

    res = client.post("/auth/verify-email", json={"token": token})
    assert (res.status_code, res.json()["detail"]) == (400, "Invalid or expired token")
    assert _tokens(email, VERIFY_EMAIL) == []


def test_unknown_malformed_and_empty_tokens_are_400_or_422(client):
    assert client.post("/auth/verify-email", json={"token": "not-a-real-token"}).status_code == 400
    assert client.post("/auth/verify-email", json={"token": ""}).status_code == 422
    assert client.post("/auth/verify-email", json={}).status_code == 422


def test_expired_token_is_rejected_and_deleted(client):
    email = _register(client)
    token = token_from_outbox(email, "verify-email")
    with SessionLocal() as db:
        db.query(EmailToken).filter(EmailToken.token_hash == hashlib.sha256(token.encode()).hexdigest()).update(
            {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)}
        )
        db.commit()

    assert client.post("/auth/verify-email", json={"token": token}).status_code == 400
    assert _user(email).email_verified_at is None
    assert _tokens(email, VERIFY_EMAIL) == []


def test_a_password_reset_token_cannot_verify_an_email(client):
    email = _register(client)
    raw = "reset-token-" + uuid.uuid4().hex
    with SessionLocal() as db:
        user = db.query(UserAccount).filter(UserAccount.email == email).one()
        db.add(
            EmailToken(
                user_id=user.id,
                purpose=RESET_PASSWORD,
                token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        db.commit()
    assert client.post("/auth/verify-email", json={"token": raw}).status_code == 400
    assert _user(email).email_verified_at is None


def test_verifying_removes_the_other_pending_verification_links(client):
    email = _register(client)
    client.post("/auth/resend-verification", json={"email": email})
    assert len(_tokens(email, VERIFY_EMAIL)) == 2

    client.post("/auth/verify-email", json={"token": token_from_outbox(email, "verify-email")})
    assert _tokens(email, VERIFY_EMAIL) == []


def test_suspended_user_is_verified_but_gets_no_token(client):
    email = _register(client)
    token = token_from_outbox(email, "verify-email")
    with SessionLocal() as db:
        db.query(UserAccount).filter(UserAccount.email == email).update({"is_active": False})
        db.commit()

    res = client.post("/auth/verify-email", json={"token": token})
    assert (res.status_code, res.json()["detail"]) == (403, "Account suspended")
    assert "access_token" not in res.json()


# ---------- POST /auth/resend-verification ----------

GENERIC = "If this email is waiting for verification, a new link has been sent"


def test_resend_sends_a_new_working_link_and_the_old_one_still_works(client):
    email = _register(client)
    old = token_from_outbox(email, "verify-email")

    res = client.post("/auth/resend-verification", json={"email": email})
    assert (res.status_code, res.json()["detail"]) == (202, GENERIC)
    assert len(_mails_to(email)) == 2
    new = token_from_outbox(email, "verify-email")
    assert new != old

    assert client.post("/auth/verify-email", json={"token": new}).status_code == 200


def test_resend_for_a_verified_or_unknown_email_looks_the_same_and_sends_nothing(client):
    verified = _register(client)
    client.post("/auth/verify-email", json={"token": token_from_outbox(verified, "verify-email")})
    unknown = _email()
    before = len(OUTBOX)

    for email in (verified, unknown):
        res = client.post("/auth/resend-verification", json={"email": email})
        assert (res.status_code, res.json()["detail"]) == (202, GENERIC)
    assert len(OUTBOX) == before


def test_resend_sends_nothing_to_a_suspended_account(client):
    email = _register(client)
    with SessionLocal() as db:
        db.query(UserAccount).filter(UserAccount.email == email).update({"is_active": False})
        db.commit()
    before = len(_mails_to(email))
    assert client.post("/auth/resend-verification", json={"email": email}).status_code == 202
    assert len(_mails_to(email)) == before


def test_resend_cooldown_blocks_repeated_requests(client, monkeypatch):
    email = _register(client)
    monkeypatch.setattr(email_token_service, "get_settings", lambda: Settings(email_token_cooldown_seconds=60))

    for _ in range(3):
        res = client.post("/auth/resend-verification", json={"email": email})
        assert (res.status_code, res.json()["detail"]) == (202, GENERIC)  # ตอบเหมือนเดิมแม้ไม่ได้ส่ง
    assert len(_mails_to(email)) == 1  # มีแต่เมลตอนสมัคร
    assert len(_tokens(email, VERIFY_EMAIL)) == 1


def test_resend_rejects_a_malformed_email(client):
    assert client.post("/auth/resend-verification", json={"email": "not-an-email"}).status_code == 422
