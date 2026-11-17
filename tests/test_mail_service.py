import logging
import smtplib
from email import message_from_bytes, policy

import pytest

from app.core.config import Settings
from app.services import mail_service
from app.services.mail_service import OUTBOX, MailMessage, send_email


def _settings(**overrides) -> Settings:
    values = dict(
        mail_backend="smtp",
        mail_from_address="sender@example.com",
        mail_from_name="ระบบตรวจจับ",
        smtp_host="smtp.test",
        smtp_port=587,
        smtp_username="sender@example.com",
        smtp_password="app-password",
        smtp_security="starttls",
        smtp_timeout_seconds=5,
    )
    values.update(overrides)
    return Settings(**values)


class FakeSMTP:
    """แทน smtplib.SMTP / SMTP_SSL: จดว่าถูกเรียกอะไรบ้าง"""

    instances: list["FakeSMTP"] = []
    fail_with: Exception | None = None

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.timeout, self.context = host, port, timeout, context
        self.calls: list[str] = []
        self.sent = None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(f"login:{user}:{password}")

    def send_message(self, mime):
        if FakeSMTP.fail_with:
            raise FakeSMTP.fail_with
        self.calls.append("send")
        self.sent = mime


@pytest.fixture
def fake_smtp(monkeypatch):
    FakeSMTP.instances = []
    FakeSMTP.fail_with = None
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", type("FakeSSL", (FakeSMTP,), {}))
    return FakeSMTP


MESSAGE = MailMessage(to="user@example.com", subject="ยืนยันอีเมล", text="ข้อความ", html="<p>ข้อความ</p>")


def test_memory_backend_keeps_message_in_outbox():
    before = len(OUTBOX)
    assert send_email(MESSAGE, _settings(mail_backend="memory")) is True
    assert len(OUTBOX) == before + 1
    assert OUTBOX[-1] is MESSAGE


def test_console_backend_logs_the_message(caplog):
    with caplog.at_level(logging.INFO, logger="app.services.mail_service"):
        assert send_email(MESSAGE, _settings(mail_backend="console")) is True
    assert "user@example.com" in caplog.text
    assert "ข้อความ" in caplog.text


def test_smtp_starttls_logs_in_and_sends(fake_smtp):
    assert send_email(MESSAGE, _settings()) is True
    (server,) = fake_smtp.instances
    assert (server.host, server.port, server.timeout) == ("smtp.test", 587, 5)
    assert server.calls == ["starttls", "login:sender@example.com:app-password", "send"]

    mime = message_from_bytes(server.sent.as_bytes(), policy=policy.default)
    assert mime["To"] == "user@example.com"
    assert mime["Subject"] == "ยืนยันอีเมล"  # ภาษาไทยต้องถูก encode/decode กลับมาได้ครบ
    assert "sender@example.com" in mime["From"] and "ระบบตรวจจับ" in mime["From"]
    assert mime.get_body(preferencelist=("plain",)).get_content().strip() == "ข้อความ"
    assert mime.get_body(preferencelist=("html",)).get_content().strip() == "<p>ข้อความ</p>"


def test_smtp_ssl_mode_uses_smtp_ssl_and_does_not_call_starttls(fake_smtp):
    assert send_email(MESSAGE, _settings(smtp_security="ssl", smtp_port=465)) is True
    (server,) = fake_smtp.instances
    assert type(server).__name__ == "FakeSSL"
    assert "starttls" not in server.calls
    assert server.calls[-1] == "send"


def test_smtp_without_credentials_skips_login(fake_smtp):
    assert send_email(MESSAGE, _settings(smtp_username=None, smtp_password=None, smtp_security="none")) is True
    (server,) = fake_smtp.instances
    assert server.calls == ["send"]


def test_html_part_is_optional(fake_smtp):
    send_email(MailMessage(to="a@example.com", subject="s", text="plain only"), _settings())
    mime = message_from_bytes(fake_smtp.instances[0].sent.as_bytes(), policy=policy.default)
    assert not mime.is_multipart()


def test_send_failure_is_logged_and_returns_false(fake_smtp, caplog):
    fake_smtp.fail_with = smtplib.SMTPAuthenticationError(535, b"bad credentials")
    with caplog.at_level(logging.ERROR, logger="app.services.mail_service"):
        assert send_email(MESSAGE, _settings()) is False  # ต้องไม่ raise
    assert "user@example.com" in caplog.text


def test_connection_error_is_swallowed(monkeypatch):
    def refuse(*args, **kwargs):
        raise ConnectionRefusedError("no server")

    monkeypatch.setattr(smtplib, "SMTP", refuse)
    assert send_email(MESSAGE, _settings()) is False


def test_verification_email_contains_a_frontend_link_with_the_token(monkeypatch):
    monkeypatch.setattr(mail_service, "get_settings", lambda: _settings(mail_backend="memory", frontend_base_url="https://app.test/"))
    assert mail_service.send_verification_email("a@example.com", "สมชาย", "tok123") is True
    mail = OUTBOX[-1]
    assert mail.to == "a@example.com"
    assert "https://app.test/verify-email?token=tok123" in mail.text  # ตัด / ท้าย base url ออก ไม่ให้เป็น //
    assert "https://app.test/verify-email?token=tok123" in mail.html
    assert "สมชาย" in mail.text
    assert "24 ชั่วโมง" in mail.text


def test_reset_email_contains_the_reset_link_and_ttl(monkeypatch):
    monkeypatch.setattr(mail_service, "get_settings", lambda: _settings(mail_backend="memory", frontend_base_url="https://app.test"))
    mail_service.send_password_reset_email("a@example.com", None, "tok456")
    mail = OUTBOX[-1]
    assert "https://app.test/reset-password?token=tok456" in mail.text
    assert "60 นาที" in mail.text
    assert mail.text.startswith("สวัสดี\n")  # ไม่มีชื่อ -> ไม่ใส่ "คุณ None"


def test_display_name_is_escaped_in_html(monkeypatch):
    monkeypatch.setattr(mail_service, "get_settings", lambda: _settings(mail_backend="memory"))
    mail_service.send_verification_email("a@example.com", "<script>alert(1)</script>", "t")
    assert "<script>" not in OUTBOX[-1].html
    assert "&lt;script&gt;" in OUTBOX[-1].html
