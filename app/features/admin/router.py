from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import DbSession, get_current_admin
from app.models.admin import AdminAccount, ThresholdSetting
from app.models.detection import DetectionRecord, Feedback
from app.models.user import UserAccount
from app.schemas.admin import (
    StatsOverviewOut,
    ThresholdOut,
    ThresholdUpdateRequest,
    ThresholdUpdateResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])

CurrentAdmin = Annotated[AdminAccount, Depends(get_current_admin)]


@router.get("/threshold", response_model=ThresholdOut | None)
def current_threshold(db: DbSession, _admin: CurrentAdmin) -> ThresholdSetting | None:
    return (
        db.query(ThresholdSetting)
        .order_by(ThresholdSetting.effective_from.desc())
        .first()
    )


@router.post("/threshold", response_model=ThresholdUpdateResponse)
def update_threshold(
    payload: ThresholdUpdateRequest, db: DbSession, admin: CurrentAdmin
) -> ThresholdUpdateResponse:
    previous = (
        db.query(ThresholdSetting)
        .order_by(ThresholdSetting.effective_from.desc())
        .first()
    )

    new_setting = ThresholdSetting(
        value=payload.value, changed_by_admin_id=admin.id, note=payload.note
    )
    db.add(new_setting)
    db.commit()
    db.refresh(new_setting)

    # /predict อ่านค่า threshold ล่าสุดจาก DB ทุกครั้ง (ดู app/services/threshold_service.py)
    # จึงมีผลกับคำขอถัดไปทันที ไม่ต้อง restart หรือ deploy container ใหม่
    return ThresholdUpdateResponse(
        previous_value=previous.value if previous else None,
        current=ThresholdOut.model_validate(new_setting),
    )


@router.get("/stats", response_model=StatsOverviewOut)
def stats_overview(db: DbSession, _admin: CurrentAdmin) -> StatsOverviewOut:
    total = db.query(DetectionRecord).count()
    total_spoof = (
        db.query(DetectionRecord).filter(DetectionRecord.verdict == "spoof").count()
    )
    total_users = db.query(UserAccount).count()

    total_feedback = db.query(Feedback).count()
    agrees = db.query(Feedback).filter(Feedback.user_agrees.is_(True)).count()
    agreement_rate = (agrees / total_feedback) if total_feedback > 0 else None

    return StatsOverviewOut(
        total_detections=total,
        total_spoof_verdicts=total_spoof,
        total_real_verdicts=total - total_spoof,
        total_users=total_users,
        feedback_agreement_rate=agreement_rate,
    )
