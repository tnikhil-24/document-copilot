import uuid
from datetime import datetime, timezone

from supabase import AsyncClient


async def list_threads(client: AsyncClient) -> list[dict]:
    result = await (
        client.table("chat_threads")
        .select("id, title, updated_at")
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data


async def create_thread(client: AsyncClient, *, user_id: str) -> dict:
    result = await client.table("chat_threads").insert({"user_id": user_id}).execute()
    return result.data[0]


async def set_thread_title(client: AsyncClient, *, thread_id: uuid.UUID, text: str) -> None:
    await (
        client.table("chat_threads")
        .update({"title": _truncate_title(text)})
        .eq("id", str(thread_id))
        .execute()
    )


def _truncate_title(text: str, max_chars: int = 60) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    return truncated[:last_space] if last_space > 0 else truncated


async def get_thread(client: AsyncClient, *, thread_id: uuid.UUID) -> dict | None:
    """Fetch a thread by ID, scoped to the caller by RLS.

    Returns `None` for a thread that doesn't exist *or* one the caller doesn't
    own — RLS filters out the latter before it ever reaches us, so both cases
    collapse into the same lookup and the same 404 at the route layer.
    """
    result = await (
        client.table("chat_threads")
        .select("*")
        .eq("id", str(thread_id))
        .maybe_single()
        .execute()
    )
    return result.data if result is not None else None


async def append_message(client: AsyncClient, *, thread_id: uuid.UUID, role: str, text: str) -> dict:
    result = await (
        client.table("chat_messages")
        .insert({"thread_id": str(thread_id), "role": role, "content": {"text": text}})
        .execute()
    )
    # No updated_at trigger exists — touch manually so the thread list stays ordered.
    now = datetime.now(timezone.utc).isoformat()
    await (
        client.table("chat_threads")
        .update({"updated_at": now})
        .eq("id", str(thread_id))
        .execute()
    )
    return result.data[0]


async def fetch_messages(client: AsyncClient, *, thread_id: uuid.UUID) -> list[dict]:
    result = await (
        client.table("chat_messages")
        .select("*")
        .eq("thread_id", str(thread_id))
        .order("created_at")
        .execute()
    )
    return result.data
