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

class AdminUserOut(BaseModel):
    """ผู้ใช้ 1 คนในมุมมองของ admin (ไม่มี password_hash)"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str | None
    created_at: datetime
    last_login_at: datetime | None
    is_active: bool
    detection_count: int  # จำนวนครั้งที่ผู้ใช้คนนี้ตรวจเสียงขณะ login

class AdminUserListOut(BaseModel):
    items: list[AdminUserOut]
    total: int  # จำนวนทั้งหมดที่ตรงกับ filter (ไม่ใช่แค่หน้านี้)
    limit: int
    offset: int