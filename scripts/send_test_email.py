"""
ลองส่งอีเมลทดสอบด้วยค่า MAIL_* / SMTP_* ใน .env ปัจจุบัน ใช้เช็คก่อน deploy ว่าตั้งค่า SMTP ถูกต้อง
(รหัสผ่านผิด / พอร์ตถูกบล็อก / เครือข่ายของ VPS ออกพอร์ต SMTP ไม่ได้ จะเห็นข้อความ error ตรงนี้ ไม่ต้องรอผู้ใช้สมัครจริง)

ใช้งาน:
  docker compose exec api python scripts/send_test_email.py <อีเมลผู้รับ>
  หรือรัน local: python scripts/send_test_email.py <อีเมลผู้รับ>
"""
import sys

sys.path.insert(0, ".")

from app.core.config import Settings, get_settings
from app.services import mail_service
from app.services.mail_service import MailMessage


def run(to: str, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    message = MailMessage(
        to=to,
        subject="ทดสอบส่งอีเมล — Thai Synthetic Voice Detection",
        text="ถ้าคุณอ่านข้อความนี้ได้ แปลว่าการตั้งค่าส่งอีเมลของระบบถูกต้องแล้ว",
        html="<p>ถ้าคุณอ่านข้อความนี้ได้ แปลว่าการตั้งค่าส่งอีเมลของระบบถูกต้องแล้ว</p>",
    )
    print(f"backend={settings.mail_backend} from={settings.mail_from_address}", end="")
    if settings.mail_backend == "smtp":
        print(f" smtp={settings.smtp_host}:{settings.smtp_port} security={settings.smtp_security} user={settings.smtp_username}")
        try:
            mail_service._send_smtp(message, settings)  # เรียกตรงๆ เพื่อให้เห็น error จริง (send_email กลืน error ไว้เขียน log)
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED: {type(exc).__name__}: {exc}")
            return 1
    else:
        print()
        if settings.mail_backend == "console":
            print("MAIL_BACKEND=console ไม่ได้ส่งอีเมลจริง (แค่พิมพ์ลง log) ตั้ง MAIL_BACKEND=smtp ใน .env ก่อน")
        mail_service.send_email(message, settings)
    print(f"OK: sent to {to}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/send_test_email.py <recipient email>")
        sys.exit(1)
    sys.exit(run(sys.argv[1]))
