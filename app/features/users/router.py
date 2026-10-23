from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models.user import UserAccount
from app.schemas.auth import UserOut

router = APIRouter(prefix="/users", tags=["users"])

CurrentUser = Annotated[UserAccount, Depends(get_current_user)]


@router.get("/me", response_model=UserOut)
def get_me(user: CurrentUser) -> UserAccount:
    return user
