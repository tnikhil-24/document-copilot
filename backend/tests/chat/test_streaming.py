import json
from collections.abc import AsyncIterator

import pytest

from app.chat.streaming import (
    ChatStreamEvent,
    CompletionEvent,
    ErrorEvent,
    TextDeltaEvent,
    encode_ui_message_stream,
)

pytestmark = pytest.mark.anyio


async def _events(*items: ChatStreamEvent) -> AsyncIterator[ChatStreamEvent]:
    for item in items:
        yield item


def _decode(chunk: str) -> dict | str:
    assert chunk.startswith("data: ") and chunk.endswith("\n\n")
    payload = chunk.removeprefix("data: ").rstrip("\n")
    return payload if payload == "[DONE]" else json.loads(payload)


async def _collect(stream: AsyncIterator[str]) -> list[dict | str]:
    return [_decode(chunk) async for chunk in stream]


class TestEncodeUIMessageStream:
    async def test_wraps_text_deltas_in_the_protocol_envelope_and_terminates(self) -> None:
        chunks = await _collect(
            encode_ui_message_stream(
                _events(TextDeltaEvent(delta="Hello "), TextDeltaEvent(delta="world"), CompletionEvent()),
                message_id="msg-1",
            )
        )

        assert chunks == [
            {"type": "start", "messageId": "msg-1"},
            {"type": "start-step"},
            {"type": "text-start", "id": "msg-1-text"},
            {"type": "text-delta", "id": "msg-1-text", "delta": "Hello "},
            {"type": "text-delta", "id": "msg-1-text", "delta": "world"},
            {"type": "text-end", "id": "msg-1-text"},
            {"type": "finish-step"},
            {"type": "finish"},
            "[DONE]",
        ]

    async def test_closes_an_open_text_block_before_emitting_an_error_and_still_terminates(self) -> None:
        chunks = await _collect(
            encode_ui_message_stream(
                _events(TextDeltaEvent(delta="partial answer"), ErrorEvent(message="Something went wrong.")),
                message_id="msg-2",
            )
        )

        assert chunks == [
            {"type": "start", "messageId": "msg-2"},
            {"type": "start-step"},
            {"type": "text-start", "id": "msg-2-text"},
            {"type": "text-delta", "id": "msg-2-text", "delta": "partial answer"},
            {"type": "text-end", "id": "msg-2-text"},
            {"type": "error", "errorText": "Something went wrong."},
            "[DONE]",
        ]

    async def test_skips_the_text_envelope_when_no_text_was_streamed(self) -> None:
        chunks = await _collect(encode_ui_message_stream(_events(CompletionEvent()), message_id="msg-3"))

        assert chunks == [
            {"type": "start", "messageId": "msg-3"},
            {"type": "start-step"},
            {"type": "finish-step"},
            {"type": "finish"},
            "[DONE]",
        ]
