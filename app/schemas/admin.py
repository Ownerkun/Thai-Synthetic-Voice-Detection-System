from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ThresholdUpdateRequest(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    note: str | None = None


class ThresholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    value: float
    effective_from: datetime
    changed_by_admin_id: UUID
    note: str | None


class ThresholdUpdateResponse(BaseModel):
    previous_value: float | None
    current: ThresholdOut


class StatsOverviewOut(BaseModel):
    total_detections: int
    total_spoof_verdicts: int
    total_real_verdicts: int
    total_users: int
    feedback_agreement_rate: float | None  # None ถ้ายังไม่มี feedback
