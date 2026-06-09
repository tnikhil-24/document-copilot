import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.chats import (
    _truncate_title,
    append_message,
    create_thread,
    fetch_messages,
    get_thread,
    list_threads,
    set_thread_title,
)

pytestmark = pytest.mark.anyio


def _client_with_table(table: MagicMock) -> MagicMock:
    client = MagicMock()
    client.table.return_value = table
    return client


class TestListThreads:
    async def test_returns_threads_ordered_by_updated_at_desc(self) -> None:
        rows = [
            {"id": "t2", "title": "B", "updated_at": "2026-06-09"},
            {"id": "t1", "title": "A", "updated_at": "2026-06-08"},
        ]
        table = MagicMock()
        table.select.return_value.order.return_value.execute = AsyncMock(return_value=MagicMock(data=rows))
        client = _client_with_table(table)

        result = await list_threads(client)

        assert result == rows
        table.select.assert_called_once_with("id, title, updated_at")
        table.select.return_value.order.assert_called_once_with("updated_at", desc=True)


class TestCreateThread:
    async def test_inserts_and_returns_the_new_thread(self) -> None:
        user_id = str(uuid.uuid4())
        thread_row = {"id": "t1", "user_id": user_id, "title": None}
        table = MagicMock()
        table.insert.return_value.execute = AsyncMock(return_value=MagicMock(data=[thread_row]))
        client = _client_with_table(table)

        result = await create_thread(client, user_id=user_id)

        assert result == thread_row
        table.insert.assert_called_once_with({"user_id": user_id})


class TestSetThreadTitle:
    async def test_updates_title_from_text(self) -> None:
        thread_id = uuid.uuid4()
        table = MagicMock()
        table.update.return_value.eq.return_value.execute = AsyncMock()
        client = _client_with_table(table)

        await set_thread_title(client, thread_id=thread_id, text="What did Netflix say about content costs?")

        table.update.assert_called_once_with({"title": "What did Netflix say about content costs?"})
        table.update.return_value.eq.assert_called_once_with("id", str(thread_id))

    async def test_truncates_long_text_at_word_boundary(self) -> None:
        thread_id = uuid.uuid4()
        table = MagicMock()
        table.update.return_value.eq.return_value.execute = AsyncMock()
        client = _client_with_table(table)

        await set_thread_title(client, thread_id=thread_id, text="word " * 20)

        title = table.update.call_args[0][0]["title"]
        assert len(title) <= 60


class TestTruncateTitle:
    def test_returns_short_text_unchanged(self) -> None:
        assert _truncate_title("short") == "short"

    def test_strips_whitespace(self) -> None:
        assert _truncate_title("  hello  ") == "hello"

    def test_truncates_at_word_boundary(self) -> None:
        result = _truncate_title("word " * 15)
        assert len(result) <= 60
        assert not result.endswith(" ")

    def test_hard_truncates_when_no_space_found(self) -> None:
        assert _truncate_title("x" * 80) == "x" * 60

    def test_exact_boundary_not_truncated(self) -> None:
        text = "a" * 60
        assert _truncate_title(text) == text


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
        table.update.return_value.eq.return_value.execute = AsyncMock()
        client = _client_with_table(table)

        result = await append_message(client, thread_id=thread_id, role="user", text="hello")

        assert result == message_row
        table.insert.assert_called_once_with(
            {"thread_id": str(thread_id), "role": "user", "content": {"text": "hello"}}
        )

    async def test_touches_thread_updated_at(self) -> None:
        thread_id = uuid.uuid4()
        table = MagicMock()
        table.insert.return_value.execute = AsyncMock(return_value=MagicMock(data=[{"id": "msg-1"}]))
        table.update.return_value.eq.return_value.execute = AsyncMock()
        client = _client_with_table(table)

        await append_message(client, thread_id=thread_id, role="user", text="hello")

        update_payload = table.update.call_args[0][0]
        assert "updated_at" in update_payload
        table.update.return_value.eq.assert_called_once_with("id", str(thread_id))


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
