"""add_was_fallback_to_model_suggestions

Revision ID: e2654160a1a8
Revises: fbdce510ef7e
Create Date: 2026-07-28 14:05:25.144250

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2654160a1a8'
down_revision: Union[str, None] = 'fbdce510ef7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'model_suggestions',
        sa.Column('was_fallback', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )


def downgrade() -> None:
    op.drop_column('model_suggestions', 'was_fallback')

