from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.retrieval.retriever import search_chunks

pytestmark = pytest.mark.anyio


def _client_with_rpc(rows: list[dict]) -> MagicMock:
    client = MagicMock()
    client.rpc.return_value.execute = AsyncMock(return_value=MagicMock(data=rows))
    return client


def _mock_openai(embedding: list[float]) -> MagicMock:
    response = MagicMock()
    response.data = [MagicMock(embedding=embedding)]
    openai_client = MagicMock()
    openai_client.embeddings.create = AsyncMock(return_value=response)
    mock_openai = MagicMock()
    mock_openai.return_value = openai_client
    return mock_openai


class TestSearchChunks:
    @patch("app.retrieval.retriever.AsyncOpenAI")
    async def test_embeds_the_query_text(self, mock_openai: MagicMock) -> None:
        embedding = [0.1] * settings.openai_embedding_dimensions
        mock_openai.return_value = _mock_openai(embedding).return_value
        client = _client_with_rpc([])

        await search_chunks(client, "What did Netflix say about content costs?")

        call_kwargs = mock_openai.return_value.embeddings.create.call_args.kwargs
        assert call_kwargs["input"] == "What did Netflix say about content costs?"
        assert call_kwargs["model"] == settings.openai_embedding_model
        assert call_kwargs["dimensions"] == settings.openai_embedding_dimensions

    @patch("app.retrieval.retriever.AsyncOpenAI")
    async def test_calls_rpc_with_embedding_and_default_params(self, mock_openai: MagicMock) -> None:
        embedding = [0.2] * settings.openai_embedding_dimensions
        mock_openai.return_value = _mock_openai(embedding).return_value
        client = _client_with_rpc([])

        await search_chunks(client, "query text")

        client.rpc.assert_called_once_with(
            "match_document_chunks",
            {
                "query_embedding": embedding,
                "match_count": 8,
                "filter_ticker": None,
                "filter_year": None,
            },
        )

    @patch("app.retrieval.retriever.AsyncOpenAI")
    async def test_passes_through_ticker_year_and_top_k(self, mock_openai: MagicMock) -> None:
        embedding = [0.3] * settings.openai_embedding_dimensions
        mock_openai.return_value = _mock_openai(embedding).return_value
        client = _client_with_rpc([])

        await search_chunks(client, "query text", ticker="NFLX", year=2023, top_k=3)

        client.rpc.assert_called_once_with(
            "match_document_chunks",
            {
                "query_embedding": embedding,
                "match_count": 3,
                "filter_ticker": "NFLX",
                "filter_year": 2023,
            },
        )

    @patch("app.retrieval.retriever.AsyncOpenAI")
    async def test_returns_chunk_rows_from_rpc(self, mock_openai: MagicMock) -> None:
        embedding = [0.4] * settings.openai_embedding_dimensions
        mock_openai.return_value = _mock_openai(embedding).return_value
        rows = [
            {
                "chunk_id": "c1",
                "content": "Content costs rose...",
                "ticker": "NFLX",
                "company_name": "Netflix, Inc.",
                "filing_type": "10-K",
                "filing_date": "2024-01-26",
                "section": "Item 7",
            }
        ]
        client = _client_with_rpc(rows)

        result = await search_chunks(client, "query text")

        assert result == rows
