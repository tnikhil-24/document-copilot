import uuid

from supabase import AsyncClient


async def get_or_create_thread(client: AsyncClient, *, user_id: str) -> dict:
    """Return the signed-in user's thread, creating one on first visit.

    Slice 1 gives each analyst exactly one thread — `order` + `limit(1)` picks
    the oldest if more than one ever exists, so behavior stays well-defined
    once Slice 2 adds multi-thread support on top of these same functions.
    """
    existing = await (
        client.table("chat_threads")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at")
        .limit(1)
        .maybe_single()
        .execute()
    )
    if existing is not None:
        return existing.data

    created = await client.table("chat_threads").insert({"user_id": user_id}).execute()
    return created.data[0]


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
    """Append a message to a thread and return the persisted row."""
    result = await (
        client.table("chat_messages")
        .insert({"thread_id": str(thread_id), "role": role, "content": {"text": text}})
        .execute()
    )
    return result.data[0]


async def fetch_messages(client: AsyncClient, *, thread_id: uuid.UUID) -> list[dict]:
    """Fetch a thread's messages in conversation order."""
    result = await (
        client.table("chat_messages")
        .select("*")
        .eq("thread_id", str(thread_id))
        .order("created_at")
        .execute()
    )
    return result.data
