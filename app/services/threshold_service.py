"""
อ่านค่า threshold ปัจจุบันจาก DB
"""
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.admin import ThresholdSetting


def get_current_threshold(db: Session, settings: Settings) -> float:
    latest = db.query(ThresholdSetting).order_by(ThresholdSetting.effective_from.desc()).first()
    return latest.value if latest is not None else settings.default_spoof_threshold
