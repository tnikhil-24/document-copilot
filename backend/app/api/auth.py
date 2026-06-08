from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import CurrentUser, get_current_user

router = APIRouter(tags=["auth"])


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str | None


@router.get("/me")
async def get_me(current_user: CurrentUser = Depends(get_current_user)) -> MeResponse:
    """Return the authenticated user's profile. Verifying the token here is what
    triggers profile bootstrap on first login (see `get_current_user`)."""
    return MeResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
    )
