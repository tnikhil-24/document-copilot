from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ingest.chunker import ChunkRecord as ChunkerRecord


def _chunk(index: int = 0) -> ChunkerRecord:
    return ChunkerRecord(
        content="Revenue 1000",
        token_count=3,
        chunk_index=index,
        metadata={"section": "Item 7", "char_start": 0, "char_end": 12},
    )


def _filing(ticker: str, accession: str, htm: str) -> dict:
    return {
        "ticker": ticker,
        "company_name": f"{ticker} Inc.",
        "cik": "0001234567",
        "form": "10-K",
        "filing_date": "2024-01-26",
        "report_date": "2023-12-31",
        "accession_number": accession,
        "primary_document": htm,
        "source_url": f"https://www.sec.gov/{htm}",
        "local_path": htm,
    }


@pytest.fixture
def manifest_dir(tmp_path: Path) -> Path:
    for name in ["a.htm", "b.htm"]:
        (tmp_path / name).write_bytes(b"<p>Content</p>")
    manifest = {
        "source": "SEC EDGAR",
        "generated_at_utc": "2024-01-01T00:00:00",
        "form": "10-K",
        "downloaded_count": 2,
        "filings": [
            _filing("NFLX", "0001065280-24-000001", "a.htm"),
            _filing("TSLA", "0001318605-24-000001", "b.htm"),
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def _patch_all(manifest_dir: Path):
    """Return a context-manager stack that mocks every external boundary."""
    return (
        patch("ingest.run.settings", manifest_path=str(manifest_dir / "manifest.json"), database_url="postgresql://test"),
        patch("ingest.run.create_engine", return_value=MagicMock()),
        patch("ingest.run.Session"),
        patch("ingest.run.html_to_markdown", return_value="# Revenue\n\nContent"),
        patch("ingest.run.chunk_markdown", return_value=[_chunk(0), _chunk(1)]),
        patch("ingest.run.embed", return_value=[[0.1] * 1536, [0.2] * 1536]),
        patch("ingest.run.get_document_by_accession", return_value=None),
        patch("ingest.run.insert_document_with_chunks"),
    )


@patch("ingest.run.insert_document_with_chunks")
@patch("ingest.run.get_document_by_accession", return_value=None)
@patch("ingest.run.embed", return_value=[[0.1] * 1536, [0.2] * 1536])
@patch("ingest.run.chunk_markdown", return_value=[_chunk(0), _chunk(1)])
@patch("ingest.run.html_to_markdown", return_value="# Revenue\n\nContent")
@patch("ingest.run.Session")
@patch("ingest.run.create_engine")
def test_ingests_new_filings(
    mock_engine,
    mock_session_cls,
    mock_html_to_md,
    mock_chunk_md,
    mock_embed,
    mock_get_doc,
    mock_insert,
    manifest_dir: Path,
    capsys,
) -> None:
    session = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=session)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

    with patch("ingest.run.settings", manifest_path=str(manifest_dir / "manifest.json"), database_url="postgresql://test"):
        from ingest import run
        run._run()

    assert mock_insert.call_count == 2
    assert session.commit.call_count == 2

    captured = capsys.readouterr()
    assert "[NFLX]" in captured.out
    assert "[TSLA]" in captured.out
    assert "2 chunks ingested" in captured.out


@patch("ingest.run.insert_document_with_chunks")
@patch("ingest.run.get_document_by_accession")
@patch("ingest.run.embed", return_value=[[0.1] * 1536, [0.2] * 1536])
@patch("ingest.run.chunk_markdown", return_value=[_chunk(0), _chunk(1)])
@patch("ingest.run.html_to_markdown", return_value="# Revenue\n\nContent")
@patch("ingest.run.Session")
@patch("ingest.run.create_engine")
def test_skips_already_ingested_filing(
    mock_engine,
    mock_session_cls,
    mock_html_to_md,
    mock_chunk_md,
    mock_embed,
    mock_get_doc,
    mock_insert,
    manifest_dir: Path,
    capsys,
) -> None:
    session = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=session)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
    # First filing exists, second does not
    mock_get_doc.side_effect = [MagicMock(), None]

    with patch("ingest.run.settings", manifest_path=str(manifest_dir / "manifest.json"), database_url="postgresql://test"):
        from ingest import run
        run._run()

    assert mock_insert.call_count == 1
    captured = capsys.readouterr()
    assert "skipped" in captured.out
    assert "2 chunks ingested" in captured.out


@patch("ingest.run.insert_document_with_chunks")
@patch("ingest.run.get_document_by_accession", return_value=None)
@patch("ingest.run.embed", return_value=[[0.1] * 1536, [0.2] * 1536])
@patch("ingest.run.chunk_markdown", return_value=[_chunk(0), _chunk(1)])
@patch("ingest.run.html_to_markdown", return_value="# Revenue\n\nContent")
@patch("ingest.run.Session")
@patch("ingest.run.create_engine")
def test_passes_correct_doc_fields_to_insert(
    mock_engine,
    mock_session_cls,
    mock_html_to_md,
    mock_chunk_md,
    mock_embed,
    mock_get_doc,
    mock_insert,
    manifest_dir: Path,
) -> None:
    session = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=session)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

    with patch("ingest.run.settings", manifest_path=str(manifest_dir / "manifest.json"), database_url="postgresql://test"):
        from ingest import run
        run._run()

    first_call_doc_fields = mock_insert.call_args_list[0].args[1]
    assert first_call_doc_fields["ticker"] == "NFLX"
    assert first_call_doc_fields["company_name"] == "NFLX Inc."
    assert first_call_doc_fields["filing_type"] == "10-K"
    assert first_call_doc_fields["accession_number"] == "0001065280-24-000001"


@patch("ingest.run.insert_document_with_chunks")
@patch("ingest.run.get_document_by_accession", return_value=None)
@patch("ingest.run.embed", return_value=[[0.1] * 1536, [0.2] * 1536])
@patch("ingest.run.chunk_markdown", return_value=[_chunk(0), _chunk(1)])
@patch("ingest.run.html_to_markdown", return_value="# Revenue\n\nContent")
@patch("ingest.run.Session")
@patch("ingest.run.create_engine")
def test_embedding_attached_to_db_chunks(
    mock_engine,
    mock_session_cls,
    mock_html_to_md,
    mock_chunk_md,
    mock_embed,
    mock_get_doc,
    mock_insert,
    manifest_dir: Path,
) -> None:
    session = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=session)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

    with patch("ingest.run.settings", manifest_path=str(manifest_dir / "manifest.json"), database_url="postgresql://test"):
        from ingest import run
        run._run()

    db_chunks = mock_insert.call_args_list[0].args[2]
    assert db_chunks[0]["embedding"] == [0.1] * 1536
    assert db_chunks[1]["embedding"] == [0.2] * 1536
    assert db_chunks[0]["chunk_index"] == 0
    assert db_chunks[1]["chunk_index"] == 1
    assert db_chunks[0]["section"] == "Item 7"
