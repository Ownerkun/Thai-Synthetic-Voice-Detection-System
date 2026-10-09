import os

# ต้องตั้ง env ก่อน import app ใด ๆ เพราะ Settings ถูก cache ไว้ตอน import ครั้งแรก
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_smoke.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("BOOTSTRAP_ADMIN_USERNAME", "admin")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "test-admin-pass-123")
os.environ.setdefault(
    "ONNX_MODEL_PATH", "/tmp/does-not-exist.onnx"
)  # บังคับให้ใช้ MockSpoofAnalyzer ตอนเทส

import io
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


def register_and_get_headers(client) -> dict:
    email = f"{uuid.uuid4().hex[:12]}@example.com"
    res = client.post(
        "/auth/register", json={"email": email, "password": "Password1234"}
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


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
