from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SegmentResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index: int
    start_seconds: float
    end_seconds: float
    spoof_probability: float
    is_spoof: bool


class DetectionResultOut(BaseModel):
    """Response ของ POST /predict ผลตรวจสอบไฟล์เดียว"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None  # None กรณีตรวจสอบแบบไม่ login และไม่ถูกบันทึก (ปัจจุบันบันทึกทุกกรณี แต่เผื่ออนาคต)
    original_filename: str
    duration_seconds: float
    sample_rate: int
    num_segments: int
    mean_probability: float
    max_probability: float
    threshold_used: float
    verdict: str
    possible_partial_spoof: bool
    model_version: str
    processing_ms: int
    segments: list[SegmentResultOut]
    saved_to_history: bool


class BatchDetectionResultOut(BaseModel):
    """Response เมื่ออัปโหลดหลายไฟล์พร้อมกัน"""

    results: list[DetectionResultOut]
    failed_files: list[str]  # ไฟล์ที่รูปแบบ/ขนาดไม่ถูกต้อง


class DetectionRecordOut(BaseModel):
    """รายการในหน้าประวัติ ไม่รวม segment รายละเอียด (ดูผ่าน /history/{id})"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    original_filename: str
    duration_seconds: float
    verdict: str
    mean_probability: float
    max_probability: float
    possible_partial_spoof: bool


class DetectionDetailOut(DetectionRecordOut):
    threshold_used: float
    model_version: str
    processing_ms: int
    segments: list[SegmentResultOut]
