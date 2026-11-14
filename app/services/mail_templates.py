"""คืนค่าเป็น (subject, text, html)"""

from html import escape

APP_NAME = "ระบบตรวจจับเสียงสังเคราะห์ภาษาไทย"


def _greeting(display_name: str | None) -> str:
    return f"สวัสดีคุณ {display_name}" if display_name else "สวัสดี"


def _render(display_name: str | None, intro: str, button: str, link: str, note: str) -> tuple[str, str]:
    greeting = _greeting(display_name)
    text = f"{greeting}\n\n{intro}\n\n{button}:\n{link}\n\n{note}\n\n— {APP_NAME}\n"
    html = (
        f"<p>{escape(greeting)}</p>"
        f"<p>{escape(intro)}</p>"
        f'<p><a href="{escape(link)}" style="display:inline-block;padding:12px 24px;background:#2E5E4E;'
        f'color:#ffffff;text-decoration:none;border-radius:8px">{escape(button)}</a></p>'
        f"<p>หรือคัดลอกลิงก์นี้เปิดในเบราว์เซอร์:<br>{escape(link)}</p>"
        f"<p>{escape(note)}</p>"
        f"<p>— {escape(APP_NAME)}</p>"
    )
    return text, html


def verification_email(display_name: str | None, link: str, ttl_hours: int) -> tuple[str, str, str]:
    text, html = _render(
        display_name,
        f"ขอบคุณที่สมัครใช้งาน กรุณายืนยันอีเมลเพื่อเริ่มใช้งาน (ลิงก์ใช้ได้ {ttl_hours} ชั่วโมง)",
        "ยืนยันอีเมล",
        link,
        "หากคุณไม่ได้สมัครใช้บริการด้วยตนเอง โปรดเพิกเฉยต่ออีเมลฉบับนี้",
    )
    return f"ยืนยันอีเมลของคุณ — {APP_NAME}", text, html


def password_reset_email(display_name: str | None, link: str, ttl_minutes: int) -> tuple[str, str, str]:
    text, html = _render(
        display_name,
        f"เราได้รับคำขอตั้งรหัสผ่านใหม่สำหรับบัญชีของคุณ (ลิงก์ใช้ได้ {ttl_minutes} นาที)",
        "ตั้งรหัสผ่านใหม่",
        link,
        "หากคุณไม่ได้เป็นผู้ขอตั้งรหัสผ่านใหม่ โปรดเพิกเฉยต่ออีเมลฉบับนี้",
    )
    return f"ตั้งรหัสผ่านใหม่ — {APP_NAME}", text, html
