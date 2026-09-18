"""
Entrypoint uvicorn app.main:app --reload หรือผ่าน Docker ตาม docker-compose.yml
"""
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.features.admin.router import router as admin_router
from app.features.auth.router import router as auth_router
from app.features.detection.router import router as detection_router
from app.features.history.router import router as history_router
from app.models.admin import AdminAccount
from app.services.onnx_analyzer import get_analyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Dev-friendly bootstrap: สร้างตารางถ้ายังไม่มี (โปรเจกต์จริงควรใช้ Alembic migration แทน — ดู alembic/)
    Base.metadata.create_all(bind=engine)

    # โหลด analyzer ล่วงหน้าตอน startup
    analyzer = get_analyzer()
    logger.info("Analyzer ready: %s", analyzer.model_version)

    _bootstrap_admin_if_missing()

    yield  # แอปรันต่อจากจุดนี้ โค้ดหลัง yield จะรันตอน shutdown


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(detection_router)
app.include_router(history_router)
app.include_router(admin_router)


def _bootstrap_admin_if_missing() -> None:
    """สร้างบัญชีแอดมินคนแรกจาก env ถ้ายังไม่มีแอดมินในระบบ สำหรับตอน dev ควรปิด BOOTSTRAP_ADMIN_PASSWORD หลังสร้างบัญชีจริงแล้ว"""
    if not settings.bootstrap_admin_username or not settings.bootstrap_admin_password:
        return

    db = SessionLocal()
    try:
        existing = db.query(AdminAccount).filter(AdminAccount.username == settings.bootstrap_admin_username).first()
        if existing is not None:
            return
        admin = AdminAccount(
            username=settings.bootstrap_admin_username,
            password_hash=hash_password(settings.bootstrap_admin_password),
        )
        db.add(admin)
        db.commit()
        logger.warning(
            "Bootstrap admin account '%s' created from BOOTSTRAP_ADMIN_PASSWORD — "
            "remove or rotate this value in .env after production deployment",
            settings.bootstrap_admin_username,
        )
    finally:
        db.close()


@app.get("/")
def root() -> dict:
    return {"service": settings.app_name, "status": "running"}
