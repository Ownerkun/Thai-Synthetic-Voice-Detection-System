from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

class AdminUserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # ฟิลด์แปลก (เช่น email, password_hash) -> 422

    display_name: str | None = Field(default=None, min_length=1, max_length=100)  # ส่ง null = ล้างชื่อ
    is_active: bool | None = None  # false = ระงับ, true = เปิดใช้อีกครั้ง

    @model_validator(mode="after")
    def check_fields(self) -> "AdminUserUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Send at least one field to update: display_name or is_active")
        if "is_active" in self.model_fields_set and self.is_active is None:
            raise ValueError("is_active must be true or false")
        return self