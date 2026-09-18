"""
Smoke test ครอบคลุม end-to-end pipeline หลักของ API:
สมัคร/login -> /predict (มี+ไม่มี token) -> /history -> feedback -> admin login -> threshold -> stats
รันด้วย: pytest -q   (ใช้ sqlite แทน postgres เฉพาะตอนเทส ผ่าน app/core/types.GUID)
"""
from tests.conftest import make_wav_bytes


def test_health_uses_mock_model_when_no_onnx_file(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["using_mock_model"] is True


def test_predict_anonymous_not_saved_to_history(client):
    wav_bytes = make_wav_bytes()
    res = client.post("/predict", files={"files": ("clip.wav", wav_bytes, "audio/wav")})
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["results"]) == 1
    result = body["results"][0]
    assert result["saved_to_history"] is False
    assert result["duration_seconds"] <= 10.0
    assert result["num_segments"] >= 1
    assert 0.0 <= result["mean_probability"] <= 1.0


def test_register_login_predict_and_history_flow(client):
    register_res = client.post(
        "/auth/register", json={"email": "student@example.com", "password": "S3cur3Passw0rd!"}
    )
    assert register_res.status_code == 201, register_res.text
    token = register_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    wav_bytes = make_wav_bytes(duration_seconds=3.0)
    predict_res = client.post(
        "/predict", files={"files": ("mine.wav", wav_bytes, "audio/wav")}, headers=headers
    )
    assert predict_res.status_code == 200, predict_res.text
    result = predict_res.json()["results"][0]
    assert result["saved_to_history"] is True
    detection_id = result["id"]

    history_res = client.get("/history", headers=headers)
    assert history_res.status_code == 200
    assert any(item["id"] == detection_id for item in history_res.json())

    detail_res = client.get(f"/history/{detection_id}", headers=headers)
    assert detail_res.status_code == 200
    assert len(detail_res.json()["segments"]) == result["num_segments"]

    feedback_res = client.post(f"/history/{detection_id}/feedback", json={"user_agrees": True}, headers=headers)
    assert feedback_res.status_code == 201, feedback_res.text

    # ยืนยันว่าจำกัดสิทธิ์จริง: token ผู้ใช้ต้องไม่สามารถเรียก endpoint แอดมินได้
    forbidden_res = client.get("/admin/stats", headers=headers)
    assert forbidden_res.status_code == 401


def test_history_and_admin_require_login_return_401_not_422(client):
    """กันบั๊ก: ถ้าไม่ส่ง Authorization header เลย ต้องได้ 401 (ตาม error contract ที่ frontend คาดไว้)
    ไม่ใช่ 422 จาก FastAPI validation layer (เคยเกิดเพราะลืมใส่ default=None ให้ Header())"""
    assert client.get("/history").status_code == 401
    assert client.get("/admin/stats").status_code == 401
    assert client.get("/admin/threshold").status_code == 401
    assert client.post("/admin/threshold", json={"value": 0.5}).status_code == 401


def test_admin_login_and_threshold_update_affects_next_predict(client):
    admin_login_res = client.post(
        "/auth/admin/login", json={"username": "admin", "password": "test-admin-pass-123"}
    )
    assert admin_login_res.status_code == 200, admin_login_res.text
    admin_headers = {"Authorization": f"Bearer {admin_login_res.json()['access_token']}"}

    update_res = client.post(
        "/admin/threshold", json={"value": 0.9, "note": "pytest smoke test"}, headers=admin_headers
    )
    assert update_res.status_code == 200, update_res.text
    assert update_res.json()["current"]["value"] == 0.9

    # threshold ใหม่ต้องมีผลกับคำขอ /predict ถัดไปทันที โดยไม่ต้อง restart
    wav_bytes = make_wav_bytes()
    predict_res = client.post("/predict", files={"files": ("after_threshold.wav", wav_bytes, "audio/wav")})
    assert predict_res.json()["results"][0]["threshold_used"] == 0.9

    stats_res = client.get("/admin/stats", headers=admin_headers)
    assert stats_res.status_code == 200
    assert stats_res.json()["total_detections"] >= 3


def test_predict_rejects_unsupported_extension(client):
    res = client.post("/predict", files={"files": ("clip.mp3", b"not-really-audio", "audio/mpeg")})
    assert res.status_code == 200
    body = res.json()
    assert body["results"] == []
    assert "clip.mp3" in body["failed_files"]
