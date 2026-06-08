"""add vector index and row level security

Revision ID: 3404a57ed514
Revises: 8bbd7ffa76ef
Create Date: 2026-06-08 00:56:02.061428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3404a57ed514'
down_revision: Union[str, Sequence[str], None] = '8bbd7ffa76ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables whose rows belong to a single user, directly (`user_id`) or transitively
# (`chat_messages` -> thread -> user, `message_citations` -> message -> thread -> user).
# Each gets RLS enabled and a single owner-scoped policy covering all operations.
_OWNER_SCOPED_POLICIES = {
    "chat_threads": "auth.uid() = user_id",
    "chat_messages": (
        "EXISTS (SELECT 1 FROM chat_threads t "
        "WHERE t.id = chat_messages.thread_id AND t.user_id = auth.uid())"
    ),
    "message_citations": (
        "EXISTS (SELECT 1 FROM chat_messages m "
        "JOIN chat_threads t ON t.id = m.thread_id "
        "WHERE m.id = message_citations.message_id AND t.user_id = auth.uid())"
    ),
}

# Shared corpus tables: every authenticated analyst can read all rows (filings are
# read by many analysts), but only the service-role client (bypasses RLS) ingests them.
_SHARED_READ_ONLY_TABLES = ["source_documents", "document_chunks"]


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )

    op.execute("ALTER TABLE profiles ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY profiles_select_own ON profiles "
        "FOR SELECT USING (auth.uid() = id)"
    )
    op.execute(
        "CREATE POLICY profiles_insert_own ON profiles "
        "FOR INSERT WITH CHECK (auth.uid() = id)"
    )
    op.execute(
        "CREATE POLICY profiles_update_own ON profiles "
        "FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id)"
    )

    for table, condition in _OWNER_SCOPED_POLICIES.items():
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_owner_all ON {table} "
            f"FOR ALL USING ({condition}) WITH CHECK ({condition})"
        )

    for table in _SHARED_READ_ONLY_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_read_authenticated ON {table} "
            "FOR SELECT TO authenticated USING (true)"
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in reversed(_SHARED_READ_ONLY_TABLES):
        op.execute(f"DROP POLICY {table}_read_authenticated ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    for table in reversed(list(_OWNER_SCOPED_POLICIES)):
        op.execute(f"DROP POLICY {table}_owner_all ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY profiles_update_own ON profiles")
    op.execute("DROP POLICY profiles_insert_own ON profiles")
    op.execute("DROP POLICY profiles_select_own ON profiles")
    op.execute("ALTER TABLE profiles DISABLE ROW LEVEL SECURITY")

    op.execute("DROP INDEX ix_document_chunks_embedding_hnsw")
