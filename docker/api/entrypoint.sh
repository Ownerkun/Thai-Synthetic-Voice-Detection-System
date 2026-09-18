#!/usr/bin/env bash
# รันตอน container "api" เริ่มทำงานทุกครั้ง (ทั้ง dev และ prod)
# 1) รอให้ฐานข้อมูลพร้อมรับการเชื่อมต่อ (กันเคส compose สั่งรันพร้อมกันแต่ postgres ยังไม่ตื่น)
# 2) รัน Alembic migration ให้ schema ล่าสุดเสมอ ก่อนเปิดรับ request จริง
# 3) ส่งต่อไปรันคำสั่งที่ CMD กำหนด (uvicorn)
set -euo pipefail

echo "[entrypoint] Waiting for database to be ready..."
python - <<'PY'
import sys
import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)

for attempt in range(1, 31):
    try:
        with engine.connect():
            print("[entrypoint] Database connection established")
            sys.exit(0)
    except OperationalError:
        print(f"[entrypoint] Database not ready (attempt {attempt}/30), retrying in 2s...")
        time.sleep(2)

print("[entrypoint] Failed to connect to database after 30 attempts", file=sys.stderr)
sys.exit(1)
PY

echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head

echo "[entrypoint] Starting application"
exec "$@"
