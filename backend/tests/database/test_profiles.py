from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.profiles import get_or_create_profile

pytestmark = pytest.mark.anyio


def _client_returning(profile_row: dict) -> MagicMock:
    """Fake Supabase client whose `profiles` table always reports `profile_row`
    as the current state — mirrors what `upsert` + `select` would see whether
    the row was just inserted or already existed."""
    table = MagicMock()
    table.upsert.return_value.execute = AsyncMock(return_value=MagicMock())
    table.select.return_value.eq.return_value.single.return_value.execute = AsyncMock(
        return_value=MagicMock(data=profile_row)
    )
    client = MagicMock()
    client.table.return_value = table
    return client


async def test_creates_profile_on_first_login() -> None:
    profile_row = {"id": "user-id", "email": "analyst@driftwood.com", "full_name": None}
    client = _client_returning(profile_row)

    result = await get_or_create_profile(client, user_id="user-id", email="analyst@driftwood.com")

    assert result == profile_row
    client.table.return_value.upsert.assert_called_once_with(
        {"id": "user-id", "email": "analyst@driftwood.com"},
        on_conflict="id",
        ignore_duplicates=True,
    )


async def test_repeat_logins_do_not_create_duplicates() -> None:
    profile_row = {"id": "user-id", "email": "analyst@driftwood.com", "full_name": None}
    client = _client_returning(profile_row)
    table = client.table.return_value

    first = await get_or_create_profile(client, user_id="user-id", email="analyst@driftwood.com")
    second = await get_or_create_profile(client, user_id="user-id", email="analyst@driftwood.com")

    assert first == second == profile_row
    # `ignore_duplicates` + `on_conflict="id"` is what makes the upsert safe to repeat:
    # Postgres no-ops on the unique-key conflict instead of raising, so two logins
    # for the same user can never produce two rows.
    for _, kwargs in table.upsert.call_args_list:
        assert kwargs == {"on_conflict": "id", "ignore_duplicates": True}
