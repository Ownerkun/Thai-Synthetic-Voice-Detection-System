from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.deps import DbSession, get_current_admin
from app.models.admin import AdminAccount
from app.models.detection import DetectionRecord, Feedback
from app.models.user import UserAccount
from app.schemas.admin_detection import (
    AdminDetectionFilters,
    AdminDetectionItemOut,
    AdminDetectionListOut,
)

router = APIRouter(prefix="/detections")

THAI_TZ = timezone(timedelta(hours=7))

CurrentAdmin = Annotated[AdminAccount, Depends(get_current_admin)]


@router.get("", response_model=AdminDetectionListOut)
def list_detections(
    params: Annotated[AdminDetectionFilters, Query()],
    db: DbSession,
    _admin: CurrentAdmin,
) -> AdminDetectionListOut:
    # outer join: guest ไม่มี user และผลที่ยังไม่มี feedback ก็แสดงด้วย
    query = (
        db.query(DetectionRecord, UserAccount.email, Feedback.user_agrees)
        .outerjoin(UserAccount, UserAccount.id == DetectionRecord.user_id)
        .outerjoin(Feedback, Feedback.detection_id == DetectionRecord.id)
    )

    query = _apply_filters(query, params)

    total = query.count()
    rows = (
        query.order_by(DetectionRecord.created_at.desc(), DetectionRecord.id)  # id ไว้ตัดสินเมื่อเวลาเท่ากัน ไม่ให้แบ่งหน้าสลับกัน
        .offset(params.offset)
        .limit(params.limit)
        .all()
    )

    return AdminDetectionListOut(
        items=[_to_item(record, email, user_agrees) for record, email, user_agrees in rows],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )

def _apply_filters(query, params: AdminDetectionFilters):
    if params.verdict is not None:
        query = query.filter(DetectionRecord.verdict == params.verdict)

    if params.date_from is not None:
        query = query.filter(DetectionRecord.created_at >= _start_of_thai_day(params.date_from))
    if params.date_to is not None:
        # นับรวมทั้งวัน date_to: เอาก่อน "เที่ยงคืนของวันถัดไป"
        query = query.filter(DetectionRecord.created_at < _start_of_thai_day(params.date_to + timedelta(days=1)))

    if params.q:
        # autoescape = ถ้าพิมพ์ % หรือ _ จะค้นหาตัวอักษรนั้นจริงๆ ไม่ใช่ wildcard
        query = query.filter(DetectionRecord.original_filename.icontains(params.q, autoescape=True))

    return query

def _start_of_thai_day(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=THAI_TZ).astimezone(timezone.utc)

def _to_item(record: DetectionRecord, user_email: str | None, user_agrees: bool | None) -> AdminDetectionItemOut:
    if user_agrees is None:
        feedback = None
    else:
        feedback = "agree" if user_agrees else "disagree"

    return AdminDetectionItemOut(
        id=record.id,
        created_at=record.created_at,
        original_filename=record.original_filename,
        duration_seconds=record.duration_seconds,
        num_segments=record.num_segments,
        mean_probability=record.mean_probability,
        max_probability=record.max_probability,
        threshold_used=record.threshold_used,
        verdict=record.verdict,
        possible_partial_spoof=record.possible_partial_spoof,
        model_version=record.model_version,
        processing_ms=record.processing_ms,
        user_id=record.user_id,
        user_email=user_email,
        feedback=feedback,
    )
