from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models.user import UserAccount
from app.schemas.auth import UserOut
from app.schemas.user import UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])

CurrentUser = Annotated[UserAccount, Depends(get_current_user)]


@router.get("/me", response_model=UserOut)
def get_me(user: CurrentUser) -> UserAccount:
    return user

@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdateRequest, db: DbSession, user: CurrentUser) -> UserAccount:
    if "display_name" in payload.model.display_name
        user.display_name = payload.display_name
    db.commit()
    db.refresh(user)
    return user