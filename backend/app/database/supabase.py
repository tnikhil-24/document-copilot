from supabase import AsyncClient, AsyncClientOptions, create_async_client

from app.config import settings


async def create_admin_client() -> AsyncClient:
    """Service-role client for privileged backend-only writes. Bypasses RLS."""
    return await create_async_client(
        settings.supabase_url, settings.supabase_service_role_key
    )


async def create_user_client(access_token: str) -> AsyncClient:
    """User-scoped client that enforces RLS as the authenticated user behind `access_token`."""
    options = AsyncClientOptions(headers={"Authorization": f"Bearer {access_token}"})
    return await create_async_client(
        settings.supabase_url, settings.supabase_anon_key, options
    )
