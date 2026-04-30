"""add_uses_tier_system_to_events

Revision ID: b75d5dbdb278
Revises: 3451509c9ce5
Create Date: 2026-04-30 11:25:40.125404

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b75d5dbdb278'
down_revision: Union[str, None] = '3451509c9ce5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add uses_tier_system column to events table
    op.add_column('events', sa.Column('uses_tier_system', sa.Boolean(), nullable=True))

    # Set default value to True for all existing events
    op.execute("UPDATE events SET uses_tier_system = TRUE")

    # Make the column non-nullable
    op.alter_column('events', 'uses_tier_system', nullable=False, server_default=sa.text('TRUE'))


def downgrade() -> None:
    # Remove uses_tier_system column from events table
    op.drop_column('events', 'uses_tier_system')
