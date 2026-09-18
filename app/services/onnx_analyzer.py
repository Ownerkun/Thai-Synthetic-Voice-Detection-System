"""
*** สถานะตอนนี้: โมเดลยังอยู่ระหว่างเทรน***
ไฟล์นี้ออกแบบให้สลับไปมาระหว่าง 2 โหมดได้โดยไม่ต้องแก้โค้ดส่วนอื่น

1. RealOnnxSpoofAnalyzer ใช้จริงเมื่อมีไฟล์ ONNX_MODEL_PATH อยู่จริง (ผ่าน onnxruntime)
2. MockSpoofAnalyzer     ใช้ตอนยังไม่มีโมเดล คืนคะแนนหลอกที่ deterministic (สุ่มจาก hash ของสัญญาณเสียง)
                             เพื่อให้ frontend/backend/DB ทำงานร่วมกันได้ครบ pipeline ระหว่างรอโมเดลจริง

Endpoint และ service ชั้นบนเรียกผ่าน `get_analyzer()` เท่านั้น
เมื่อโมเดล .onnx เทรนเสร็จ ให้นำวางไฟล์ไว้ที่ ONNX_MODEL_PATH (ดู docker-compose volume `models`)
แล้วรีสตาร์ท container ระบบจะสลับไปใช้โมเดลจริงเอง
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from functools import lru_cache

import numpy as np

from app.core.config import get_settings
from app.services.audio_types import AnalysisReport, AudioBuffer, SegmentResult

logger = logging.getLogger(__name__)


class SpoofAnalyzer(ABC):
    model_version: str

    @abstractmethod
    def analyze(self, buffer: AudioBuffer, threshold: float) -> AnalysisReport: ...


def _softmax_temperature(logits: np.ndarray, temperature: float) -> np.ndarray:
    scaled = logits / max(temperature, 1e-6)
    scaled = scaled - np.max(scaled, axis=-1, keepdims=True)
    exp = np.exp(scaled)
    return exp / np.sum(exp, axis=-1, keepdims=True)


def _split_segments(waveform: np.ndarray, segment_samples: int) -> np.ndarray:
    """แบ่งเป็นช่วงความยาวคงที่ ถ้าสั้นกว่า 1 ช่วง ให้เติมด้วยการวนซ้ำสัญญาณ"""
    if len(waveform) == 0:
        waveform = np.zeros(segment_samples, dtype=np.float32)

    if len(waveform) < segment_samples:
        repeats = int(np.ceil(segment_samples / len(waveform)))
        waveform = np.tile(waveform, repeats)[:segment_samples]
        return waveform.reshape(1, segment_samples)

    n_segments = int(np.ceil(len(waveform) / segment_samples))
    padded_len = n_segments * segment_samples
    if padded_len > len(waveform):
        # ช่วงสุดท้ายเติมด้วยการวนซ้ำจากต้นสัญญาณ
        pad_needed = padded_len - len(waveform)
        waveform = np.concatenate([waveform, waveform[:pad_needed]])
    return waveform.reshape(n_segments, segment_samples)


def _build_report(
    *,
    segment_probs: np.ndarray,
    sample_rate: int,
    segment_samples: int,
    duration_seconds: float,
    threshold: float,
    model_version: str,
    processing_ms: int,
) -> AnalysisReport:
    seg_duration = segment_samples / sample_rate
    segments: list[SegmentResult] = []
    for i, prob in enumerate(segment_probs):
        start = i * seg_duration
        end = min(start + seg_duration, duration_seconds) if duration_seconds > start else start + seg_duration
        segments.append(
            SegmentResult(
                index=i,
                start_seconds=round(start, 3),
                end_seconds=round(end, 3),
                spoof_probability=float(prob),
                is_spoof=bool(prob >= threshold),
            )
        )

    mean_p = float(np.mean(segment_probs))
    max_p = float(np.max(segment_probs))
    verdict = "spoof" if mean_p >= threshold else "real"
    # เสียงมีทั้งช่วงที่คะแนนสูงและต่ำปนกันชัดเจนอาจเป็น partial spoof (ตัดต่อบางช่วง)
    possible_partial = bool(len(segments) > 1 and np.std(segment_probs) > 0.25)

    return AnalysisReport(
        duration_seconds=round(duration_seconds, 3),
        sample_rate=sample_rate,
        num_segments=len(segments),
        mean_spoof_probability=round(mean_p, 4),
        max_spoof_probability=round(max_p, 4),
        threshold=threshold,
        verdict=verdict,
        possible_partial_spoof=possible_partial,
        model_version=model_version,
        processing_ms=processing_ms,
        segments=segments,
    )


class RealOnnxSpoofAnalyzer(SpoofAnalyzer):
    """โหลด model.onnx จริงผ่าน ONNX Runtime"""

    def __init__(self, model_path: str, meta_path: str) -> None:
        import onnxruntime as ort

        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

        meta: dict = {}
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)

        settings = get_settings()
        self.sample_rate = int(meta.get("sample_rate", settings.target_sample_rate))
        self.segment_samples = int(meta.get("segment_samples", settings.segment_samples))
        self.temperature = float(meta.get("temperature", settings.inference_temperature))
        self.model_version = str(meta.get("model_version", settings.model_version))
        self.spoof_class_index = int(meta.get("spoof_class_index", 1))
        logger.info("Real ONNX model loaded: %s (version=%s)", model_path, self.model_version)

    def analyze(self, buffer: AudioBuffer, threshold: float) -> AnalysisReport:
        started = time.perf_counter()
        duration_seconds = buffer.duration_seconds
        segments = _split_segments(buffer.waveform, self.segment_samples)

        logits = self.session.run(None, {self.input_name: segments.astype(np.float32)})[0]
        probs = _softmax_temperature(np.asarray(logits), self.temperature)
        spoof_probs = probs[:, self.spoof_class_index]

        processing_ms = int((time.perf_counter() - started) * 1000)
        return _build_report(
            segment_probs=spoof_probs,
            sample_rate=self.sample_rate,
            segment_samples=self.segment_samples,
            duration_seconds=duration_seconds,
            threshold=threshold,
            model_version=self.model_version,
            processing_ms=processing_ms,
        )


class MockSpoofAnalyzer(SpoofAnalyzer):
    """คืนคะแนนหลอกแบบ deterministic (จาก hash ของสัญญาณเสียง) ไว้ทดสอบ pipeline"""

    def __init__(self) -> None:
        settings = get_settings()
        self.sample_rate = settings.target_sample_rate
        self.segment_samples = settings.segment_samples
        self.model_version = "mock-v0 (real model not yet available)"
        logger.warning(
            "ONNX model file not found — using MockSpoofAnalyzer as a temporary stand-in "
            "(results are simulated values, not real detection output)"
        )

    def analyze(self, buffer: AudioBuffer, threshold: float) -> AnalysisReport:
        started = time.perf_counter()
        duration_seconds = buffer.duration_seconds
        segments = _split_segments(buffer.waveform, self.segment_samples)

        spoof_probs = np.array(
            [self._pseudo_random_prob(seg, i) for i, seg in enumerate(segments)], dtype=np.float32
        )

        processing_ms = int((time.perf_counter() - started) * 1000)
        return _build_report(
            segment_probs=spoof_probs,
            sample_rate=self.sample_rate,
            segment_samples=self.segment_samples,
            duration_seconds=duration_seconds,
            threshold=threshold,
            model_version=self.model_version,
            processing_ms=processing_ms,
        )

    @staticmethod
    def _pseudo_random_prob(segment: np.ndarray, index: int) -> float:
        digest = hashlib.sha256(segment.tobytes() + index.to_bytes(4, "little")).digest()
        return int.from_bytes(digest[:4], "little") / 0xFFFFFFFF


@lru_cache
def get_analyzer() -> SpoofAnalyzer:
    """โหลดครั้งเดียวแล้ว cache ไว้ตลอดอายุ process สลับ Real/Mock ถ้ามีไฟล์โมเดล"""
    settings = get_settings()
    if os.path.exists(settings.onnx_model_path):
        try:
            return RealOnnxSpoofAnalyzer(settings.onnx_model_path, settings.onnx_model_meta_path)
        except Exception:  # noqa: BLE001 ถ้าโหลดโมเดลพัง ให้ fallback เป็น mock พร้อม log
            logger.exception("Failed to load ONNX model — falling back to MockSpoofAnalyzer")
    return MockSpoofAnalyzer()
