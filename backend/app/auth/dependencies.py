import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from supabase import AsyncClient, AuthApiError

from app.database.supabase import create_user_client


@dataclass(frozen=True)
class CurrentUser:
    """Identity of the authenticated user, derived from a verified Supabase access token."""

    id: uuid.UUID
    email: str
    access_token: str


def _extract_bearer_token(authorization: str | None = Header(default=None)) -> str:
    """Pull the bearer token out of the Authorization header, or reject the request."""
    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=401, detail="Authorization header must be a bearer token"
        )

    return token


async def get_user_client(token: str = Depends(_extract_bearer_token)) -> AsyncClient:
    """Request-scoped Supabase client that enforces RLS as the authenticated user."""
    return await create_user_client(token)


async def get_current_user(
    token: str = Depends(_extract_bearer_token),
    client: AsyncClient = Depends(get_user_client),
) -> CurrentUser:
    """Verify the bearer token with Supabase Auth and return the authenticated user's identity."""
    try:
        response = await client.auth.get_user(token)
    except AuthApiError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    if response is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = response.user
    if user.email is None:
        raise HTTPException(status_code=401, detail="Authenticated user has no email")

    return CurrentUser(id=uuid.UUID(user.id), email=user.email, access_token=token)
