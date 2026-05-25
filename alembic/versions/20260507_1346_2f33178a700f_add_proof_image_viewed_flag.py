"""add_proof_image_viewed_flag

Revision ID: 2f33178a700f
Revises: 11835e0ff1de
Create Date: 2026-05-07 13:46:32.183975

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2f33178a700f'
down_revision: str | None = '11835e0ff1de'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add proof_image_viewed_by_admin boolean column to activity_progress table
    # Defaults to True for existing records (so old proofs don't show as new)
    # New uploads will explicitly set this to False
    op.add_column('activity_progress',
                  sa.Column('proof_image_viewed_by_admin', sa.Boolean(),
                           nullable=False, server_default=sa.true()))


def downgrade() -> None:
    # Remove proof_image_viewed_by_admin column
    op.drop_column('activity_progress', 'proof_image_viewed_by_admin')
