"""
AudioPreprocessor — Data Cleaning decode -> to_mono -> resample -> trim_silence -> normalize_loudness -> enforce_max_duration
"""
from __future__ import annotations

import io
import logging
import os

import numpy as np
import soundfile as sf

from app.core.config import get_settings
from app.services.audio_types import AudioBuffer

logger = logging.getLogger(__name__)


class UnsupportedAudioError(ValueError):
    """ไฟล์เสียงไม่ผ่านการตรวจสอบรูปแบบ, ขนาด"""


class AudioPreprocessor:
    def __init__(
        self,
        target_sample_rate: int | None = None,
        max_duration_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self.target_sample_rate = target_sample_rate or settings.target_sample_rate
        self.max_duration_seconds = max_duration_seconds or settings.max_duration_seconds
        self._allowed_ext = settings.allowed_audio_extensions
        self._max_bytes = settings.max_upload_size_bytes

    def validate_format(self, filename: str, file_size_bytes: int) -> bool:
        ext = os.path.splitext(filename.lower())[1]
        if ext not in self._allowed_ext:
            return False
        if file_size_bytes <= 0 or file_size_bytes > self._max_bytes:
            return False
        return True

    def decode(self, file_bytes: bytes, source_format: str) -> AudioBuffer:
        try:
            waveform, sample_rate = sf.read(io.BytesIO(file_bytes), dtype="float32", always_2d=False)
        except Exception as exc:  # noqa: BLE001 — ห่อ error ของ libsndfile ให้เป็นข้อความที่ API เข้าใจ
            raise UnsupportedAudioError(f"Failed to read audio file: {exc}") from exc
        return AudioBuffer(waveform=np.asarray(waveform, dtype=np.float32), sample_rate=sample_rate, source_format=source_format)

    def to_mono(self, buffer: AudioBuffer) -> AudioBuffer:
        wf = buffer.waveform
        if wf.ndim > 1:
            wf = wf.mean(axis=1)
        return AudioBuffer(waveform=wf.astype(np.float32), sample_rate=buffer.sample_rate, source_format=buffer.source_format)

    def resample(self, buffer: AudioBuffer) -> AudioBuffer:
        if buffer.sample_rate == self.target_sample_rate:
            return buffer
        wf = _resample_signal(buffer.waveform, buffer.sample_rate, self.target_sample_rate)
        return AudioBuffer(waveform=wf.astype(np.float32), sample_rate=self.target_sample_rate, source_format=buffer.source_format)

    def trim_silence(self, buffer: AudioBuffer, threshold_db: float = -40.0, frame_ms: float = 20.0) -> AudioBuffer:
        """ตัดช่วงเงียบต้นและท้ายด้วย energy-based VAD อย่างง่าย (RMS ต่อเฟรม เทียบ threshold_db)"""
        wf = buffer.waveform
        if len(wf) == 0:
            return buffer
        frame_len = max(1, int(buffer.sample_rate * frame_ms / 1000))
        n_frames = max(1, len(wf) // frame_len)
        trimmed = wf[: n_frames * frame_len].reshape(n_frames, frame_len)
        rms = np.sqrt(np.mean(trimmed**2, axis=1) + 1e-12)
        db = 20 * np.log10(rms + 1e-12)
        voiced = np.where(db > threshold_db)[0]
        if len(voiced) == 0:
            # ทั้งไฟล์เงียบ คืนสัญญาณเดิมโดยไม่ตัด กันเคส waveform ว่างเปล่า
            return buffer
        start = voiced[0] * frame_len
        end = min(len(wf), (voiced[-1] + 1) * frame_len)
        return AudioBuffer(waveform=wf[start:end], sample_rate=buffer.sample_rate, source_format=buffer.source_format)

    def normalize_loudness(self, buffer: AudioBuffer, target_dbfs: float = -23.0) -> AudioBuffer:
        """ปรับระดับความดังแบบ RMS-normalize สู่ค่าเป้าหมาย (ประมาณ LUFS)
        หมายเหตุ: เป็นการประมาณอย่างง่าย ถ้าต้องการความแม่นยำระดับ ITU-R BS.1770
        ค่อยพิจารณาเปลี่ยนไปใช้ไลบรารี pyloudnorm """
        wf = buffer.waveform
        rms = np.sqrt(np.mean(wf**2) + 1e-12)
        if rms < 1e-9:
            return buffer
        current_dbfs = 20 * np.log10(rms)
        gain_db = target_dbfs - current_dbfs
        gain = 10 ** (gain_db / 20)
        normalized = np.clip(wf * gain, -1.0, 1.0)
        return AudioBuffer(waveform=normalized.astype(np.float32), sample_rate=buffer.sample_rate, source_format=buffer.source_format)

    def enforce_max_duration(self, buffer: AudioBuffer) -> AudioBuffer:
        max_samples = int(self.max_duration_seconds * buffer.sample_rate)
        if len(buffer.waveform) <= max_samples:
            return buffer
        logger.info("Audio trimmed from %.2fs to %.2fs", buffer.duration_seconds, self.max_duration_seconds)
        return AudioBuffer(
            waveform=buffer.waveform[:max_samples], sample_rate=buffer.sample_rate, source_format=buffer.source_format
        )

    def process(self, file_bytes: bytes, filename: str) -> AudioBuffer:
        ext = os.path.splitext(filename.lower())[1].lstrip(".")
        buffer = self.decode(file_bytes, source_format=ext)
        buffer = self.to_mono(buffer)
        buffer = self.resample(buffer)
        buffer = self.trim_silence(buffer)
        buffer = self.normalize_loudness(buffer)
        buffer = self.enforce_max_duration(buffer)
        return buffer


def _resample_signal(waveform: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """resample โดยพยายามใช้ soxr ก่อน แล้วค่อย fallback ไป scipy
    เพื่อไม่ให้ image ล้มเวลา build ถ้าแพลตฟอร์มไหนไม่มี wheel ของ soxr พร้อมใช้"""
    try:
        import soxr

        return soxr.resample(waveform, orig_sr, target_sr)
    except ImportError:
        from scipy.signal import resample_poly
        from math import gcd

        g = gcd(orig_sr, target_sr)
        return resample_poly(waveform, target_sr // g, orig_sr // g)
