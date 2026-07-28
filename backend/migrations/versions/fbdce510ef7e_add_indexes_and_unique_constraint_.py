"""add_indexes_and_unique_constraint_suggestion_id

Revision ID: fbdce510ef7e
Revises: f9c935596961
Create Date: 2026-07-28

Hardening migration on top of the initial schema:

1. UNIQUE constraint on human_corrections.suggestion_id
   -- A suggestion can only ever produce one correction.  Without this a
   retried or duplicated confirm-call would insert a second row and inflate
   the total denominator of agreement_rate without a matching numerator,
   silently skewing every metric forever.

2. Non-unique index on model_suggestions.post_id
   -- /api/metrics and the suggestion-list endpoint both filter by post_id.
   Without an index Postgres does a full-table seq-scan; with one it uses
   an index scan that scales O(log n) regardless of table size.

3. Non-unique index on human_corrections.post_id
   -- Same reasoning: post-scoped correction lookups and the metrics
   aggregation JOIN on this column.

4. The UNIQUE constraint on human_corrections.suggestion_id already
   creates an implicit unique index, so no separate CREATE INDEX is needed
   for that column.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "fbdce510ef7e"
down_revision = "f9c935596961"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. UNIQUE constraint on human_corrections.suggestion_id
    #    PostgreSQL automatically creates a unique index to enforce this,
    #    so no separate CREATE INDEX is needed for that column.
    # ------------------------------------------------------------------
    op.create_unique_constraint(
        "uq_human_corrections_suggestion_id",
        "human_corrections",
        ["suggestion_id"],
    )

    # ------------------------------------------------------------------
    # 2. Index on model_suggestions.post_id
    # ------------------------------------------------------------------
    op.create_index(
        "ix_model_suggestions_post_id",
        "model_suggestions",
        ["post_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # 3. Index on human_corrections.post_id
    # ------------------------------------------------------------------
    op.create_index(
        "ix_human_corrections_post_id",
        "human_corrections",
        ["post_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_human_corrections_post_id", table_name="human_corrections")
    op.drop_index("ix_model_suggestions_post_id", table_name="model_suggestions")
    op.drop_constraint(
        "uq_human_corrections_suggestion_id",
        "human_corrections",
        type_="unique",
    )
