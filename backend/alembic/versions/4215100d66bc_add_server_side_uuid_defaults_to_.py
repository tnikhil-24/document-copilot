"""add server-side uuid defaults to primary keys

Revision ID: 4215100d66bc
Revises: 3404a57ed514
Create Date: 2026-06-08 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4215100d66bc'
down_revision: Union[str, Sequence[str], None] = '3404a57ed514'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Every `id` column was created without a server-side default, so any insert that
# bypasses the SQLAlchemy ORM (e.g. the Supabase/postgrest client the app actually
# uses) sends no `id` and violates the not-null constraint. `gen_random_uuid()` has
# been built into Postgres core since v13, so no extension is required.
_TABLES = ["chat_threads", "chat_messages", "message_citations", "source_documents", "document_chunks"]


def upgrade() -> None:
    for table in _TABLES:
        op.alter_column(table, "id", server_default=sa.text("gen_random_uuid()"))


def downgrade() -> None:
    for table in _TABLES:
        op.alter_column(table, "id", server_default=None)
