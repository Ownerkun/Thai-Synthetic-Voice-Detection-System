import io

import numpy as np
import soundfile as sf

from app.core.config import get_settings
from tests.conftest import make_wav_bytes, register_and_get_headers


def _post(client, *named_files: tuple[str, bytes], headers: dict | None = None):
    files = [("files", (name, data, "audio/wav")) for name, data in named_files]
    return client.post("/predict", files=files, headers=headers)


def _wav_with_no_samples() -> bytes:
    buf = io.BytesIO()
    sf.write(buf, np.zeros(0, dtype=np.float32), 16000, format="WAV")
    return buf.getvalue()


def test_unsupported_extension_is_reported_with_reason(client):
    res = _post(client, ("clip.mp3", b"whatever"))
    assert res.status_code == 200
    body = res.json()
    assert body["results"] == []
    assert len(body["failed_files"]) == 1
    failure = body["failed_files"][0]
    assert failure["filename"] == "clip.mp3"
    assert failure["reason"] == "unsupported_format"
    assert ".mp3" in failure["message"]


def test_failed_file_has_exactly_filename_reason_and_message(client):
    failure = _post(client, ("clip.mp3", b"whatever")).json()["failed_files"][0]
    assert set(failure.keys()) == {"filename", "reason", "message"}


def test_zero_byte_file_is_reported_as_empty_audio(client):
    failure = _post(client, ("empty.wav", b"")).json()["failed_files"][0]
    assert failure["reason"] == "empty_audio"


def test_valid_file_with_no_samples_is_reported_as_empty_audio_not_analysed(client):
    body = _post(client, ("nothing.wav", _wav_with_no_samples())).json()
    assert body["results"] == []  # must not get a real/spoof verdict for nothing
    assert body["failed_files"][0]["reason"] == "empty_audio"


def test_corrupted_file_is_reported_as_decode_failed_without_leaking_internals(client):
    failure = _post(client, ("broken.wav", b"this is not audio at all" * 50)).json()[
        "failed_files"
    ][0]
    assert failure["reason"] == "decode_failed"
    assert "BytesIO" not in failure["message"]


def test_file_over_the_size_limit_is_reported_as_file_too_large(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_upload_size_bytes", 1000)
    failure = _post(client, ("big.wav", make_wav_bytes())).json()["failed_files"][0]
    assert failure["reason"] == "file_too_large"


def test_mixed_batch_keeps_the_good_file_and_explains_every_bad_one(client):
    body = _post(
        client,
        ("good.wav", make_wav_bytes()),
        ("bad.mp3", b"x"),
        ("broken.wav", b"garbage" * 10),
    ).json()
    assert [r["original_filename"] for r in body["results"]] == ["good.wav"]
    reasons = {f["filename"]: f["reason"] for f in body["failed_files"]}
    assert reasons == {"bad.mp3": "unsupported_format", "broken.wav": "decode_failed"}


def test_successful_upload_has_empty_failed_files(client):
    body = _post(client, ("good.wav", make_wav_bytes())).json()
    assert len(body["results"]) == 1
    assert body["failed_files"] == []


def test_rejected_file_is_not_saved_to_history(client):
    headers = register_and_get_headers(client)
    _post(client, ("bad.mp3", b"x"), ("broken.wav", b"garbage" * 10), headers=headers)
    assert client.get("/history", headers=headers).json() == []
