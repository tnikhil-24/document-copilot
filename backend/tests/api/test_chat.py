import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api import chat as chat_api
from app.api.chat import ChatStreamRequest, get_thread_route, stream_chat
from app.auth.dependencies import CurrentUser
from app.chat.messages import UIMessage, UIMessagePart

pytestmark = pytest.mark.anyio


def _current_user() -> CurrentUser:
    return CurrentUser(id=uuid.uuid4(), email="analyst@driftwood.com", access_token="token", full_name="Analyst One")


def _user_message(text: str = "What did Netflix's 10-K say?") -> UIMessage:
    return UIMessage(id="m1", role="user", parts=[UIMessagePart(type="text", text=text)])


class TestGetThreadRoute:
    async def test_returns_the_thread_and_its_history_as_ui_messages(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        user = _current_user()
        client = MagicMock()
        thread = {"id": uuid.uuid4(), "user_id": str(user.id)}
        rows = [
            {"id": "msg-1", "role": "user", "content": {"text": "hi"}},
            {"id": "msg-2", "role": "assistant", "content": {"text": "hello"}},
        ]
        get_or_create = AsyncMock(return_value=thread)
        fetch = AsyncMock(return_value=rows)
        monkeypatch.setattr(chat_api, "get_or_create_thread", get_or_create)
        monkeypatch.setattr(chat_api, "fetch_messages", fetch)

        response = await get_thread_route(current_user=user, client=client)

        assert response.id == thread["id"]
        assert response.messages == [
            UIMessage(id="msg-1", role="user", parts=[UIMessagePart(type="text", text="hi")]),
            UIMessage(id="msg-2", role="assistant", parts=[UIMessagePart(type="text", text="hello")]),
        ]
        get_or_create.assert_awaited_once_with(client, user_id=str(user.id))
        fetch.assert_awaited_once_with(client, thread_id=thread["id"])


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
        monkeypatch.setattr(chat_api, "get_thread", AsyncMock(return_value={"id": thread_id}))
        body = ChatStreamRequest(
            threadId=thread_id,
            messages=[UIMessage(id="m1", role="assistant", parts=[UIMessagePart(type="text", text="hi")])],
        )

        with pytest.raises(HTTPException) as exc_info:
            await stream_chat(body, current_user=_current_user(), client=MagicMock())

        assert exc_info.value.status_code == 400

    async def test_returns_400_for_an_empty_message_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        thread_id = uuid.uuid4()
        monkeypatch.setattr(chat_api, "get_thread", AsyncMock(return_value={"id": thread_id}))
        body = ChatStreamRequest(threadId=thread_id, messages=[])

        with pytest.raises(HTTPException) as exc_info:
            await stream_chat(body, current_user=_current_user(), client=MagicMock())

        assert exc_info.value.status_code == 400

    async def test_streams_an_sse_response_with_the_ai_sdk_protocol_headers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        thread_id = uuid.uuid4()
        monkeypatch.setattr(chat_api, "get_thread", AsyncMock(return_value={"id": thread_id}))
        body = ChatStreamRequest(threadId=thread_id, messages=[_user_message()])

        response = await stream_chat(body, current_user=_current_user(), client=MagicMock())

        assert response.media_type == "text/event-stream"
        assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
