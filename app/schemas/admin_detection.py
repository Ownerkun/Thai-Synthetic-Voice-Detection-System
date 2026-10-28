from datetime import datetime, date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AdminDetectionFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    # --- เรียงลำดับ (ค่าเริ่มต้น = ใหม่สุดก่อน) ---
    sort: Literal["created_at", "mean_probability", "processing_ms"] = "created_at"
    order: Literal["asc", "desc"] = "desc"

    # --- filter (ใส่เฉพาะที่ต้องการ ใส่หลายตัวพร้อมกัน = ต้องตรงทุกเงื่อนไข) ---
    verdict: Literal["real", "spoof"] | None = None
    # วันที่ตามเวลาไทย (UTC+7) นับรวมทั้งวัน เช่น date_from=2026-10-01&date_to=2026-10-01 = ทั้งวันที่ 1 ต.ค.
    date_from: date | None = None
    date_to: date | None = None
    q: str | None = Field(default=None, min_length=1, max_length=100, description="ค้นหาจากชื่อไฟล์ (บางส่วน ไม่สนตัวพิมพ์)")

    user_id: UUID | None = None  # ผลตรวจของผู้ใช้คนนี้คนเดียว (ใช้ลิงก์มาจากหน้าจัดการผู้ใช้)
    user_email: str | None = Field(default=None, min_length=1, max_length=255, description="ค้นหาจากอีเมลผู้ใช้ (บางส่วน ไม่สนตัวพิมพ์)")
    guest: bool | None = Field(default=None, description="true = เฉพาะที่ไม่ได้ login, false = เฉพาะที่ login")
    model_version: str | None = Field(default=None, min_length=1, max_length=50, description="ตรงทุกตัวอักษร")
    partial_spoof: bool | None = Field(default=None, description="true = เฉพาะที่ระบบสงสัยว่าปลอมบางช่วง")
    
    # ช่วงของ mean_probability (ความน่าจะเป็นที่เป็นเสียงปลอมโดยเฉลี่ย) 0.0 - 1.0
    feedback: Literal["agree", "disagree", "none"] | None = Field(
        default=None, description="agree/disagree = ผู้ใช้กด feedback แบบนั้น, none = ยังไม่มี feedback")
    min_prob: float | None = Field(default=None, ge=0.0, le=1.0)
    max_prob: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def check_date_range(self) -> "AdminDetectionFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        if self.min_prob is not None and self.max_prob is not None and self.min_prob > self.max_prob:
            raise ValueError("min_prob must not be greater than max_prob")
        return self


class AdminDetectionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    original_filename: str
    duration_seconds: float
    num_segments: int
    mean_probability: float
    max_probability: float
    threshold_used: float
    verdict: str  # "real" | "spoof"
    possible_partial_spoof: bool
    model_version: str
    processing_ms: int
    user_id: UUID | None
    user_email: str | None
    feedback: Literal["agree", "disagree"] | None  # None = ยังไม่มี feedback


class AdminDetectionListOut(BaseModel):
    items: list[AdminDetectionItemOut]
    total: int  # จำนวนที่ตรงกับ filter ทั้งหมด
    limit: int
    offset: int

class AdminDetectionDetailOut(AdminDetectionItemOut):
    sample_rate: int
    file_size_bytes: int
    audio_format: str
    feedback_created_at: datetime | None
    feedback_updated_at: datetime | None
