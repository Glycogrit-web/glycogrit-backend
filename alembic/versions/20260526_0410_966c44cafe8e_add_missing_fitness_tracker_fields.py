"""add_missing_fitness_tracker_fields

Revision ID: 966c44cafe8e
Revises: c3a2156c4d0f
Create Date: 2026-05-26 04:10:42.559375

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '966c44cafe8e'
down_revision: str | None = 'c3a2156c4d0f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add missing fields to fitness_tracker_connections table"""
    # Add sync and error tracking fields
    op.add_column('fitness_tracker_connections', sa.Column('sync_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('fitness_tracker_connections', sa.Column('last_error', sa.Text(), nullable=True))
    op.add_column('fitness_tracker_connections', sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('fitness_tracker_connections', sa.Column('webhook_subscription_id', sa.String(255), nullable=True))


def downgrade() -> None:
    """Remove the added fields"""
    op.drop_column('fitness_tracker_connections', 'webhook_subscription_id')
    op.drop_column('fitness_tracker_connections', 'error_count')
    op.drop_column('fitness_tracker_connections', 'last_error')
    op.drop_column('fitness_tracker_connections', 'sync_enabled')
