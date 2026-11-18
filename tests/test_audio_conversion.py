"""แปลงไฟล์เสียงนามสกุลอื่นด้วย ffmpeg (mp3, m4a, aac, ogg, opus, webm, mp4)

เทสต์ที่ต้องใช้ ffmpeg จริงจะถูกข้ามถ้าเครื่องนี้ไม่มี ffmpeg (ใน Docker image มีให้แล้ว)
"""
import shutil
import stat
import subprocess
import time

import numpy as np
import pytest

from app.core.config import get_settings
from app.services import audio_preprocessor
from app.services.audio_preprocessor import AudioPreprocessor, UnsupportedAudioError
from app.services.audio_types import FailureReason
from tests.conftest import admin_login_headers, make_wav_bytes, register_and_get_headers

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed on this machine")

# นามสกุล -> ตัวเข้ารหัสของ ffmpeg (None = ใช้ค่าเริ่มต้นของนามสกุลนั้น)
ENCODERS = {"mp3": None, "m4a": None, "aac": "aac", "ogg": None, "opus": "libopus", "webm": "libopus", "mp4": "aac"}
FREQ = 440.0


def make_audio(ext: str, tmp_path, duration: float = 2.0, channels: int = 2, sample_rate: int = 44100) -> bytes:
    """สร้างไฟล์เสียงคลื่นไซน์ 440 Hz ด้วย ffmpeg (ข้ามเทสต์ถ้า ffmpeg เครื่องนี้เข้ารหัสนามสกุลนี้ไม่ได้)"""
    out = tmp_path / f"tone.{ext}"
    command = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency={FREQ}:duration={duration}:sample_rate={sample_rate}",
               "-ac", str(channels)]
    if ENCODERS[ext]:
        command += ["-c:a", ENCODERS[ext]]
    result = subprocess.run(command + [str(out)], capture_output=True)
    if result.returncode != 0:
        pytest.skip(f"this ffmpeg cannot encode .{ext}: {result.stderr.decode()[-200:]}")
    return out.read_bytes()


def dominant_frequency(waveform: np.ndarray, sample_rate: int) -> float:
    spectrum = np.abs(np.fft.rfft(waveform * np.hanning(len(waveform))))
    return float(np.fft.rfftfreq(len(waveform), 1 / sample_rate)[spectrum.argmax()])


# ---------- แปลงได้จริง: เสียงที่ออกมาต้องเป็น 16 kHz mono และเป็นเสียงเดิม (ความถี่ 440 Hz) ----------


@needs_ffmpeg
@pytest.mark.parametrize("ext", list(ENCODERS))
def test_each_format_is_converted_to_16khz_mono_with_the_same_sound(ext, tmp_path):
    buffer = AudioPreprocessor().process(make_audio(ext, tmp_path), f"clip.{ext}")
    assert buffer.sample_rate == 16000
    assert buffer.waveform.ndim == 1
    assert buffer.source_format == ext
    assert buffer.duration_seconds == pytest.approx(2.0, abs=0.15)
    assert dominant_frequency(buffer.waveform, buffer.sample_rate) == pytest.approx(FREQ, abs=5)


@needs_ffmpeg
def test_m4a_with_index_at_the_end_of_the_file_is_converted(tmp_path):
    # ffmpeg เขียน index ของ .m4a/.mp4 (moov) ไว้ท้ายไฟล์เป็นค่าเริ่มต้น ถ้าส่งเข้า ffmpeg ทาง pipe จะอ่านไม่ได้
    data = make_audio("m4a", tmp_path)
    assert data.rfind(b"moov") > data.find(b"mdat"), "precondition: this test file must have moov after mdat"
    assert len(AudioPreprocessor().process(data, "clip.m4a").waveform) > 0


@needs_ffmpeg
def test_long_file_is_cut_to_the_max_duration_while_converting(tmp_path):
    # เรียก decode() ตรง ๆ (ก่อนขั้น enforce_max_duration) เพื่อพิสูจน์ว่าตัดตั้งแต่ตอนถอดรหัส ไม่ใช่ถอดทั้งไฟล์แล้วค่อยตัด
    buffer = AudioPreprocessor().decode(make_audio("mp3", tmp_path, duration=15), "mp3")
    assert buffer.duration_seconds == pytest.approx(get_settings().max_duration_seconds, abs=0.05)


