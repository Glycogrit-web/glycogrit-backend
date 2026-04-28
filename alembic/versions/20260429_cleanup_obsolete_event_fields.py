"""cleanup obsolete event fields

Revision ID: 20260429_cleanup_fields
Revises: 34131f88348c
Create Date: 2026-04-29

This migration removes obsolete fields from the events table that are no longer
needed after the tier system implementation and Strava integration removal.

Fields being removed:
- start_date, end_date: Replaced by event_date and event_end_date (TIMESTAMP)
- certificate_type: Now handled by tier rewards
- requires_payment: Now handled at tier level
- registration_fee: Replaced by tier-level pricing
- rewards: Moved to tier rewards
- goodies: Now managed in separate user_goodies table
- uses_tier_system: ALL events now use tiers (no longer optional)
- auto_started_at, auto_completed_at: Strava auto-tracking not implemented
- sync_enabled: Strava auto-sync not implemented
- completion_criteria: Not being used

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260429_cleanup_fields'
down_revision = '34131f88348c'
branch_labels = None
depends_on = None


def upgrade():
    # Drop obsolete date fields (replaced by event_date/event_end_date TIMESTAMP fields)
    op.drop_column('events', 'start_date')
    op.drop_column('events', 'end_date')

    # Drop obsolete payment/pricing fields (now handled by tiers)
    op.drop_column('events', 'certificate_type')
    op.drop_column('events', 'requires_payment')
    op.drop_column('events', 'registration_fee')

    # Drop obsolete reward/goodie fields (now handled by tier system)
    op.drop_column('events', 'rewards')
    op.drop_column('events', 'goodies')

    # Drop obsolete tier system flag (all events use tiers now)
    op.drop_column('events', 'uses_tier_system')

    # Drop Strava auto-tracking fields (not implemented)
    op.drop_column('events', 'auto_started_at')
    op.drop_column('events', 'auto_completed_at')
    op.drop_column('events', 'sync_enabled')
    op.drop_column('events', 'completion_criteria')


def downgrade():
    # Recreate all dropped columns in reverse order

    # Strava auto-tracking fields
    op.add_column('events', sa.Column('completion_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('events', sa.Column('sync_enabled', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('events', sa.Column('auto_completed_at', sa.DateTime(), nullable=True))
    op.add_column('events', sa.Column('auto_started_at', sa.DateTime(), nullable=True))

    # Tier system flag
    op.add_column('events', sa.Column('uses_tier_system', sa.Boolean(), server_default='false', nullable=False))

    # Reward/goodie fields
    op.add_column('events', sa.Column('goodies', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('events', sa.Column('rewards', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Payment/pricing fields
    op.add_column('events', sa.Column('registration_fee', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('events', sa.Column('requires_payment', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('events', sa.Column('certificate_type', sa.String(length=20), nullable=True))

    # Date fields
    op.add_column('events', sa.Column('end_date', sa.Date(), nullable=True))
    op.add_column('events', sa.Column('start_date', sa.Date(), nullable=True))

    # Recreate indexes if they existed
    op.create_index('ix_events_end_date', 'events', ['end_date'], unique=False)
    op.create_index('ix_events_start_date', 'events', ['start_date'], unique=False)
