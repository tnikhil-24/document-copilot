"""Translates between the AI SDK's UI message wire format and the plain
role/text representation the orchestrator and assistant operate on.

Keeping the two separate means a richer wire format (tool calls, reasoning,
file parts, ...) can evolve at the HTTP boundary without the orchestrator or
agent ever needing to understand AI SDK message parts.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

Role = Literal["user", "assistant", "system"]


class UIMessagePart(BaseModel):
    """One part of an AI SDK UI message. Only `text` parts are produced or
    consumed today — richer part types arrive with the real agent."""

    type: Literal["text"]
    text: str


class UIMessage(BaseModel):
    """A message in the AI SDK UI message wire format."""

    id: str
    role: Role
    parts: list[UIMessagePart]


@dataclass(frozen=True)
class ChatTurnMessage:
    """Plain role + text view of a message — what the orchestrator, persistence
    layer, and (later) assistant operate on, decoupled from wire-format parts."""

    role: Role
    text: str


def to_internal(message: UIMessage) -> ChatTurnMessage:
    """Flatten a UI message's text parts into the internal representation."""
    text = "".join(part.text for part in message.parts if part.type == "text")
    return ChatTurnMessage(role=message.role, text=text)


def to_ui_message(message: ChatTurnMessage, *, message_id: str) -> UIMessage:
    """Wrap the internal representation back into a UI message for the wire."""
    return UIMessage(
        id=message_id,
        role=message.role,
        parts=[UIMessagePart(type="text", text=message.text)],
    )
