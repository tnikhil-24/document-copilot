import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from supabase import AsyncClient

from app.auth.dependencies import CurrentUser, get_current_user, get_user_client
from app.chat.messages import ChatTurnMessage, UIMessage, to_internal, to_ui_message
from app.chat.orchestrator import run_turn
from app.chat.streaming import UI_MESSAGE_STREAM_HEADERS, encode_ui_message_stream
from app.database.chats import fetch_messages, get_or_create_thread, get_thread

router = APIRouter(tags=["chat"])


class ThreadResponse(BaseModel):
    id: uuid.UUID
    messages: list[UIMessage]


class ChatStreamRequest(BaseModel):
    thread_id: uuid.UUID = Field(alias="threadId")
    messages: list[UIMessage]


@router.get("/thread")
async def get_thread_route(
    current_user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_user_client),
) -> ThreadResponse:
    """Return the signed-in analyst's thread and its history, auto-creating
    the thread on first visit. Slice 1 gives each analyst exactly one thread."""
    thread = await get_or_create_thread(client, user_id=str(current_user.id))
    rows = await fetch_messages(client, thread_id=thread["id"])

    messages = [
        to_ui_message(
            ChatTurnMessage(role=row["role"], text=row["content"]["text"]),
            message_id=row["id"],
        )
        for row in rows
    ]
    return ThreadResponse(id=thread["id"], messages=messages)


@router.post("/chat/stream")
async def stream_chat(
    body: ChatStreamRequest,
    current_user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_user_client),
) -> StreamingResponse:
    """Stream one assistant turn for `threadId` as an AI SDK UI message stream.

    The reply is a hardcoded stub today — `run_turn` is the seam a later
    slice swaps for a real agent without changing this route or the wire
    contract `encode_ui_message_stream` produces.
    """
    thread = await get_thread(client, thread_id=body.thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    if not body.messages or body.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Expected the latest message to be from the user")

    user_message = to_internal(body.messages[-1])
    events = run_turn(client, thread_id=body.thread_id, user_message=user_message)
    message_id = str(uuid.uuid4())

    return StreamingResponse(
        encode_ui_message_stream(events, message_id=message_id),
        media_type="text/event-stream",
        headers=UI_MESSAGE_STREAM_HEADERS,
    )