@needs_ffmpeg
def test_mono_and_stereo_inputs_both_come_out_mono(tmp_path):
    for channels in (1, 2):
        buffer = AudioPreprocessor().process(make_audio("ogg", tmp_path, channels=channels), "clip.ogg")
        assert buffer.waveform.ndim == 1


# ---------- นามสกุลไม่ตรงกับเนื้อไฟล์ (เบราว์เซอร์อัดเสียงได้ webm แต่ frontend ตั้งชื่อ .wav) ----------


@needs_ffmpeg
def test_webm_recording_named_wav_is_still_decoded(tmp_path):
    buffer = AudioPreprocessor().process(make_audio("webm", tmp_path), "recording.wav")
    assert buffer.sample_rate == 16000
    assert dominant_frequency(buffer.waveform, buffer.sample_rate) == pytest.approx(FREQ, abs=5)
    assert buffer.source_format == "wav"  # ยึดนามสกุลที่ผู้ใช้ส่งมา


@needs_ffmpeg
def test_wav_named_mp3_is_still_decoded():
    assert len(AudioPreprocessor().process(make_wav_bytes(), "clip.mp3").waveform) > 0


# ---------- ไฟล์ที่ไม่ใช่เสียงจริง / อันตราย ----------


@needs_ffmpeg
@pytest.mark.parametrize("name", ["fake.mp3", "fake.webm", "fake.m4a", "fake.ogg"])
def test_garbage_bytes_fail_with_decode_failed_and_do_not_leak_ffmpeg_output(name):
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().process(b"this is not audio at all" * 50, name)
    assert err.value.reason == FailureReason.DECODE_FAILED
    assert "ffmpeg" not in str(err.value).lower()


@needs_ffmpeg
@pytest.mark.parametrize(
    "playlist",
    [
        b"#EXTM3U\n#EXT-X-TARGETDURATION:10\n#EXTINF:10,\nfile:///etc/passwd\n#EXT-X-ENDLIST\n",
        b"ffconcat version 1.0\nfile '/etc/hostname'\n",
    ],
    ids=["hls-playlist", "concat-list"],
)
def test_playlist_files_that_point_at_other_files_are_rejected(playlist):
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().process(playlist, "evil.webm")
    assert err.value.reason == FailureReason.DECODE_FAILED


@needs_ffmpeg
def test_video_without_any_audio_track_fails_with_decode_failed(tmp_path):
    video = tmp_path / "silent.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:d=1:s=64x64", "-an", str(video)], check=True)
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().process(video.read_bytes(), "silent.mp4")
    assert err.value.reason == FailureReason.DECODE_FAILED


# ---------- ffmpeg ไม่มี / ค้าง (ไม่ต้องใช้ ffmpeg จริง) ----------


