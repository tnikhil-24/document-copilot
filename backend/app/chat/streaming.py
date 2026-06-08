"""The turn-level streaming contract and its encoding onto the wire.

`ChatStreamEvent` is the stable seam: the orchestrator emits these three event
types whether it's running the stub or, later, a real PydanticAI agent —
nothing about the route or the wire encoding has to change when that swap
happens. `encode_ui_message_stream` is the one place that knows how to turn
that seam into the AI SDK UI Message Stream Protocol the frontend expects
(server-sent events, `data: <json>` framing, `[DONE]` terminator).
"""

import json
from collections.abc import AsyncIterator
from typing import Literal

from pydantic import BaseModel

UI_MESSAGE_STREAM_HEADERS = {"x-vercel-ai-ui-message-stream": "v1"}


class TextDeltaEvent(BaseModel):
    """An incremental chunk of assistant text."""

    type: Literal["text-delta"] = "text-delta"
    delta: str


class CompletionEvent(BaseModel):
    """The turn finished generating successfully."""

    type: Literal["completion"] = "completion"


class ErrorEvent(BaseModel):
    """The turn failed; nothing further will be emitted for it."""

    type: Literal["error"] = "error"
    message: str


ChatStreamEvent = TextDeltaEvent | CompletionEvent | ErrorEvent


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def encode_ui_message_stream(
    events: AsyncIterator[ChatStreamEvent], *, message_id: str
) -> AsyncIterator[str]:
    """Encode a `ChatStreamEvent` sequence as an AI SDK UI message stream.

    Wraps the assistant's text in the start/text-start/.../text-end/finish
    envelope the protocol expects, and always ends with the `[DONE]`
    terminator — including after an error, so the client's stream settles.
    """
    text_id = f"{message_id}-text"
    text_open = False

    yield _sse({"type": "start", "messageId": message_id})
    yield _sse({"type": "start-step"})

    async for event in events:
        match event:
            case TextDeltaEvent(delta=delta):
                if not text_open:
                    yield _sse({"type": "text-start", "id": text_id})
                    text_open = True
                yield _sse({"type": "text-delta", "id": text_id, "delta": delta})
            case CompletionEvent():
                if text_open:
                    yield _sse({"type": "text-end", "id": text_id})
                    text_open = False
                yield _sse({"type": "finish-step"})
                yield _sse({"type": "finish"})
            case ErrorEvent(message=message):
                if text_open:
                    yield _sse({"type": "text-end", "id": text_id})
                    text_open = False
                yield _sse({"type": "error", "errorText": message})

    yield "data: [DONE]\n\n"
