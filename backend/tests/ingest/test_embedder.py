from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ingest.embedder import embed, _BATCH_SIZE


def _make_mock_client(vectors: list[list[float]]) -> MagicMock:
    """Return a mock OpenAI client whose embeddings.create returns the given vectors."""
    item = lambda v: MagicMock(embedding=v)
    response = MagicMock()
    response.data = [item(v) for v in vectors]
    client = MagicMock()
    client.embeddings.create.return_value = response
    return client


@patch("ingest.embedder.OpenAI")
def test_returns_one_vector_per_input(mock_openai: MagicMock) -> None:
    texts = ["hello", "world", "foo"]
    vectors = [[float(i)] * 3 for i in range(len(texts))]
    mock_openai.return_value = _make_mock_client(vectors)

    result = embed(texts)

    assert len(result) == len(texts)
    assert result == vectors


@patch("ingest.embedder.OpenAI")
def test_empty_input_returns_empty_list(mock_openai: MagicMock) -> None:
    mock_openai.return_value = _make_mock_client([])

    result = embed([])

    assert result == []
    mock_openai.return_value.embeddings.create.assert_not_called()


@patch("ingest.embedder.OpenAI")
def test_batches_large_input(mock_openai: MagicMock) -> None:
    n = _BATCH_SIZE + 10
    texts = [f"text {i}" for i in range(n)]

    first_batch_vectors = [[float(i)] * 2 for i in range(_BATCH_SIZE)]
    second_batch_vectors = [[float(i + _BATCH_SIZE)] * 2 for i in range(10)]

    client = MagicMock()
    first_response = MagicMock()
    first_response.data = [MagicMock(embedding=v) for v in first_batch_vectors]
    second_response = MagicMock()
    second_response.data = [MagicMock(embedding=v) for v in second_batch_vectors]
    client.embeddings.create.side_effect = [first_response, second_response]
    mock_openai.return_value = client

    result = embed(texts)

    assert len(result) == n
    assert client.embeddings.create.call_count == 2
    first_call_input = client.embeddings.create.call_args_list[0].kwargs["input"]
    second_call_input = client.embeddings.create.call_args_list[1].kwargs["input"]
    assert len(first_call_input) == _BATCH_SIZE
    assert len(second_call_input) == 10


@patch("ingest.embedder.OpenAI")
def test_uses_settings_model_and_dimensions(mock_openai: MagicMock) -> None:
    from app.config import settings

    texts = ["test"]
    mock_openai.return_value = _make_mock_client([[0.0] * settings.openai_embedding_dimensions])

    embed(texts)

    call_kwargs = mock_openai.return_value.embeddings.create.call_args.kwargs
    assert call_kwargs["model"] == settings.openai_embedding_model
    assert call_kwargs["dimensions"] == settings.openai_embedding_dimensions


@patch("ingest.embedder.OpenAI")
def test_exact_batch_boundary(mock_openai: MagicMock) -> None:
    """Exactly _BATCH_SIZE inputs should produce exactly one API call."""
    texts = [f"t{i}" for i in range(_BATCH_SIZE)]
    vectors = [[0.0]] * _BATCH_SIZE
    mock_openai.return_value = _make_mock_client(vectors)

    result = embed(texts)

    assert len(result) == _BATCH_SIZE
    mock_openai.return_value.embeddings.create.assert_called_once()
