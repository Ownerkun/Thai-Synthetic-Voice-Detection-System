from uuid import UUID

from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    user_agrees: bool


class FeedbackOut(BaseModel):
    id: UUID
    detection_id: UUID
    user_agrees: bool
