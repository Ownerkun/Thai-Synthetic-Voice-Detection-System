import os

# ต้องตั้ง env ก่อน import app ใด ๆ เพราะ Settings ถูก cache ไว้ตอน import ครั้งแรก
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_smoke.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("BOOTSTRAP_ADMIN_USERNAME", "admin")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "test-admin-pass-123")
# เทสต์ต้องไม่ส่งอีเมลจริงเด็ดขาด แม้ .env ของเครื่องนี้จะตั้ง MAIL_BACKEND=smtp ไว้ (จึงบังคับค่า ไม่ใช้ setdefault)
os.environ["MAIL_BACKEND"] = "memory"
os.environ["FRONTEND_BASE_URL"] = "http://frontend.test"
os.environ["EMAIL_TOKEN_COOLDOWN_SECONDS"] = "0"  # เทสต์ที่ตรวจช่วงรอจะตั้งค่าเองด้วย monkeypatch
os.environ.setdefault(
    "ONNX_MODEL_PATH", "/tmp/does-not-exist.onnx"
)  # บังคับให้ใช้ MockSpoofAnalyzer ตอนเทส

import io
import re
import uuid

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    # ลบ db ไฟล์เก่าก่อนรันชุดเทส กันข้อมูลค้างจากรันก่อนหน้า
    db_path = "./test_smoke.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    from app.main import app

    with TestClient(app) as c:
        yield c


def make_wav_bytes(
    duration_seconds: float = 2.0, sample_rate: int = 16000, freq: float = 220.0
) -> bytes:
    t = np.linspace(
        0, duration_seconds, int(sample_rate * duration_seconds), endpoint=False
    )
    waveform = 0.2 * np.sin(2 * np.pi * freq * t).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, waveform, sample_rate, format="WAV")
    return buf.getvalue()


def token_from_outbox(email: str, page: str) -> str:
    """หาโทเคนจากลิงก์ล่าสุดในอีเมลที่ "ส่ง" ถึง email (page = verify-email | reset-password)"""
    from app.services.mail_service import OUTBOX

    for mail in reversed(OUTBOX):
        if mail.to == email:
            match = re.search(rf"/{page}\?token=([\w-]+)", mail.text)
            if match:
                return match.group(1)
    raise AssertionError(f"no {page} email sent to {email}")


def register_verified(client, body: dict) -> dict:
    """สมัคร + กดลิงก์ยืนยันอีเมลจากอีเมลที่ส่งออก (ผ่าน flow จริง) แล้วคืน header ของผู้ใช้ที่ login แล้ว"""
    res = client.post("/auth/register", json=body)
    assert res.status_code == 201, res.text
    token = token_from_outbox(body["email"], "verify-email")
    res = client.post("/auth/verify-email", json={"token": token})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def register_and_get_headers(client) -> dict:
    email = f"{uuid.uuid4().hex[:12]}@example.com"
    return register_verified(client, {"email": email, "password": "Password1234"})


def predict_and_get_detection_id(
    client, headers: dict, filename: str = "clip.wav"
) -> str:
    res = client.post(
        "/predict",
        files={"files": (filename, make_wav_bytes(), "audio/wav")},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    return res.json()["results"][0]["id"]


def admin_login_headers(client) -> dict:
    res = client.post(
        "/auth/admin/login",
        json={"username": "admin", "password": "test-admin-pass-123"},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
