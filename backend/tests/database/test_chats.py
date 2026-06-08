import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.chats import append_message, fetch_messages, get_or_create_thread, get_thread

pytestmark = pytest.mark.anyio


def _client_with_table(table: MagicMock) -> MagicMock:
    client = MagicMock()
    client.table.return_value = table
    return client


class TestGetOrCreateThread:
    async def test_returns_existing_thread_without_creating_one(self) -> None:
        thread_row = {"id": "thread-1", "user_id": "user-1"}
        table = MagicMock()
        lookup = table.select.return_value.eq.return_value.order.return_value.limit.return_value.maybe_single
        lookup.return_value.execute = AsyncMock(return_value=MagicMock(data=thread_row))
        client = _client_with_table(table)

        result = await get_or_create_thread(client, user_id="user-1")

        assert result == thread_row
        table.select.return_value.eq.assert_called_once_with("user_id", "user-1")
        table.insert.assert_not_called()

    async def test_creates_a_thread_on_first_visit(self) -> None:
        thread_row = {"id": "thread-1", "user_id": "user-1"}
        table = MagicMock()
        lookup = table.select.return_value.eq.return_value.order.return_value.limit.return_value.maybe_single
        lookup.return_value.execute = AsyncMock(return_value=None)
        table.insert.return_value.execute = AsyncMock(return_value=MagicMock(data=[thread_row]))
        client = _client_with_table(table)

        result = await get_or_create_thread(client, user_id="user-1")

        assert result == thread_row
        table.insert.assert_called_once_with({"user_id": "user-1"})


class TestGetThread:
    async def test_returns_the_thread_when_found_and_owned(self) -> None:
        thread_id = uuid.uuid4()
        thread_row = {"id": str(thread_id), "user_id": "user-1"}
        table = MagicMock()
        lookup = table.select.return_value.eq.return_value.maybe_single
        lookup.return_value.execute = AsyncMock(return_value=MagicMock(data=thread_row))
        client = _client_with_table(table)

        result = await get_thread(client, thread_id=thread_id)

        assert result == thread_row
        table.select.return_value.eq.assert_called_once_with("id", str(thread_id))

    async def test_returns_none_when_missing_or_not_owned(self) -> None:
        """RLS filters out threads the caller doesn't own before they reach us,
        so a thread that doesn't exist and one the caller can't see look identical
        here — both become `None`, and both become a 404 at the route layer."""
        thread_id = uuid.uuid4()
        table = MagicMock()
        lookup = table.select.return_value.eq.return_value.maybe_single
        lookup.return_value.execute = AsyncMock(return_value=None)
        client = _client_with_table(table)

        result = await get_thread(client, thread_id=thread_id)

        assert result is None


class TestAppendMessage:
    async def test_inserts_the_message_and_returns_the_persisted_row(self) -> None:
        thread_id = uuid.uuid4()
        message_row = {"id": "msg-1", "role": "user", "content": {"text": "hello"}}
        table = MagicMock()
        table.insert.return_value.execute = AsyncMock(return_value=MagicMock(data=[message_row]))
        client = _client_with_table(table)

        result = await append_message(client, thread_id=thread_id, role="user", text="hello")

        assert result == message_row
        table.insert.assert_called_once_with(
            {"thread_id": str(thread_id), "role": "user", "content": {"text": "hello"}}
        )


class TestFetchMessages:
    async def test_returns_messages_in_conversation_order(self) -> None:
        thread_id = uuid.uuid4()
        rows = [{"id": "msg-1"}, {"id": "msg-2"}]
        table = MagicMock()
        ordered = table.select.return_value.eq.return_value.order
        ordered.return_value.execute = AsyncMock(return_value=MagicMock(data=rows))
        client = _client_with_table(table)

        result = await fetch_messages(client, thread_id=thread_id)

        assert result == rows
        table.select.return_value.eq.assert_called_once_with("thread_id", str(thread_id))
        ordered.assert_called_once_with("created_at")
