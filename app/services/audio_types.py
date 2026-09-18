"""
Type ภายในของ pipeline ตรวจสอบเสียง
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np


@dataclass
class AudioBuffer:

    waveform: np.ndarray
    sample_rate: int
    source_format: str

    @property
    def duration_seconds(self) -> float:
        return len(self.waveform) / float(self.sample_rate)

    def release(self) -> None:
        self.waveform = np.array([], dtype=np.float32)


@dataclass
class SegmentResult:
    index: int
    start_seconds: float
    end_seconds: float
    spoof_probability: float
    is_spoof: bool


@dataclass
class AnalysisReport:
    """ผลลัพธ์ชั่วคราวก่อนบันทึกลงฐานข้อมูล"""

    duration_seconds: float
    sample_rate: int
    num_segments: int
    mean_spoof_probability: float
    max_spoof_probability: float
    threshold: float
    verdict: str  # "real" | "spoof"
    possible_partial_spoof: bool
    model_version: str
    processing_ms: int
    segments: list[SegmentResult] = field(default_factory=list)

    def to_record_kwargs(
        self, *, user_id: uuid.UUID | None, original_filename: str, file_size_bytes: int, audio_format: str
    ) -> dict:
        """คืนค่าเป็น kwargs สำหรับสร้าง DetectionRecord เก็บเฉพาะ metadata, คะแนน"""
        return dict(
            user_id=user_id,
            original_filename=original_filename,
            duration_seconds=self.duration_seconds,
            sample_rate=self.sample_rate,
            file_size_bytes=file_size_bytes,
            audio_format=audio_format,
            num_segments=self.num_segments,
            mean_probability=self.mean_spoof_probability,
            max_probability=self.max_spoof_probability,
            threshold_used=self.threshold,
            verdict=self.verdict,
            possible_partial_spoof=self.possible_partial_spoof,
            model_version=self.model_version,
            processing_ms=self.processing_ms,
        )
