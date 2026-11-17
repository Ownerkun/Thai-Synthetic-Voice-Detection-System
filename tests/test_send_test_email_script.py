import importlib.util
import smtplib
from pathlib import Path

from app.core.config import Settings
from app.services.mail_service import OUTBOX

spec = importlib.util.spec_from_file_location("send_test_email", Path("scripts/send_test_email.py"))
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


def test_memory_backend_sends_and_exits_0(capsys):
    before = len(OUTBOX)
    assert script.run("me@example.com", Settings(mail_backend="memory")) == 0
    assert OUTBOX[-1].to == "me@example.com" and len(OUTBOX) == before + 1
    assert "OK: sent to me@example.com" in capsys.readouterr().out


def test_smtp_failure_prints_the_real_error_and_exits_1(monkeypatch, capsys):
    def refuse(*args, **kwargs):
        raise ConnectionRefusedError("port 587 blocked")

    monkeypatch.setattr(smtplib, "SMTP", refuse)
    settings = Settings(mail_backend="smtp", smtp_host="smtp.test", smtp_username="u@gmail.com", smtp_password="secret-pass")
    assert script.run("me@example.com", settings) == 1
    out = capsys.readouterr().out
    assert "FAILED: ConnectionRefusedError: port 587 blocked" in out
    assert "secret-pass" not in out  # ไม่พิมพ์รหัสผ่านออกมา
