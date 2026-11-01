from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# ตัวเลือกของแบบสอบถาม "เสียงนี้ถูกอัดมาอย่างไร" ทุกข้อไม่บังคับตอบ
# ค่าด้านล่างคือรหัสที่เก็บลง DB และส่งผ่าน API
# ถ้าเพิ่มตัวเลือก ต้องเพิ่มทั้งที่นี่และใน feedback_options.py (มีเทสเช็คว่าตรงกัน)
# ---------------------------------------------------------------------------
AudioSource = Literal[
    "direct_voice",  # พูดใส่ไมค์โดยตรง
    "speaker_replay",  # เปิดเสียงจากอีกเครื่องผ่านลำโพง แล้วอัดต่ออีกที
    "phone_call",  # อัดจากสายโทรศัพท์
    "chat_voice_message",  # ข้อความเสียงจากแอปแชต
    "shared_media",  # คลิป/ไฟล์ที่ได้รับส่งต่อหรือดาวน์โหลดมา
    "other",
]
InputMethod = Literal["recorded_in_app", "uploaded_file"]  # ฝั่ง frontend รู้เองอยู่แล้ว ส่งให้อัตโนมัติได้ไม่ต้องถามผู้ใช้
Environment = Literal["quiet_room", "noisy_indoor", "outdoors", "in_vehicle", "crowded_public"]
MicDistance = Literal["close", "normal", "far"]  # ชิดปาก (< 5 ซม.) / ปกติ (6 ซม. - 20 ซม.) / ไกล (> 20 ซม.)
AudioIssue = Literal[
    "background_noise",
    "echo",
    "uneven_volume",  # เสียงดังเบาไม่สม่ำเสมอ
    "too_quiet",
    "distorted",  # เสียงแตก
    "choppy",  # เสียงขาดๆ หายๆ
    "music_or_tv",
    "multiple_speakers",
]
TruthBasis = Literal["self_recorded", "self_generated", "know_the_speaker", "not_sure"]
SpeakerAccent = Literal["central", "northern", "northeastern", "southern", "other"]
SpeakerAgeGroup = Literal["under_20", "20_39", "40_59", "60_plus"]


class FeedbackDetailsOut(BaseModel):
    """ฟิลด์แบบสอบถามทั้งหมด (ใช้เป็น response) None = ไม่ได้ตอบข้อนั้น"""

    audio_source: AudioSource | None = None
    input_method: InputMethod | None = None
    environment: Environment | None = None
    mic_distance: MicDistance | None = None
    audio_issues: list[AudioIssue] | None = None  # [] = ตอบว่า "ไม่มีปัญหา", None = ไม่ได้ตอบ
    recording_device: str | None = None
    playback_device: str | None = None
    truth_basis: TruthBasis | None = None
    speaker_accent: SpeakerAccent | None = None
    speaker_age_group: SpeakerAgeGroup | None = None
    comment: str | None = None


DETAIL_FIELDS = tuple(FeedbackDetailsOut.model_fields)  # ชื่อฟิลด์แบบสอบถามทั้งหมด (ไม่รวม user_agrees)


def extract_details(source) -> dict:
    """ดึงฟิลด์แบบสอบถามจาก object ใดก็ได้ (Feedback จาก DB หรือ FeedbackRequest) เป็น dict"""
    return {name: getattr(source, name) for name in DETAIL_FIELDS}


class FeedbackRequest(FeedbackDetailsOut):
    """POST / PUT feedback: user_agrees บังคับเหมือนเดิม ที่เหลือไม่บังคับ"""

    model_config = ConfigDict(extra="forbid")

    user_agrees: bool
    # ฟิลด์ข้อความ: จำกัดความยาวเพิ่มจากชนิดของ response
    recording_device: str | None = Field(default=None, max_length=100)
    playback_device: str | None = Field(default=None, max_length=100)
    comment: str | None = Field(default=None, max_length=300)

    @field_validator("recording_device", "playback_device", "comment")
    @classmethod
    def blank_text_means_not_answered(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None  # ช่องที่เว้นว่างหรือมีแต่ช่องว่าง = ไม่ได้ตอบ

    @field_validator("audio_issues")
    @classmethod
    def issues_must_be_unique(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("audio_issues must not contain duplicates")
        return value

    @model_validator(mode="after")
    def check_playback_device(self) -> "FeedbackRequest":
        if self.playback_device is not None and self.audio_source != "speaker_replay":
            raise ValueError("playback_device can only be sent when audio_source is speaker_replay")
        return self


class FeedbackOut(FeedbackDetailsOut):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    detection_id: UUID
    user_agrees: bool
    created_at: datetime
    updated_at: datetime | None


class FeedbackHistoryItemOut(FeedbackDetailsOut):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    detection_id: UUID
    original_filename: str
    verdict: str
    user_agrees: bool
    created_at: datetime
    updated_at: datetime | None
