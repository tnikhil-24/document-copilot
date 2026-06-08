"""Coordinates one chat turn end to end.

This is the seam a later slice swaps from a hardcoded stub to a real
PydanticAI agent: the route layer only ever sees `run_turn` and the
`ChatStreamEvent` sequence it yields, so neither has to change when the
reply stops being a canned string and starts being a grounded answer.
"""

import re
import uuid
from collections.abc import AsyncIterator

from supabase import AsyncClient

from app.chat.messages import ChatTurnMessage
from app.chat.streaming import ChatStreamEvent, CompletionEvent, ErrorEvent, TextDeltaEvent
from app.database.chats import append_message

_STUB_REPLY = (
    "Answer not yet implemented. Retrieval and grounding land in a later slice — "
    "for now this reply only proves the streaming and persistence plumbing works."
)

_TOKEN_PATTERN = re.compile(r"\S+\s*")


def _stream_tokens(text: str) -> list[str]:
    """Split `text` into word-plus-trailing-whitespace chunks so the stub
    streams token by token while `"".join(tokens) == text` stays exact —
    that's what lets the persisted reply match what the client rendered."""
    return _TOKEN_PATTERN.findall(text)


async def run_turn(
    client: AsyncClient, *, thread_id: uuid.UUID, user_message: ChatTurnMessage
) -> AsyncIterator[ChatStreamEvent]:
    """Persist the user's message, stream a reply, persist the reply, done.

    Failures are caught and turned into an `ErrorEvent` rather than left to
    propagate: by the time we're streaming, the response has already started
    with a 200 and SSE headers, so an in-band error event is the only way
    left to tell the client the turn failed — there's no HTTP status left
    to change.
    """
    try:
        await append_message(client, thread_id=thread_id, role=user_message.role, text=user_message.text)

        reply = _STUB_REPLY
        for token in _stream_tokens(reply):
            yield TextDeltaEvent(delta=token)

        await append_message(client, thread_id=thread_id, role="assistant", text=reply)
    except Exception:
        yield ErrorEvent(message="Something went wrong while generating a response.")
        return

    yield CompletionEvent()
