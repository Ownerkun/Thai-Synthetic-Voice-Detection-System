import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import Settings
from app.core.database import SessionLocal
from app.core.security import create_access_token, decode_access_token, is_session_revoked
from app.models.email_token import RESET_PASSWORD, VERIFY_EMAIL, EmailToken
from app.models.user import UserAccount
from app.services import email_token_service
from app.services.mail_service import OUTBOX
from tests.conftest import make_wav_bytes, register_verified, token_from_outbox

OLD = "Password1234"
NEW = "BrandNewPass567"
GENERIC = "If this email is registered, a password reset link has been sent"


def _verified_user(client) -> tuple[str, dict]:
    email = f"{uuid.uuid4().hex[:12]}@example.com"
    return email, register_verified(client, {"email": email, "password": OLD})


def _forgot(client, email: str):
    return client.post("/auth/forgot-password", json={"email": email})


def _reset(client, token: str, password: str = NEW):
    return client.post("/auth/reset-password", json={"token": token, "new_password": password})


def _login(client, email: str, password: str):
    return client.post("/auth/login", json={"email": email, "password": password})


def _reset_mails(email: str) -> list:
    return [m for m in OUTBOX if m.to == email and "/reset-password?token=" in m.text]


def _set(email: str, **values) -> None:
    with SessionLocal() as db:
        db.query(UserAccount).filter(UserAccount.email == email).update(values)
        db.commit()


# ---------- POST /auth/forgot-password ----------


def test_forgot_password_sends_a_reset_link(client):
    email, _ = _verified_user(client)
    res = _forgot(client, email)
    assert (res.status_code, res.json()["detail"]) == (202, GENERIC)

    (mail,) = _reset_mails(email)
    assert "60 นาที" in mail.text
    assert token_from_outbox(email, "reset-password")


def test_unknown_and_suspended_emails_get_the_same_answer_but_no_mail(client):
    unknown = f"{uuid.uuid4().hex[:12]}@example.com"
    suspended, _ = _verified_user(client)
    _set(suspended, is_active=False)
    before = len(OUTBOX)

    for email in (unknown, suspended):
        res = _forgot(client, email)
        assert (res.status_code, res.json()["detail"]) == (202, GENERIC)
    assert len(OUTBOX) == before


def test_forgot_password_rejects_a_malformed_email(client):
    assert _forgot(client, "not-an-email").status_code == 422


def test_forgot_password_cooldown_sends_only_one_mail(client, monkeypatch):
    email, _ = _verified_user(client)
    monkeypatch.setattr(email_token_service, "get_settings", lambda: Settings(email_token_cooldown_seconds=60))
    for _ in range(3):
        assert _forgot(client, email).status_code == 202
    assert len(_reset_mails(email)) == 1


# ---------- POST /auth/reset-password ----------


def test_reset_password_changes_the_password(client):
    email, _ = _verified_user(client)
    _forgot(client, email)
    res = _reset(client, token_from_outbox(email, "reset-password"))
    assert res.status_code == 200

    assert _login(client, email, NEW).status_code == 200
    assert _login(client, email, OLD).status_code == 401


def test_reset_link_works_only_once(client):
    email, _ = _verified_user(client)
    _forgot(client, email)
    token = token_from_outbox(email, "reset-password")
    assert _reset(client, token).status_code == 200

    res = _reset(client, token, "AnotherPass999")
    assert (res.status_code, res.json()["detail"]) == (400, "Invalid or expired token")
    assert _login(client, email, NEW).status_code == 200  # รหัสผ่านไม่ถูกเปลี่ยนซ้ำ


def test_using_one_reset_link_invalidates_the_other_pending_ones(client):
    email, _ = _verified_user(client)
    _forgot(client, email)
    first = token_from_outbox(email, "reset-password")
    _forgot(client, email)
    second = token_from_outbox(email, "reset-password")
    assert first != second

    assert _reset(client, second).status_code == 200
    assert _reset(client, first).status_code == 400


def test_invalid_expired_and_wrong_purpose_tokens_are_rejected(client):
    email, _ = _verified_user(client)
    assert _reset(client, "not-a-real-token").status_code == 400

    _forgot(client, email)
    token = token_from_outbox(email, "reset-password")
    with SessionLocal() as db:
        db.query(EmailToken).filter(EmailToken.token_hash == hashlib.sha256(token.encode()).hexdigest()).update(
            {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)}
        )
        db.commit()
    assert _reset(client, token).status_code == 400  # หมดอายุ
    assert _login(client, email, OLD).status_code == 200

    # ลิงก์ยืนยันอีเมลเอามารีเซ็ตรหัสผ่านไม่ได้
    other = f"{uuid.uuid4().hex[:12]}@example.com"
    client.post("/auth/register", json={"email": other, "password": OLD})
    assert _reset(client, token_from_outbox(other, "verify-email")).status_code == 400


