"""ORM models, one per file. Import them all here so Alembic autogenerate
and SQLAlchemy's mapper configuration see the complete schema."""

from app.database.models.base import Base
from app.database.models.chat_message import ChatMessage
from app.database.models.chat_thread import ChatThread
from app.database.models.document_chunk import DocumentChunk
from app.database.models.message_citation import MessageCitation
from app.database.models.profile import Profile
from app.database.models.source_document import SourceDocument

__all__ = [
    "Base",
    "ChatMessage",
    "ChatThread",
    "DocumentChunk",
    "MessageCitation",
    "Profile",
    "SourceDocument",
]
