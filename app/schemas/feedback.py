from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    user_agrees: bool


class FeedbackOut(BaseModel):
    id: UUID
    detection_id: UUID
    user_agrees: bool
    created_at: datetime
    updated_at: datetime | None

class FeedbackHistoryItemOut(BaseModel):
    id: UUID
    detection_id: UUID
    original_filename: str
    verdict: str
    user_agrees: bool
    created_at: datetime
    updated_at: datetime | None

