import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from app.core.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AdminAccount(Base):
    __tablename__ = "admin_account"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    threshold_changes: Mapped[list["ThresholdSetting"]] = relationship(back_populates="changed_by")


class ThresholdSetting(Base):
    """เก็บเป็นประวัติทุกครั้งที่แก้ไข ไม่ทับค่าเดิม เพื่อย้อนตรวจได้ว่าผลแต่ละครั้งใช้ค่า threshold ใด"""

    __tablename__ = "threshold_setting"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    changed_by_admin_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("admin_account.id"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    changed_by: Mapped["AdminAccount"] = relationship(back_populates="threshold_changes")
