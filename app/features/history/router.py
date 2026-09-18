from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import DbSession, get_current_user
from app.models.detection import DetectionRecord, Feedback
from app.models.user import UserAccount
from app.schemas.detection import DetectionDetailOut, DetectionRecordOut, SegmentResultOut
from app.schemas.feedback import FeedbackOut, FeedbackRequest

router = APIRouter(prefix="/history", tags=["history"])

CurrentUser = Annotated[UserAccount, Depends(get_current_user)]


@router.get("", response_model=list[DetectionRecordOut])
def list_history(db: DbSession, user: CurrentUser, limit: int = Query(default=50, le=200)) -> list[DetectionRecord]:
    return (
        db.query(DetectionRecord)
        .filter(DetectionRecord.user_id == user.id)
        .order_by(DetectionRecord.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{detection_id}", response_model=DetectionDetailOut)
def get_detail(detection_id: UUID, db: DbSession, user: CurrentUser) -> DetectionDetailOut:
    record = _get_owned_record_or_404(db, detection_id, user.id)
    return DetectionDetailOut(
        **DetectionRecordOut.model_validate(record).model_dump(),
        threshold_used=record.threshold_used,
        model_version=record.model_version,
        processing_ms=record.processing_ms,
        segments=[
            SegmentResultOut(
                index=s.segment_index,
                start_seconds=s.start_seconds,
                end_seconds=s.end_seconds,
                spoof_probability=s.spoof_probability,
                is_spoof=s.spoof_probability >= record.threshold_used,
            )
            for s in record.segments
        ],
    )


@router.delete("/{detection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_item(detection_id: UUID, db: DbSession, user: CurrentUser) -> None:
    record = _get_owned_record_or_404(db, detection_id, user.id)
    db.delete(record)
    db.commit()


@router.post("/{detection_id}/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def submit_feedback(detection_id: UUID, payload: FeedbackRequest, db: DbSession, user: CurrentUser) -> Feedback:
    """UC6: Submit accuracy feedback — login required; guest users cannot give feedback.
    Feedback.user_id is NOT NULL so it must be tied to an authenticated account."""
    record = _get_owned_record_or_404(db, detection_id, user.id)
    if record.feedback is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Feedback already submitted for this record")

    feedback = Feedback(detection_id=record.id, user_id=user.id, user_agrees=payload.user_agrees)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def _get_owned_record_or_404(db: DbSession, detection_id: UUID, user_id: UUID) -> DetectionRecord:
    record = (
        db.query(DetectionRecord)
        .filter(DetectionRecord.id == detection_id, DetectionRecord.user_id == user_id)
        .first()
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return record
