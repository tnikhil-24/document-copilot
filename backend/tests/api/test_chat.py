import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api import chat as chat_api
from app.api.chat import (
    ChatStreamRequest,
    get_thread_detail,
    get_threads,
    post_threads,
    stream_chat,
)
from app.auth.dependencies import CurrentUser
from app.chat.messages import UIMessage, UIMessagePart

pytestmark = pytest.mark.anyio


def _current_user() -> CurrentUser:
    return CurrentUser(id=uuid.uuid4(), email="analyst@driftwood.com", access_token="token", full_name="Analyst One")


def _user_message(text: str = "What did Netflix's 10-K say?") -> UIMessage:
    return UIMessage(id="m1", role="user", parts=[UIMessagePart(type="text", text=text)])


class TestGetThreads:
    async def test_returns_thread_summaries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        thread_id = uuid.uuid4()
        rows = [{"id": str(thread_id), "title": "Netflix costs", "updated_at": "2026-06-09T00:00:00+00:00"}]
        monkeypatch.setattr(chat_api, "list_threads", AsyncMock(return_value=rows))

        result = await get_threads(current_user=_current_user(), client=MagicMock())

        assert len(result) == 1
        assert result[0].id == thread_id
        assert result[0].title == "Netflix costs"

    async def test_returns_empty_list_when_user_has_no_threads(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(chat_api, "list_threads", AsyncMock(return_value=[]))

        result = await get_threads(current_user=_current_user(), client=MagicMock())

        assert result == []


class TestPostThreads:
    async def test_creates_and_returns_a_thread_summary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        user = _current_user()
        thread_id = uuid.uuid4()
        thread_row = {
            "id": str(thread_id),
            "user_id": str(user.id),
            "title": None,
            "created_at": "2026-06-09T00:00:00+00:00",
            "updated_at": "2026-06-09T00:00:00+00:00",
        }
        mock_create = AsyncMock(return_value=thread_row)
        monkeypatch.setattr(chat_api, "create_thread", mock_create)

        result = await post_threads(current_user=user, client=MagicMock())

        assert result.id == thread_id
        assert result.title is None
        assert mock_create.await_count == 1
        assert mock_create.call_args.kwargs["user_id"] == str(user.id)


class TestGetThreadDetail:
    async def test_returns_thread_with_messages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        thread_id = uuid.uuid4()
        thread = {"id": str(thread_id), "title": "Netflix costs"}
        rows = [
            {"id": "msg-1", "role": "user", "content": {"text": "hi"}},
            {"id": "msg-2", "role": "assistant", "content": {"text": "hello"}},
        ]
        monkeypatch.setattr(chat_api, "get_thread", AsyncMock(return_value=thread))
        monkeypatch.setattr(chat_api, "fetch_messages", AsyncMock(return_value=rows))

        response = await get_thread_detail(thread_id=thread_id, current_user=_current_user(), client=MagicMock())

        assert response.id == thread_id
        assert response.title == "Netflix costs"
        assert response.messages == [
            UIMessage(id="msg-1", role="user", parts=[UIMessagePart(type="text", text="hi")]),
            UIMessage(id="msg-2", role="assistant", parts=[UIMessagePart(type="text", text="hello")]),
        ]

    async def test_returns_404_for_missing_or_unauthorized_thread(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(chat_api, "get_thread", AsyncMock(return_value=None))

        with pytest.raises(HTTPException) as exc_info:
            await get_thread_detail(thread_id=uuid.uuid4(), current_user=_current_user(), client=MagicMock())

        assert exc_info.value.status_code == 404


class TestStreamChat:
    async def test_returns_404_for_a_thread_that_does_not_exist_or_isnt_owned(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(chat_api, "get_thread", AsyncMock(return_value=None))
        body = ChatStreamRequest(threadId=uuid.uuid4(), messages=[_user_message()])

        with pytest.raises(HTTPException) as exc_info:
            await stream_chat(body, current_user=_current_user(), client=MagicMock())

        assert exc_info.value.status_code == 404

    async def test_returns_400_when_the_latest_message_isnt_from_the_user(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        thread_id = uuid.uuid4()
        monkeypatch.setattr(chat_api, "get_thread", AsyncMock(return_value={"id": thread_id, "title": "x"}))
        body = ChatStreamRequest(
            threadId=thread_id,
            messages=[UIMessage(id="m1", role="assistant", parts=[UIMessagePart(type="text", text="hi")])],
        )

        with pytest.raises(HTTPException) as exc_info:
            await stream_chat(body, current_user=_current_user(), client=MagicMock())

        assert exc_info.value.status_code == 400

    async def test_returns_400_for_an_empty_message_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        thread_id = uuid.uuid4()
        monkeypatch.setattr(chat_api, "get_thread", AsyncMock(return_value={"id": thread_id, "title": "x"}))
        body = ChatStreamRequest(threadId=thread_id, messages=[])

        with pytest.raises(HTTPException) as exc_info:
            await stream_chat(body, current_user=_current_user(), client=MagicMock())

        assert exc_info.value.status_code == 400

    async def test_sets_title_on_first_turn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        thread_id = uuid.uuid4()
        monkeypatch.setattr(chat_api, "get_thread", AsyncMock(return_value={"id": thread_id, "title": None}))
        mock_set_title = AsyncMock()
        monkeypatch.setattr(chat_api, "set_thread_title", mock_set_title)
        body = ChatStreamRequest(threadId=thread_id, messages=[_user_message("What did Netflix say?")])

        await stream_chat(body, current_user=_current_user(), client=MagicMock())

        assert mock_set_title.await_count == 1
        assert mock_set_title.call_args.kwargs["thread_id"] == thread_id
        assert mock_set_title.call_args.kwargs["text"] == "What did Netflix say?"

    async def test_does_not_set_title_when_thread_already_has_one(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        thread_id = uuid.uuid4()
        monkeypatch.setattr(
            chat_api, "get_thread", AsyncMock(return_value={"id": thread_id, "title": "Netflix costs"})
        )
        mock_set_title = AsyncMock()
        monkeypatch.setattr(chat_api, "set_thread_title", mock_set_title)
        body = ChatStreamRequest(threadId=thread_id, messages=[_user_message()])

        await stream_chat(body, current_user=_current_user(), client=MagicMock())

        mock_set_title.assert_not_awaited()

    async def test_streams_an_sse_response_with_the_ai_sdk_protocol_headers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        thread_id = uuid.uuid4()
        monkeypatch.setattr(
            chat_api, "get_thread", AsyncMock(return_value={"id": thread_id, "title": "existing title"})
        )
        body = ChatStreamRequest(threadId=thread_id, messages=[_user_message()])

        response = await stream_chat(body, current_user=_current_user(), client=MagicMock())

        assert response.media_type == "text/event-stream"
        assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
