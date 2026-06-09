from __future__ import annotations

from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.document_chunk import DocumentChunk
from app.database.models.source_document import SourceDocument


class ChunkRecord(TypedDict):
    chunk_index: int
    content: str
    token_count: int
    embedding: list[float]
    section: str
    char_start: int
    char_end: int


def get_document_by_accession(session: Session, accession_number: str) -> SourceDocument | None:
    return session.scalar(
        select(SourceDocument).where(SourceDocument.accession_number == accession_number)
    )


def insert_document_with_chunks(
    session: Session,
    doc_fields: dict,
    chunks: list[ChunkRecord],
) -> SourceDocument:
    doc = SourceDocument(**doc_fields)
    session.add(doc)
    session.flush()  # populate doc.id before building chunk foreign keys

    filing_date = doc.filing_date
    base_metadata = {
        "ticker": doc.ticker,
        "company_name": doc.company_name,
        "filing_type": doc.filing_type,
        "filing_date": filing_date.isoformat(),
        "year": filing_date.year,
        "accession_number": doc.accession_number,
    }

    for chunk in chunks:
        session.add(
            DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                token_count=chunk["token_count"],
                embedding=chunk["embedding"],
                chunk_metadata={
                    **base_metadata,
                    "section": chunk["section"],
                    "char_start": chunk["char_start"],
                    "char_end": chunk["char_end"],
                },
            )
        )

    return doc
