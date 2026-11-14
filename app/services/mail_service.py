"""
มี 3 โหมดตาม MAIL_BACKEND
  console : พิมพ์ข้อความลง log (dev: copy ลิงก์จาก log มาเปิดเอง)
  smtp    : ส่งจริงผ่าน SMTP ใช้ได้กับ Gmail (App Password), Resend, Brevo, Mailjet, Amazon SES ฯลฯ
            เปลี่ยนผู้ให้บริการด้วยการแก้ SMTP_* ใน .env
  memory  : เก็บไว้ใน OUTBOX (ใช้ในเทสต์)
"""

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import Settings, get_settings
from app.services import mail_templates

logger = logging.getLogger(__name__)


@dataclass
class MailMessage:
    to: str
    subject: str
    text: str
    html: str | None = None


OUTBOX: list[MailMessage] = []  # ใช้เฉพาะ MAIL_BACKEND=memory


def send_email(message: MailMessage, settings: Settings | None = None) -> bool:
    """คืน True ถ้าส่ง หรือบันทึก สำเร็จ ไม่ raise"""
    settings = settings or get_settings()
    try:
        if settings.mail_backend == "smtp":
            _send_smtp(message, settings)
        elif settings.mail_backend == "memory":
            OUTBOX.append(message)
        else:
            logger.info("[MAIL console] to=%s subject=%s\n%s", message.to, message.subject, message.text)
        return True
    except Exception:  # noqa: BLE001 smtplib/socket โยน exception หลายชนิด ไม่ให้หลุดไปทำให้ background task พัง
        logger.exception("Failed to send email to %s (backend=%s)", message.to, settings.mail_backend)
        return False


def _build(message: MailMessage, settings: Settings) -> EmailMessage:
    mime = EmailMessage()
    mime["From"] = formataddr((settings.mail_from_name, settings.mail_from_address))
    mime["To"] = message.to
    mime["Subject"] = message.subject
    mime.set_content(message.text)
    if message.html:
        mime.add_alternative(message.html, subtype="html")
    return mime


def _send_smtp(message: MailMessage, settings: Settings) -> None:
    mime = _build(message, settings)
    timeout = settings.smtp_timeout_seconds
    if settings.smtp_security == "ssl":
        server: smtplib.SMTP = smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, timeout=timeout, context=ssl.create_default_context()
        )
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout)
    with server:
        if settings.smtp_security == "starttls":
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(mime)


def _link(path: str, raw_token: str, settings: Settings) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/{path}?token={raw_token}"


def send_verification_email(to: str, display_name: str | None, raw_token: str) -> bool:
    settings = get_settings()
    link = _link("verify-email", raw_token, settings)
    subject, text, html = mail_templates.verification_email(display_name, link, settings.verify_email_ttl_minutes // 60)
    return send_email(MailMessage(to=to, subject=subject, text=text, html=html), settings)


def send_password_reset_email(to: str, display_name: str | None, raw_token: str) -> bool:
    settings = get_settings()
    link = _link("reset-password", raw_token, settings)
    subject, text, html = mail_templates.password_reset_email(display_name, link, settings.reset_password_ttl_minutes)
    return send_email(MailMessage(to=to, subject=subject, text=text, html=html), settings)
