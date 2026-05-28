"""Add unique constraint for user_event_tier to allow multiple registrations

Revision ID: 20260528_multi_reg
Revises: f20292e84906
Create Date: 2026-05-28 15:00:00

This migration enables users to have multiple registrations per event (one per tier).
- Adds UNIQUE constraint on (user_id, event_id, current_tier_id)
- Adds performance index on (user_id, event_id)
- Prevents duplicate registrations for the same tier
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260528_multi_reg'
down_revision = 'f20292e84906'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add unique constraint to prevent duplicate tier registrations.

    IMPORTANT: Before running this migration, verify no duplicate
    (user_id, event_id, current_tier_id) combinations exist:

    SELECT user_id, event_id, current_tier_id, COUNT(*)
    FROM registrations
    WHERE current_tier_id IS NOT NULL
    GROUP BY user_id, event_id, current_tier_id
    HAVING COUNT(*) > 1;
    """
    # Add UNIQUE constraint on (user_id, event_id, current_tier_id)
    # This prevents duplicate registrations for the same tier
    op.create_unique_constraint(
        'uq_registration_user_event_tier',
        'registrations',
        ['user_id', 'event_id', 'current_tier_id']
    )

    # Add index for performance on (user_id, event_id) queries
    # This improves query performance when fetching all user registrations for an event
    op.create_index(
        'idx_registrations_user_event',
        'registrations',
        ['user_id', 'event_id'],
        unique=False
    )


def downgrade():
    """Remove the unique constraint and index."""
    op.drop_index('idx_registrations_user_event', table_name='registrations')
    op.drop_constraint('uq_registration_user_event_tier', 'registrations', type_='unique')
