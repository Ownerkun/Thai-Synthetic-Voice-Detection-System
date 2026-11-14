from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.core.security import create_access_token, hash_password, verify_password
from app.deps import DbSession
from app.models.admin import AdminAccount
from app.models.email_token import VERIFY_EMAIL
from app.models.user import UserAccount
from app.schemas.auth import (
    AdminLoginRequest,
    EmailRequest,
    LoginRequest,
    MessageOut,
    RegisterRequest,
    RegisterResponse,
    TokenRequest,
    TokenResponse,
    UserOut,
)

from app.services.email_token_service import consume_token, delete_tokens, issue_token
from app.services.mail_service import send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession, background_tasks: BackgroundTasks) -> RegisterResponse:
    existing = db.query(UserAccount).filter(UserAccount.email == payload.email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already in use"
        )

    user = UserAccount(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    raw_token = issue_token(db, user, VERIFY_EMAIL)
    if raw_token is not None:
        background_tasks.add_task(send_verification_email, user.email, user.display_name, raw_token)
    return RegisterResponse(email=user.email)

@router.post("/verify-email", response_model=TokenResponse)
def verify_email(payload: TokenRequest, db: DbSession) -> TokenResponse:
    user = consume_token(db, payload.token, VERIFY_EMAIL)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
    delete_tokens(db, user.id, VERIFY_EMAIL)

    if not user.is_active:
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    db.commit()
    return TokenResponse(access_token=create_access_token(subject_id=user.id, role="user"))


@router.post("/resend-verification", response_model=MessageOut, status_code=status.HTTP_202_ACCEPTED)
def resend_verification(payload: EmailRequest, db: DbSession, background_tasks: BackgroundTasks) -> MessageOut:
    user = db.query(UserAccount).filter(UserAccount.email == payload.email).first()
    if user is not None and user.is_active and not user.email_verified:
        raw_token = issue_token(db, user, VERIFY_EMAIL)  # None = เพิ่งส่งไป ยังอยู่ในช่วงรอ
        if raw_token is not None:
            background_tasks.add_task(send_verification_email, user.email, user.display_name, raw_token)
    # ตอบเหมือนกันทุกกรณี ไม่บอกว่าอีเมลนี้มีในระบบหรือไม่
    return MessageOut(detail="If this email is waiting for verification, a new link has been sent")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.query(UserAccount).filter(UserAccount.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    # เช็คหลังตรวจรหัสผ่านเท่านั้น คนที่ไม่รู้รหัสผ่านจะไม่รู้ว่าบัญชีนี้มีอยู่หรือถูกระงับ
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(subject_id=user.id, role="user")
    return TokenResponse(access_token=token)


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(payload: AdminLoginRequest, db: DbSession) -> TokenResponse:
    admin = (
        db.query(AdminAccount).filter(AdminAccount.username == payload.username).first()
    )
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(subject_id=admin.id, role="admin")
    return TokenResponse(access_token=token)