def test_weak_password_is_422_and_does_not_burn_the_link(client):
    email, _ = _verified_user(client)
    _forgot(client, email)
    token = token_from_outbox(email, "reset-password")
    assert _reset(client, token, "short").status_code == 422
    assert _reset(client, token).status_code == 200


def test_reset_through_the_mailbox_also_verifies_an_unverified_account(client):
    email = f"{uuid.uuid4().hex[:12]}@example.com"
    client.post("/auth/register", json={"email": email, "password": OLD})
    assert _login(client, email, OLD).status_code == 403

    _forgot(client, email)  # ขอได้ทั้งที่ยังไม่ยืนยัน
    assert _reset(client, token_from_outbox(email, "reset-password")).status_code == 200

    assert _login(client, email, NEW).status_code == 200
    with SessionLocal() as db:
        user = db.query(UserAccount).filter(UserAccount.email == email).one()
        assert db.query(EmailToken).filter(EmailToken.user_id == user.id, EmailToken.purpose == VERIFY_EMAIL).count() == 0


def test_reset_does_not_unsuspend_an_account(client):
    email, _ = _verified_user(client)
    _forgot(client, email)
    token = token_from_outbox(email, "reset-password")
    _set(email, is_active=False)
    assert _reset(client, token).status_code == 200
    res = _login(client, email, NEW)
    assert (res.status_code, res.json()["detail"]) == (403, "Account suspended")


# ---------- เซสชันเก่าถูกเพิกถอนหลังรีเซ็ต ----------


def test_tokens_issued_before_a_reset_stop_working_but_new_logins_do(client):
    email, old_headers = _verified_user(client)
    assert client.get("/users/me", headers=old_headers).status_code == 200

    _forgot(client, email)
    _reset(client, token_from_outbox(email, "reset-password"))

    res = client.get("/users/me", headers=old_headers)
    assert res.status_code == 401
    assert client.get("/history", headers=old_headers).status_code == 401

    new_token = _login(client, email, NEW).json()["access_token"]  # login ทันทีหลังรีเซ็ตต้องใช้ได้
    assert client.get("/users/me", headers={"Authorization": f"Bearer {new_token}"}).status_code == 200


def test_predict_treats_a_revoked_token_as_a_guest(client):
    email, old_headers = _verified_user(client)
    _forgot(client, email)
    _reset(client, token_from_outbox(email, "reset-password"))

    res = client.post("/predict", files={"files": ("a.wav", make_wav_bytes(), "audio/wav")}, headers=old_headers)
    assert res.status_code == 200  # ยังตรวจเสียงได้แบบ guest
    assert client.get("/history", headers=old_headers).status_code == 401


def test_changing_the_password_while_logged_in_keeps_the_current_session(client):
    email, headers = _verified_user(client)
    res = client.put("/users/me/password", json={"current_password": OLD, "new_password": NEW}, headers=headers)
    assert res.status_code == 204
    assert client.get("/users/me", headers=headers).status_code == 200  # พฤติกรรมเดิม ไม่ถูกเปลี่ยนโดยฟีเจอร์นี้


def test_is_session_revoked_rules():
    user_id = uuid.uuid4()
    changed = datetime.now(timezone.utc)
    before = decode_access_token(create_access_token(user_id, "user"))
    assert before is not None and before.issued_at is not None

    assert is_session_revoked(before, None) is False  # ไม่เคยรีเซ็ต
    assert is_session_revoked(before, changed + timedelta(seconds=1)) is True  # token ออกก่อนรีเซ็ต
    assert is_session_revoked(before, changed - timedelta(seconds=5)) is False  # token ออกหลังรีเซ็ต
    # SQLite คืนเวลาแบบไม่มี timezone ต้องตีความเป็น UTC เหมือนกัน
    assert is_session_revoked(before, (changed - timedelta(seconds=5)).replace(tzinfo=None)) is False

    legacy = decode_access_token(create_access_token(user_id, "user"))
    legacy.issued_at = None  # token รุ่นก่อนมี iat
    assert is_session_revoked(legacy, changed) is True
    assert is_session_revoked(legacy, None) is False
