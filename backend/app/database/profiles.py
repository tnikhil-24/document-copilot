from supabase import AsyncClient


async def get_or_create_profile(client: AsyncClient, user_id: str, email: str) -> dict:
    """Fetch the caller's profile, creating it on first login.

    `upsert(..., ignore_duplicates=True)` makes this race-safe and idempotent —
    concurrent first logins can't create duplicate rows — then a select fetches
    the row whether it was just inserted or already existed. RLS scopes both
    operations to `auth.uid() = id`, so the user-scoped client only ever
    touches its own row.
    """
    await client.table("profiles").upsert(
        {"id": user_id, "email": email},
        on_conflict="id",
        ignore_duplicates=True,
    ).execute()

    result = await client.table("profiles").select("*").eq("id", user_id).single().execute()
    return result.data
