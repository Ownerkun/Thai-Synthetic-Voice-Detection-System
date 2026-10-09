from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import joinedload

from app.deps import DbSession, get_current_user
from app.models.detection import Feedback
from app.models.user import UserAccount
from app.schemas.feedback import FeedbackHistoryItemOut

router = APIRouter(prefix="/feedback", tags=["feedback"])

CurrentUser = Annotated[UserAccount, Depends(get_current_user)]


@router.get("", response_model=list[FeedbackHistoryItemOut])
def list_my_feedback(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[FeedbackHistoryItemOut]:
    rows = (
        db.query(Feedback)
        .options(joinedload(Feedback.detection))  # load the detection in the same query (avoid one query per row)
        .filter(Feedback.user_id == user.id)
        .order_by(Feedback.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        FeedbackHistoryItemOut(
            id=fb.id,
            detection_id=fb.detection_id,
            original_filename=fb.detection.original_filename,
            verdict=fb.detection.verdict,
            user_agrees=fb.user_agrees,
            created_at=fb.created_at,
            updated_at=fb.updated_at,
        )
        for fb in rows
    ]