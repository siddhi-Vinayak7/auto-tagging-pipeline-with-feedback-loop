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

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# ---------------------------------------------------------------------------
# posts
# ---------------------------------------------------------------------------

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
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
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,           # ix_model_suggestions_post_id
    )
    # PostgreSQL ARRAY(Text) — maximum 3 items enforced at application layer
    suggested_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
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
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,           # ix_human_corrections_post_id
    )
    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_suggestions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,          # uq_human_corrections_suggestion_id — one correction per suggestion
    )
    final_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
    )
    # Precomputed agreement fields — see docs/SCHEMA.md for rationale
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tags_added: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
    )
    tags_removed: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
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
