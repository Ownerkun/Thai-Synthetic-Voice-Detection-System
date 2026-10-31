from typing import Annotated
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.security import hash_password, verify_password

from app.deps import DbSession, get_current_user
from app.models.user import UserAccount
from app.schemas.auth import UserOut
from app.schemas.user import UserUpdateRequest, ChangePasswordRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])

CurrentUser = Annotated[UserAccount, Depends(get_current_user)]



@router.get("/me", response_model=UserOut)
def get_me(user: CurrentUser) -> UserAccount:
    return user

@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdateRequest, db: DbSession, user: CurrentUser) -> UserAccount:
    if "display_name" in payload.model_fields_set:
        user.display_name = payload.display_name
    db.commit()
    db.refresh(user)
    return user

@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: ChangePasswordRequest, db: DbSession, user: CurrentUser) -> Response:
    # ต้องรู้รหัสเดิมด้วย กันคนที่ได้ token ไปชั่วคราว (เช่น เปิดเครื่องทิ้งไว้) เปลี่ยนรหัสยึดบัญชีได้
    # ใช้ 400 ไม่ใช่ 401 เพราะ frontend มักตีความ 401 ว่า "token หมดอายุ" แล้วเด้งไปหน้า login
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    user.password_hash = hash_password(payload.new_password)
    db.commit()

    logger.info("User %s changed their password", user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)