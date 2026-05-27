"""remove_redundant_columns_from_event_activities

Revision ID: 22f99d04baf4
Revises: be1342ef7505
Create Date: 2026-05-28 02:46:08.770355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22f99d04baf4'
down_revision: Union[str, None] = 'be1342ef7505'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove redundant columns from event_activities table:
    - max_participants (capacity now handled by event_registration_tiers)
    - current_participants (capacity now handled by event_registration_tiers)
    - registration_fee (pricing now handled by event_registration_tiers)

    These columns made activities event-specific, but with the tier system,
    these concerns are handled at the tier level, allowing activities to be
    reusable templates.
    """
    # Drop columns from event_activities
    op.drop_column('event_activities', 'max_participants')
    op.drop_column('event_activities', 'current_participants')
    op.drop_column('event_activities', 'registration_fee')


def downgrade() -> None:
    """Restore the removed columns"""
    # Add back columns to event_activities
    op.add_column('event_activities',
        sa.Column('registration_fee', sa.Numeric(precision=10, scale=2), nullable=True)
    )
    op.add_column('event_activities',
        sa.Column('current_participants', sa.Integer(), nullable=True, server_default='0')
    )
    op.add_column('event_activities',
        sa.Column('max_participants', sa.Integer(), nullable=True)
    )
