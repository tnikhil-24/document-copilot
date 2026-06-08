import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import TIMESTAMP, Base

if TYPE_CHECKING:
    from app.database.models.chat_thread import ChatThread


class Profile(Base):
    """One row per authenticated user, keyed by Supabase `auth.users.id`."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    full_name: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    threads: Mapped[list["ChatThread"]] = relationship(back_populates="owner", passive_deletes=True)
