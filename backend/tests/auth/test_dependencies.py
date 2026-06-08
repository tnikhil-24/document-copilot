import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from supabase import AuthApiError

from app.auth import dependencies
from app.auth.dependencies import CurrentUser, _extract_bearer_token, get_current_user

pytestmark = pytest.mark.anyio


def _client_returning(user: MagicMock | None = None, error: Exception | None = None) -> MagicMock:
    client = MagicMock()
    if error is not None:
        client.auth.get_user = AsyncMock(side_effect=error)
    else:
        client.auth.get_user = AsyncMock(return_value=MagicMock(user=user))
    return client


class TestExtractBearerToken:
    def test_extracts_token_from_bearer_header(self) -> None:
        assert _extract_bearer_token("Bearer abc123") == "abc123"

    def test_rejects_missing_header(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _extract_bearer_token(None)
        assert exc_info.value.status_code == 401

    def test_rejects_non_bearer_scheme(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _extract_bearer_token("Basic abc123")
        assert exc_info.value.status_code == 401

    def test_rejects_bearer_scheme_with_no_token(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _extract_bearer_token("Bearer ")
        assert exc_info.value.status_code == 401


class TestGetCurrentUser:
    async def test_valid_token_returns_current_user_and_bootstraps_profile(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        user_id = uuid.uuid4()
        user = MagicMock(id=str(user_id), email="analyst@driftwood.com")
        client = _client_returning(user=user)
        get_or_create = AsyncMock(return_value={"full_name": "Analyst One"})
        monkeypatch.setattr(dependencies, "get_or_create_profile", get_or_create)

        current_user = await get_current_user(token="valid-token", client=client)

        assert current_user == CurrentUser(
            id=user_id,
            email="analyst@driftwood.com",
            access_token="valid-token",
            full_name="Analyst One",
        )
        get_or_create.assert_awaited_once_with(
            client, user_id=str(user_id), email="analyst@driftwood.com"
        )

    async def test_expired_or_invalid_token_returns_401(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _client_returning(
            error=AuthApiError("invalid JWT", status=401, code=None)
        )
        monkeypatch.setattr(dependencies, "get_or_create_profile", AsyncMock())

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="expired-token", client=client)

        assert exc_info.value.status_code == 401

    async def test_user_without_email_returns_401(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        user = MagicMock(id=str(uuid.uuid4()), email=None)
        client = _client_returning(user=user)
        monkeypatch.setattr(dependencies, "get_or_create_profile", AsyncMock())

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="phone-only-token", client=client)

        assert exc_info.value.status_code == 401
