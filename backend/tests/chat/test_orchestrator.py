import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.chat import orchestrator
from app.chat.messages import ChatTurnMessage
from app.chat.orchestrator import run_turn
from app.chat.streaming import ChatStreamEvent, CompletionEvent, ErrorEvent, TextDeltaEvent

pytestmark = pytest.mark.anyio


async def _drain(events: AsyncIterator[ChatStreamEvent]) -> list[ChatStreamEvent]:
    return [event async for event in events]


class TestRunTurn:
    async def test_persists_both_messages_and_streams_the_stub_reply(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        thread_id = uuid.uuid4()
        client = MagicMock()
        append = AsyncMock(return_value={"id": "msg-1"})
        monkeypatch.setattr(orchestrator, "append_message", append)

        events = await _drain(
            run_turn(client, thread_id=thread_id, user_message=ChatTurnMessage(role="user", text="What's new?"))
        )

        # Sequence: any number of text deltas that reconstruct the stub reply, then completion.
        *deltas, last = events
        assert all(isinstance(event, TextDeltaEvent) for event in deltas)
        assert deltas, "expected the reply to stream as at least one delta"
        assert "".join(event.delta for event in deltas) == orchestrator._STUB_REPLY
        assert last == CompletionEvent()

        user_call, assistant_call = append.await_args_list
        assert user_call.args == (client,)
        assert user_call.kwargs == {"thread_id": thread_id, "role": "user", "text": "What's new?"}
        assert assistant_call.kwargs == {
            "thread_id": thread_id,
            "role": "assistant",
            "text": orchestrator._STUB_REPLY,
        }

    async def test_persists_the_user_message_before_streaming_the_reply(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The question must be saved before we start streaming the answer —
        otherwise a client that disconnects mid-stream loses its own message."""
        thread_id = uuid.uuid4()
        client = MagicMock()
        append = AsyncMock(return_value={"id": "msg-1"})
        monkeypatch.setattr(orchestrator, "append_message", append)

        events = run_turn(client, thread_id=thread_id, user_message=ChatTurnMessage(role="user", text="hi"))
        first_event = await events.__anext__()

        assert isinstance(first_event, TextDeltaEvent)
        assert append.await_count == 1
        assert append.await_args_list[0].kwargs["role"] == "user"

    async def test_emits_an_error_event_when_persistence_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        thread_id = uuid.uuid4()
        client = MagicMock()
        monkeypatch.setattr(orchestrator, "append_message", AsyncMock(side_effect=RuntimeError("db unreachable")))

        events = await _drain(
            run_turn(client, thread_id=thread_id, user_message=ChatTurnMessage(role="user", text="hi"))
        )

        assert events == [ErrorEvent(message="Something went wrong while generating a response.")]


class TestStreamTokens:
    def test_concatenating_tokens_reproduces_the_original_text(self) -> None:
        text = "Answer not yet implemented. Streaming lands here first."

        assert "".join(orchestrator._stream_tokens(text)) == text
