from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_DEMUXER_WHITELIST = "matroska,webm,mov,mp4,m4a,3gp,3g2,mj2,ogg,mp3,aac,wav,flac"


class ConversionError(Exception):
    """แปลงไม่สำเร็จเพราะไฟล์มีปัญหา (เสียหาย ไม่มีเสียง ไม่ใช่เสียงจริง หรือแปลงนานเกินไป)"""


class ConverterUnavailableError(Exception):
    """เครื่องนี้ไม่มี ffmpeg (ปัญหาฝั่งเซิร์ฟเวอร์ ไม่ใช่ไฟล์ของผู้ใช้)"""


def ffmpeg_available() -> bool:
    return shutil.which(get_settings().ffmpeg_path) is not None


def convert_to_wav(file_bytes: bytes, max_duration_seconds: float) -> bytes:
    """คืนไบต์ของไฟล์ WAV (float32) จากเสียงแทร็กแรก ตัดเหลือไม่เกิน max_duration_seconds"""
    settings = get_settings()
    ffmpeg = shutil.which(settings.ffmpeg_path)
    if ffmpeg is None:
        raise ConverterUnavailableError(f"ffmpeg not found (FFMPEG_PATH={settings.ffmpeg_path!r})")

    # ใช้ไฟล์ชั่วคราวทั้งขาเข้าและขาออก ไม่ใช้ pipe เพราะไฟล์ .m4a/.mp4 บางไฟล์เก็บ index ไว้ท้ายไฟล์ ต้อง seek ได้
    with tempfile.TemporaryDirectory(prefix="audio-convert-") as tmp:
        src, dst = Path(tmp) / "input", Path(tmp) / "output.wav"
        src.write_bytes(file_bytes)
        command = [
            ffmpeg, "-nostdin", "-v", "error", "-y",
            "-format_whitelist", _DEMUXER_WHITELIST,
            "-protocol_whitelist", "file",
            "-i", str(src),
            "-vn", "-map", "0:a:0",  # เอาเฉพาะแทร็กเสียงแรก
            "-t", str(max_duration_seconds),  # ตัดความยาวเอาแค่ max_duration_seconds
            "-c:a", "pcm_f32le", "-f", "wav", str(dst),
        ]
        try:
            result = subprocess.run(
                command, capture_output=True, timeout=settings.ffmpeg_timeout_seconds, check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise ConversionError(f"ffmpeg timed out after {settings.ffmpeg_timeout_seconds:g}s") from exc
        except OSError as exc:  # เช่น ไม่มีสิทธิ์รัน
            raise ConverterUnavailableError(f"cannot run ffmpeg: {exc}") from exc

        if result.returncode != 0 or not dst.exists():
            detail = result.stderr.decode("utf-8", errors="replace").strip()[-500:]
            raise ConversionError(f"ffmpeg exited with {result.returncode}: {detail}")
        return dst.read_bytes()
