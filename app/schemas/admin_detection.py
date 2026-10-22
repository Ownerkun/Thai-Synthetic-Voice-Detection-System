from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminDetectionFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


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
