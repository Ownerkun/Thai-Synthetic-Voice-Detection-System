import logging
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import func, or_

from app.deps import DbSession, get_current_admin
from app.models.admin import AdminAccount, ThresholdSetting
from app.models.detection import DetectionRecord, Feedback
from app.models.user import UserAccount
from app.schemas.admin import (
    StatsOverviewOut,
    ThresholdOut,
    ThresholdUpdateRequest,
    ThresholdUpdateResponse,
    AdminUserListOut,
    AdminUserOut,
    AdminUserUpdateRequest,
)

logger = logging.getLogger(__name__)
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

def _to_admin_user_out(user: UserAccount, detection_count: int) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        is_active=user.is_active,
        detection_count=detection_count,
    )

@router.get("/users", response_model=AdminUserListOut)
def list_users(
    db: DbSession,
    _admin: CurrentAdmin,
    q: str | None = Query(default=None, max_length=100, description="ค้นหาจาก email หรือ display_name"),
    is_active: bool | None = Query(default=None, description="true = ใช้งานปกติ, false = ถูกระงับ"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminUserListOut:
    query = db.query(UserAccount)

    if q:
        # autoescape = ถ้าพิมพ์ % หรือ _ จะค้นหาตัวอักษรนั้นจริงๆ ไม่ใช่ wildcard
        query = query.filter(
            or_(
                UserAccount.email.icontains(q, autoescape=True),
                UserAccount.display_name.icontains(q, autoescape=True),
            )
        )
    if is_active is not None:
        query = query.filter(UserAccount.is_active.is_(is_active))

    total = query.count()
    users = (
        query.order_by(UserAccount.created_at.desc(), UserAccount.id)  # id ไว้ตัดสินเมื่อ created_at เท่ากัน ไม่ให้แบ่งหน้าสลับกัน
        .offset(offset)
        .limit(limit)
        .all()
    )

    # นับจำนวนการตรวจของผู้ใช้ทั้งหน้าด้วย query เดียว (ไม่วน query ทีละคน)
    counts: dict[UUID, int] = {}
    if users:
        rows = (
            db.query(DetectionRecord.user_id, func.count(DetectionRecord.id))
            .filter(DetectionRecord.user_id.in_([u.id for u in users]))
            .group_by(DetectionRecord.user_id)
            .all()
        )
        counts = {user_id: count for user_id, count in rows}

    return AdminUserListOut(
        items=[_to_admin_user_out(u, counts.get(u.id, 0)) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )

@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: UUID, payload: AdminUserUpdateRequest, db: DbSession, admin: CurrentAdmin
) -> AdminUserOut:
    user = db.get(UserAccount, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # แก้เฉพาะฟิลด์ที่ client ส่งมาจริงๆ (แยก "ไม่ส่ง" ออกจาก "ส่ง null")
    if "display_name" in payload.model_fields_set:
        user.display_name = payload.display_name
    if "is_active" in payload.model_fields_set:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)

    logger.info(
        "Admin %r updated user %s: %s", admin.username, user.id, sorted(payload.model_fields_set)
    )

    detection_count = db.query(DetectionRecord).filter(DetectionRecord.user_id == user.id).count()
    return _to_admin_user_out(user, detection_count)