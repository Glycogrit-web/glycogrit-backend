"""add_event_end_date_and_activity_progress

Revision ID: 23c59d68f2e7
Revises: 20260427_multi_tier
Create Date: 2026-04-27 19:47:26.026547

Changes:
1. Add event_end_date to events table
2. Create activity_progress table for tracking user activity completion
3. Make event-level pricing fields nullable (moved to tiers)
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '23c59d68f2e7'
down_revision: str | None = '20260427_multi_tier'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add event_end_date to events table
    op.add_column('events', sa.Column('event_end_date', sa.TIMESTAMP(), nullable=True))

    # 2. Create activity_progress table for tracking user activity completion
    op.create_table(
        'activity_progress',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('registration_id', sa.Integer(), sa.ForeignKey('registrations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('event_categories.id', ondelete='CASCADE'), nullable=False, index=True),

        # Progress tracking
        sa.Column('distance_completed', sa.Numeric(10, 2), nullable=False, default=0.00),
        sa.Column('target_distance', sa.Numeric(10, 2), nullable=False),
        sa.Column('progress_percentage', sa.Numeric(5, 2), nullable=False, default=0.00),
        sa.Column('is_completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),

        # Manual entry support
        sa.Column('last_manual_entry', sa.Numeric(10, 2), nullable=True),
        sa.Column('last_manual_entry_at', sa.TIMESTAMP(), nullable=True),

        # 3rd party sync (Strava, etc.)
        sa.Column('last_sync_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('sync_source', sa.String(50), nullable=True),  # 'manual', 'strava', 'garmin', etc.

        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.UniqueConstraint('registration_id', name='uq_activity_progress_registration')
    )

    # 3. Make event-level pricing fields nullable (now tier-specific)
    # These fields remain for backward compatibility but are optional when uses_tier_system=True
    op.alter_column('events', 'registration_fee', nullable=True, existing_type=sa.Numeric(10, 2))
    op.alter_column('events', 'certificate_type', nullable=True, existing_type=sa.String(50))


def downgrade() -> None:
    # Reverse changes
    op.drop_table('activity_progress')
    op.drop_column('events', 'event_end_date')

    # Revert nullable constraints (if needed)
    op.alter_column('events', 'registration_fee', nullable=False, existing_type=sa.Numeric(10, 2))
    op.alter_column('events', 'certificate_type', nullable=False, existing_type=sa.String(50))
