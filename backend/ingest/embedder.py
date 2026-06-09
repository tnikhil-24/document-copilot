from __future__ import annotations

from openai import OpenAI

from app.config import settings

# OpenAI caps embedding requests at 300k tokens. With chunks up to ~550 tokens
# (500 chunk_size + 50 overlap), 500 items keeps each request under that limit.
_BATCH_SIZE = 500


def embed(texts: list[str]) -> list[list[float]]:
    client = OpenAI(api_key=settings.openai_api_key)
    results: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=batch,
            dimensions=settings.openai_embedding_dimensions,
        )
        results.extend(item.embedding for item in response.data)
    return results
