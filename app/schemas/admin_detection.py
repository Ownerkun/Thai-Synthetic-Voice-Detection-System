from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AdminDetectionFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    # --- filter (ใส่เฉพาะที่ต้องการ ใส่หลายตัวพร้อมกัน = ต้องตรงทุกเงื่อนไข) ---
    verdict: Literal["real", "spoof"] | None = None
    # วันที่ตามเวลาไทย (UTC+7) นับรวมทั้งวัน เช่น date_from=2026-10-01&date_to=2026-10-01 = ทั้งวันที่ 1 ต.ค.
    date_from: date | None = None
    date_to: date | None = None
    q: str | None = Field(default=None, min_length=1, max_length=100, description="ค้นหาจากชื่อไฟล์ (บางส่วน ไม่สนตัวพิมพ์)")

    @model_validator(mode="after")
    def check_date_range(self) -> "AdminDetectionFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
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
