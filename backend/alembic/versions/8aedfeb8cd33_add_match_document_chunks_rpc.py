"""add match_document_chunks rpc

Revision ID: 8aedfeb8cd33
Revises: 4215100d66bc
Create Date: 2026-06-11 01:33:00.383823

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8aedfeb8cd33'
down_revision: Union[str, Sequence[str], None] = '4215100d66bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Dimension must match document_chunks.embedding (vector(1536), set via
# settings.openai_embedding_dimensions). Postgres function signatures can't
# reference app config, so it's hardcoded here as in prior migrations.
_VECTOR_DIM = 1536

_FUNCTION_SQL = f"""
CREATE FUNCTION match_document_chunks(
    query_embedding vector({_VECTOR_DIM}),
    match_count int,
    filter_ticker text DEFAULT NULL,
    filter_year int DEFAULT NULL
)
RETURNS TABLE (
    chunk_id uuid,
    content text,
    ticker text,
    company_name text,
    filing_type text,
    filing_date text,
    section text
)
LANGUAGE sql STABLE
AS $$
    SELECT
        document_chunks.id AS chunk_id,
        document_chunks.content,
        document_chunks.metadata ->> 'ticker' AS ticker,
        document_chunks.metadata ->> 'company_name' AS company_name,
        document_chunks.metadata ->> 'filing_type' AS filing_type,
        document_chunks.metadata ->> 'filing_date' AS filing_date,
        document_chunks.metadata ->> 'section' AS section
    FROM document_chunks
    WHERE (filter_ticker IS NULL OR document_chunks.metadata ->> 'ticker' = filter_ticker)
      AND (filter_year IS NULL OR (document_chunks.metadata ->> 'year')::int = filter_year)
    ORDER BY document_chunks.embedding <=> query_embedding
    LIMIT match_count;
$$;
"""

_DROP_FUNCTION_SQL = f"DROP FUNCTION match_document_chunks(vector({_VECTOR_DIM}), int, text, int)"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(_FUNCTION_SQL)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(_DROP_FUNCTION_SQL)
