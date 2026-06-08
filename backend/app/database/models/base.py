"""Shared declarative base and column helpers for ORM models.

Every model must inherit from `Base` so Alembic autogenerate sees one
consistent `Base.metadata`.
"""

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase

TIMESTAMP = DateTime(timezone=True)


class Base(DeclarativeBase):
    pass
