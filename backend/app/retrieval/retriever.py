from __future__ import annotations

from openai import AsyncOpenAI
from supabase import AsyncClient

from app.config import settings


async def search_chunks(
    client: AsyncClient,
    query: str,
    *,
    ticker: str | None = None,
    year: int | None = None,
    top_k: int = 8,
) -> list[dict]:
    """Semantic search over `document_chunks` via the `match_document_chunks` RPC.

    Returns full chunk content plus metadata (chunk_id, content, ticker,
    company_name, filing_type, filing_date, section), ordered by cosine
    similarity to `query`.
    """
    embedding = await _embed_query(query)
    result = await client.rpc(
        "match_document_chunks",
        {
            "query_embedding": embedding,
            "match_count": top_k,
            "filter_ticker": ticker,
            "filter_year": year,
        },
    ).execute()
    return result.data


async def _embed_query(query: str) -> list[float]:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=query,
        dimensions=settings.openai_embedding_dimensions,
    )
    return response.data[0].embedding
