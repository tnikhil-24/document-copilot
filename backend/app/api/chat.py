import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from supabase import AsyncClient

from app.auth.dependencies import CurrentUser, get_current_user, get_user_client
from app.chat.messages import ChatTurnMessage, UIMessage, to_internal, to_ui_message
from app.chat.orchestrator import run_turn
from app.chat.streaming import UI_MESSAGE_STREAM_HEADERS, encode_ui_message_stream
from app.database.chats import (
    create_thread,
    fetch_messages,
    get_thread,
    list_threads,
    set_thread_title,
)

router = APIRouter(tags=["chat"])


class ThreadSummary(BaseModel):
    id: uuid.UUID
    title: str | None
    updated_at: datetime


class ThreadDetail(BaseModel):
    id: uuid.UUID
    title: str | None
    messages: list[UIMessage]


class ChatStreamRequest(BaseModel):
    thread_id: uuid.UUID = Field(alias="threadId")
    messages: list[UIMessage]


@router.get("/threads")
async def get_threads(
    current_user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_user_client),
) -> list[ThreadSummary]:
    rows = await list_threads(client)
    return [ThreadSummary.model_validate(row) for row in rows]


@router.post("/threads")
async def post_threads(
    current_user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_user_client),
) -> ThreadSummary:
    thread = await create_thread(client, user_id=str(current_user.id))
    return ThreadSummary.model_validate(thread)


@router.get("/threads/{thread_id}")
async def get_thread_detail(
    thread_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_user_client),
) -> ThreadDetail:
    thread = await get_thread(client, thread_id=thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    rows = await fetch_messages(client, thread_id=thread_id)
    messages = [
        to_ui_message(
            ChatTurnMessage(role=row["role"], text=row["content"]["text"]),
            message_id=row["id"],
        )
        for row in rows
    ]
    return ThreadDetail(id=thread["id"], title=thread.get("title"), messages=messages)


@router.post("/chat/stream")
async def stream_chat(
    body: ChatStreamRequest,
    current_user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_user_client),
) -> StreamingResponse:
    """Stream one assistant turn for `threadId` as an AI SDK UI message stream."""
    thread = await get_thread(client, thread_id=body.thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    if not body.messages or body.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Expected the latest message to be from the user")

    user_message = to_internal(body.messages[-1])

    if thread.get("title") is None:
        await set_thread_title(client, thread_id=body.thread_id, text=user_message.text)

    events = run_turn(client, thread_id=body.thread_id, user_message=user_message)
    message_id = str(uuid.uuid4())

    return StreamingResponse(
        encode_ui_message_stream(events, message_id=message_id),
        media_type="text/event-stream",
        headers=UI_MESSAGE_STREAM_HEADERS,
    )
