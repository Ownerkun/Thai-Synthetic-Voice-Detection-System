import io

import numpy as np
import pytest
import soundfile as sf

from app.core.config import get_settings
from app.services.audio_preprocessor import AudioPreprocessor, UnsupportedAudioError
from app.services.audio_types import FailureReason
from tests.conftest import make_wav_bytes


def _wav_with_no_samples() -> bytes:
    """A perfectly valid WAV file whose audio part is empty"""
    buf = io.BytesIO()
    sf.write(buf, np.zeros(0, dtype=np.float32), 16000, format="WAV")
    return buf.getvalue()


# ---------- decode() ----------


def test_garbage_bytes_fail_with_decode_failed():
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().process(b"this is not audio at all" * 50, "fake.wav")
    assert err.value.reason == FailureReason.DECODE_FAILED


def test_decode_failure_message_does_not_leak_library_internals():
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().process(b"this is not audio at all" * 50, "fake.wav")
    assert "BytesIO" not in str(err.value)
    assert "libsndfile" not in str(err.value).lower()


def test_valid_file_with_zero_samples_fails_with_empty_audio():
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().process(_wav_with_no_samples(), "silence_of_nothing.wav")
    assert err.value.reason == FailureReason.EMPTY_AUDIO


def test_valid_wav_still_processes():
    buffer = AudioPreprocessor().process(make_wav_bytes(), "ok.wav")
    assert len(buffer.waveform) > 0


# ---------- validate_format() ----------


def test_validate_format_rejects_wrong_extension():
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().validate_format("clip.mp3", 1000)
    assert err.value.reason == FailureReason.UNSUPPORTED_FORMAT
    assert ".mp3" in str(err.value)


def test_validate_format_rejects_file_without_extension():
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().validate_format("recording", 1000)
    assert err.value.reason == FailureReason.UNSUPPORTED_FORMAT
    assert "(none)" in str(err.value)


def test_validate_format_rejects_zero_byte_file():
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().validate_format("clip.wav", 0)
    assert err.value.reason == FailureReason.EMPTY_AUDIO


def test_validate_format_rejects_file_over_the_size_limit(monkeypatch):
    monkeypatch.setattr(
        get_settings(), "max_upload_size_bytes", 1000
    )  # AudioPreprocessor reads it in __init__
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().validate_format("clip.wav", 1001)
    assert err.value.reason == FailureReason.FILE_TOO_LARGE


def test_validate_format_accepts_wav_and_flac_in_any_letter_case():
    AudioPreprocessor().validate_format("A.WAV", 1000)  # must not raise
    AudioPreprocessor().validate_format("b.flac", 1000)


def test_extension_is_checked_before_size():
    with pytest.raises(UnsupportedAudioError) as err:
        AudioPreprocessor().validate_format("clip.mp3", 0)
    assert err.value.reason == FailureReason.UNSUPPORTED_FORMAT
