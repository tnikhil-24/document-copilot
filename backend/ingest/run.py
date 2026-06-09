from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.database.documents import ChunkRecord, get_document_by_accession, insert_document_with_chunks
from ingest.chunker import chunk_markdown
from ingest.embedder import embed
from ingest.parser import html_to_markdown


def _run() -> None:
    manifest_path = Path(settings.manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    downloads_dir = manifest_path.parent
    db_url = settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(db_url)

    for filing in manifest["filings"]:
        accession = filing["accession_number"]
        ticker = filing["ticker"]
        filing_date = filing["filing_date"]

        with Session(engine) as session:
            if get_document_by_accession(session, accession) is not None:
                print(f"[{ticker}] [{filing_date}] — skipped")
                continue

        htm_path = downloads_dir / filing["local_path"].replace("\\", "/")
        markdown = html_to_markdown(htm_path.read_bytes())
        chunks = chunk_markdown(markdown)
        vectors = embed([c.content for c in chunks])

        db_chunks: list[ChunkRecord] = [
            {
                "chunk_index": c.chunk_index,
                "content": c.content,
                "token_count": c.token_count,
                "embedding": vectors[i],
                "section": c.metadata["section"],
                "char_start": c.metadata["char_start"],
                "char_end": c.metadata["char_end"],
            }
            for i, c in enumerate(chunks)
        ]

        doc_fields = {
            "ticker": ticker,
            "company_name": filing.get("company_name", ticker),
            "cik": filing["cik"],
            "filing_type": filing["form"],
            "filing_date": date.fromisoformat(filing_date),
            "accession_number": accession,
            "source_url": filing["source_url"],
            "content_markdown": markdown,
        }

        with Session(engine) as session:
            insert_document_with_chunks(session, doc_fields, db_chunks)
            session.commit()

        print(f"[{ticker}] [{filing_date}] — {len(db_chunks)} chunks ingested")


if __name__ == "__main__":
    _run()
