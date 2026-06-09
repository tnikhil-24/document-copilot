from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database.documents import ChunkRecord, get_document_by_accession, insert_document_with_chunks

pytestmark = pytest.mark.integration


@pytest.fixture
def session():
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        trans = conn.begin()
        with Session(conn) as sess:
            yield sess
        trans.rollback()


@pytest.fixture
def accession() -> str:
    return f"0001234567-24-{uuid.uuid4().hex[:6]}"


def _doc_fields(accession_number: str) -> dict:
    return {
        "ticker": "NFLX",
        "company_name": "Netflix, Inc.",
        "cik": "1065280",
        "filing_type": "10-K",
        "filing_date": date(2024, 1, 26),
        "accession_number": accession_number,
        "source_url": "https://www.sec.gov/Archives/edgar/data/1065280/000106528024000001/nflx-20231231.htm",
        "content_markdown": "# Annual Report\n\nContent here.",
    }


def _chunk(index: int = 0) -> ChunkRecord:
    return {
        "chunk_index": index,
        "content": "Revenue was 33723 million.",
        "token_count": 6,
        "embedding": [0.0] * 1536,
        "section": "Item 7",
        "char_start": 0,
        "char_end": 26,
    }


def test_get_document_by_accession_returns_none_for_unknown(session: Session) -> None:
    result = get_document_by_accession(session, "does-not-exist")
    assert result is None


def test_insert_and_retrieve_by_accession(session: Session, accession: str) -> None:
    insert_document_with_chunks(session, _doc_fields(accession), [_chunk()])

    retrieved = get_document_by_accession(session, accession)

    assert retrieved is not None
    assert retrieved.ticker == "NFLX"
    assert retrieved.accession_number == accession


def test_insert_creates_correct_chunk_count_and_metadata(session: Session, accession: str) -> None:
    doc = insert_document_with_chunks(session, _doc_fields(accession), [_chunk(0), _chunk(1)])
    session.flush()
    session.refresh(doc)

    assert len(doc.chunks) == 2

    meta = doc.chunks[0].chunk_metadata
    assert meta["ticker"] == "NFLX"
    assert meta["company_name"] == "Netflix, Inc."
    assert meta["filing_type"] == "10-K"
    assert meta["filing_date"] == "2024-01-26"
    assert meta["year"] == 2024
    assert meta["accession_number"] == accession
    assert meta["section"] == "Item 7"
    assert meta["char_start"] == 0
    assert meta["char_end"] == 26


def test_duplicate_accession_raises_integrity_error(session: Session, accession: str) -> None:
    insert_document_with_chunks(session, _doc_fields(accession), [_chunk()])
    session.flush()

    with pytest.raises(IntegrityError):
        insert_document_with_chunks(session, _doc_fields(accession), [_chunk()])
        session.flush()
