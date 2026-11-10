from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Logical PostgreSQL schemas defined in NEX-DOC-007 §3.1
LOGICAL_SCHEMAS: tuple[str, ...] = (
    "core",
    "market",
    "fundamental",
    "analytics",
    "ml",
    "news",
    "portfolio",
    "engagement",
    "ops",
)

# SQL naming conventions defined in NEX-DOC-007 §17
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix__%(table_name)s__%(column_0_label)s",
    "uq": "uq__%(table_name)s__%(column_0_name)s",
    "ck": "ck__%(table_name)s__%(constraint_name)s",
    "fk": "fk__%(table_name)s__%(column_0_name)s__%(referred_table_name)s",
    "pk": "pk__%(table_name)s",
}


class Base(DeclarativeBase):
    """Base SQLAlchemy 2 declarative model shared by future Phase 2+ domain models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