def test_wav_and_flac_never_need_ffmpeg(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("ffmpeg must not be used for a valid .wav")

    monkeypatch.setattr(audio_preprocessor, "convert_to_wav", boom)
    assert len(AudioPreprocessor().process(make_wav_bytes(), "ok.wav").waveform) > 0


def test_long_wav_is_read_only_up_to_the_max_duration():
    buffer = AudioPreprocessor().decode(make_wav_bytes(duration_seconds=15), "wav")  # ก่อนขั้น enforce_max_duration
    assert buffer.duration_seconds == pytest.approx(get_settings().max_duration_seconds, abs=0.05)


@pytest.fixture
def no_ffmpeg(monkeypatch):
    monkeypatch.setattr(get_settings(), "ffmpeg_path", "/nonexistent/ffmpeg")


def test_format_that_needs_ffmpeg_reports_conversion_unavailable_when_it_is_missing(no_ffmpeg):
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().process(b"anything", "clip.m4a")
    assert err.value.reason == FailureReason.CONVERSION_UNAVAILABLE
    assert ".m4a" in str(err.value)
    assert "/nonexistent" not in str(err.value)  # path ภายในเครื่องไม่หลุดไปถึงผู้ใช้


def test_broken_wav_without_ffmpeg_is_still_decode_failed(no_ffmpeg):
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().process(b"this is not audio at all" * 50, "fake.wav")
    assert err.value.reason == FailureReason.DECODE_FAILED


def test_valid_wav_works_without_ffmpeg(no_ffmpeg):
    assert len(AudioPreprocessor().process(make_wav_bytes(), "ok.wav").waveform) > 0


def _fake_ffmpeg(tmp_path, body: str) -> str:
    script = tmp_path / "fake-ffmpeg"
    script.write_text(f"#!/bin/sh\n{body}\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


def test_ffmpeg_that_hangs_is_stopped_after_the_timeout(monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "ffmpeg_path", _fake_ffmpeg(tmp_path, "sleep 30"))
    monkeypatch.setattr(settings, "ffmpeg_timeout_seconds", 0.5)
    started = time.monotonic()
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().process(b"anything", "clip.mp3")
    assert err.value.reason == FailureReason.DECODE_FAILED
    assert time.monotonic() - started < 10


def test_ffmpeg_that_exits_without_output_is_decode_failed(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "ffmpeg_path", _fake_ffmpeg(tmp_path, "exit 0"))
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().process(b"anything", "clip.mp3")
    assert err.value.reason == FailureReason.DECODE_FAILED


# ---------- validate_format ----------


@pytest.mark.parametrize("ext", ["wav", "flac", "mp3", "m4a", "aac", "ogg", "opus", "webm", "mp4"])
def test_validate_format_accepts_every_supported_extension_in_any_letter_case(ext):
    AudioPreprocessor().validate_format(f"clip.{ext}", 1000)
    AudioPreprocessor().validate_format(f"CLIP.{ext.upper()}", 1000)


@pytest.mark.parametrize("name", ["notes.txt", "photo.png", "movie.avi", "archive.zip", "m3u.m3u8", "clip"])
def test_validate_format_still_rejects_other_files(name):
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().validate_format(name, 1000)
    assert err.value.reason == FailureReason.UNSUPPORTED_FORMAT


# ---------- ผ่าน endpoint ----------


def _post(client, *named_files: tuple[str, bytes], headers: dict | None = None):
    files = [("files", (name, data, "application/octet-stream")) for name, data in named_files]
    return client.post("/predict", files=files, headers=headers)


@needs_ffmpeg
def test_predict_accepts_a_batch_of_mixed_formats(client, tmp_path):
    names = [("a.wav", make_wav_bytes()), ("b.mp3", make_audio("mp3", tmp_path)), ("c.webm", make_audio("webm", tmp_path))]
    body = _post(client, *names).json()
    assert body["failed_files"] == []
    assert [r["original_filename"] for r in body["results"]] == ["a.wav", "b.mp3", "c.webm"]
    assert all(r["sample_rate"] == 16000 and r["num_segments"] >= 1 for r in body["results"])


@needs_ffmpeg
def test_converted_upload_is_saved_with_its_original_format(client, tmp_path):
    headers = register_and_get_headers(client)
    detection_id = _post(client, ("voice.m4a", make_audio("m4a", tmp_path)), headers=headers).json()["results"][0]["id"]
    detail = client.get(f"/admin/detections/{detection_id}", headers=admin_login_headers(client)).json()
    assert detail["audio_format"] == "m4a"
    assert detail["original_filename"] == "voice.m4a"


def test_predict_reports_conversion_unavailable_per_file_and_still_analyzes_the_rest(client, no_ffmpeg):
    body = _post(client, ("a.wav", make_wav_bytes()), ("b.m4a", b"anything")).json()
    assert [r["original_filename"] for r in body["results"]] == ["a.wav"]
    assert body["failed_files"] == [
        {"filename": "b.m4a", "reason": "conversion_unavailable", "message": body["failed_files"][0]["message"]}
    ]

