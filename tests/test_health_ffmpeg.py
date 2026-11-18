import shutil

from app.core.config import get_settings


def test_health_tells_whether_ffmpeg_is_available(client, monkeypatch):
    assert client.get("/health").json()["ffmpeg_available"] is (shutil.which("ffmpeg") is not None)
    monkeypatch.setattr(get_settings(), "ffmpeg_path", "/nonexistent/ffmpeg")
    assert client.get("/health").json()["ffmpeg_available"] is False
