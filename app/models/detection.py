import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from app.core.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DetectionRecord(Base):
    """ผลตรวจสอบเสียง 1 ไฟล์ เก็บเฉพาะ metadata และคะแนน ไม่เก็บไฟล์เสียงจริง"""

    __tablename__ = "detection_record"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    # user_id เป็นค่าว่างได้ = ผู้ใช้ไม่ได้ Login ตอนตรวจสอบ (จะไม่ปรากฏในหน้าประวัติ)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("user_account.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_format: Mapped[str] = mapped_column(String(20), nullable=False)

    num_segments: Mapped[int] = mapped_column(Integer, nullable=False)
    mean_probability: Mapped[float] = mapped_column(Float, nullable=False)
    max_probability: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_used: Mapped[float] = mapped_column(Float, nullable=False)
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)  # "real" | "spoof"
    possible_partial_spoof: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    processing_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    user: Mapped["UserAccount"] = relationship(back_populates="detection_records")  # type: ignore[name-defined]
    segments: Mapped[list["SegmentScore"]] = relationship(
        back_populates="detection", cascade="all, delete-orphan", order_by="SegmentScore.segment_index"
    )
    feedback: Mapped["Feedback"] = relationship(
        back_populates="detection", cascade="all, delete-orphan", uselist=False
    )


class SegmentScore(Base):
    __tablename__ = "segment_score"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    detection_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("detection_record.id", ondelete="CASCADE"), nullable=False, index=True
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    spoof_probability: Mapped[float] = mapped_column(Float, nullable=False)

    detection: Mapped["DetectionRecord"] = relationship(back_populates="segments")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    detection_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("detection_record.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_agrees: Mapped[bool] = mapped_column(Boolean, nullable=False)

    detection: Mapped["DetectionRecord"] = relationship(back_populates="feedback")
    user: Mapped["UserAccount"] = relationship(back_populates="feedbacks")  # type: ignore[name-defined]
