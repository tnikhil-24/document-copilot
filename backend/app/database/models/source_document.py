import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import TIMESTAMP, Base

if TYPE_CHECKING:
    from app.database.models.document_chunk import DocumentChunk


class SourceDocument(Base):
    """A normalized SEC filing — extracted Markdown plus filing metadata."""

    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    ticker: Mapped[str] = mapped_column(index=True)
    company_name: Mapped[str]
    cik: Mapped[str] = mapped_column(index=True)
    filing_type: Mapped[str]
    filing_date: Mapped[date]
    accession_number: Mapped[str] = mapped_column(unique=True)
    source_url: Mapped[str]
    content_markdown: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", order_by="DocumentChunk.chunk_index", passive_deletes=True
    )
