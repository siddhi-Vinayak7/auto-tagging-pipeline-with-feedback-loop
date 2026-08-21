"""
models.py
---------
SQLAlchemy ORM models for the three core tables:
  - posts
  - model_suggestions
  - human_corrections

ARRAY columns use PostgreSQL's native ARRAY type via sqlalchemy.dialects.postgresql.
All foreign-key relationships include cascade rules so deleting a post cascades
to its suggestions and corrections.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator, CHAR

from database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's native UUID type, otherwise uses CHAR(36), storing stringized UUIDs.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(str(value)))
        return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value))
        return value


ArrayType = ARRAY(Text).with_variant(JSON, "sqlite")


# ---------------------------------------------------------------------------
# posts
# ---------------------------------------------------------------------------

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    suggestions: Mapped[list["ModelSuggestion"]] = relationship(
        "ModelSuggestion",
        back_populates="post",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# model_suggestions
# ---------------------------------------------------------------------------

class ModelSuggestion(Base):
    __tablename__ = "model_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,           # ix_model_suggestions_post_id
    )
    # PostgreSQL ARRAY(Text) / SQLite JSON — maximum 3 items enforced at application layer
    suggested_tags: Mapped[list[str]] = mapped_column(
        ArrayType,
        nullable=False,
        default=list,
    )
    was_fallback: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    post: Mapped["Post"] = relationship("Post", back_populates="suggestions")
    corrections: Mapped[list["HumanCorrection"]] = relationship(
        "HumanCorrection",
        back_populates="suggestion",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# human_corrections
# ---------------------------------------------------------------------------

class HumanCorrection(Base):
    __tablename__ = "human_corrections"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,           # ix_human_corrections_post_id
    )
    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("model_suggestions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,          # uq_human_corrections_suggestion_id — one correction per suggestion
    )
    final_tags: Mapped[list[str]] = mapped_column(
        ArrayType,
        nullable=False,
        default=list,
    )
    # Precomputed agreement fields — see docs/SCHEMA.md for rationale
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tags_added: Mapped[list[str]] = mapped_column(
        ArrayType,
        nullable=False,
        default=list,
    )
    tags_removed: Mapped[list[str]] = mapped_column(
        ArrayType,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    post: Mapped["Post"] = relationship("Post")
    suggestion: Mapped["ModelSuggestion"] = relationship(
        "ModelSuggestion", back_populates="corrections"
    )
