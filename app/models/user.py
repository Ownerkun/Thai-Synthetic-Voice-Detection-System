import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from app.core.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.detection import DetectionRecord, Feedback


class UserAccount(Base):
    """ผู้ใช้ทั่วไปเก็บเฉพาะอีเมล/รหัสผ่าน"""

    __tablename__ = "user_account"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # None = ยังไม่ได้ยืนยันอีเมล (login ไม่ได้) · บัญชีที่มีอยู่ก่อนมีระบบนี้ migration ตั้งให้เป็น "ยืนยันแล้ว"
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # token (JWT) ที่ออกก่อนเวลานี้ใช้ไม่ได้ ตั้งค่าตอนรีเซ็ตรหัสผ่านผ่านอีเมล
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    detection_records: Mapped[list["DetectionRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="user", cascade="all, delete-orphan")
