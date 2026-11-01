import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, func
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
    updated_at: Mapped[datetime | None] = mapped_column((DateTime(timezone=True)), nullable=True, onupdate=func.now())
    user_agrees: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # --- แบบสอบถามรายละเอียด (ทุกช่องไม่บังคับ NULL = ผู้ใช้ไม่ได้ตอบข้อนั้น) ---
    # เก็บเป็น string ธรรมดา ไม่ใช่ DB enum จะได้เพิ่มตัวเลือกใหม่ได้โดยไม่ต้อง migration (ค่าที่ยอมรับตรวจที่ schema)
    audio_source: Mapped[str | None] = mapped_column(String(30), nullable=True)  # เสียงนี้ได้มาอย่างไร (เช่น เปิดจากอีกเครื่องผ่านลำโพง)
    input_method: Mapped[str | None] = mapped_column(String(30), nullable=True)  # อัดในเว็บ / อัปโหลดไฟล์
    environment: Mapped[str | None] = mapped_column(String(30), nullable=True)  # สถานที่อัด
    mic_distance: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # none_as_null: ไม่ตอบ = SQL NULL จริง (ไม่งั้น SQLAlchemy เก็บเป็น JSON 'null' แล้ว IS NULL ใช้ไม่ได้) / [] = ตอบว่าไม่มีปัญหา
    audio_issues: Mapped[list[str] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    recording_device: Mapped[str | None] = mapped_column(String(100), nullable=True)  # รุ่นอุปกรณ์ที่ใช้อัด (พิมพ์เอง)
    playback_device: Mapped[str | None] = mapped_column(String(100), nullable=True)  # รุ่นอุปกรณ์ที่เปิดเสียง (เฉพาะกรณี audio_source = speaker_replay)
    truth_basis: Mapped[str | None] = mapped_column(String(30), nullable=True)  # ผู้ใช้รู้ได้อย่างไรว่าเสียงนี้จริง/สังเคราะห์ (ความน่าเชื่อถือของ label)
    speaker_accent: Mapped[str | None] = mapped_column(String(30), nullable=True)
    speaker_age_group: Mapped[str | None] = mapped_column(String(30), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(300), nullable=True)

    detection: Mapped["DetectionRecord"] = relationship(back_populates="feedback")
    user: Mapped["UserAccount"] = relationship(back_populates="feedbacks")  # type: ignore[name-defined]
