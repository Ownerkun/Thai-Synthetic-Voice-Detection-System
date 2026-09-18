"""
สร้างบัญชีแอดมินเพิ่มเติม (นอกเหนือจาก bootstrap admin คนแรกที่ระบบสร้างให้อัตโนมัติ)

ใช้งาน:
  docker compose exec api python scripts/create_admin.py <username> <password>
  หรือรัน local: python scripts/create_admin.py <username> <password>
"""
import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.admin import AdminAccount


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: python scripts/create_admin.py <username> <password>")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]
    if len(password) < 8:
        print("Password must be at least 8 characters")
        sys.exit(1)

    db = SessionLocal()
    try:
        if db.query(AdminAccount).filter(AdminAccount.username == username).first():
            print(f"Admin account '{username}' already exists")
            sys.exit(1)

        admin = AdminAccount(username=username, password_hash=hash_password(password))
        db.add(admin)
        db.commit()
        print(f"Admin account '{username}' created successfully")
    finally:
        db.close()


if __name__ == "__main__":
    main()
