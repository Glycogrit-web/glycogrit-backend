"""add_performance_indexes

Revision ID: 20260529_perf_idx
Revises: 20260528_1500_add_unique_user_event_tier
Create Date: 2026-05-29 12:00:00.000000

This migration adds critical performance indexes to improve query execution times.
Expected impact: 50-70% faster query execution for filtered queries.

Indexes added:
- registrations (event_id, payment_successful) - for confirmed registrations queries
- registrations (status, event_id) - for event registration lists
- activity_progress (user_id, event_id) - for user progress lookups
- events (is_featured, event_date) - for featured events list
- payments (status, user_id) - for user payment history
- registrations (confirmed_at) - for date-based queries
- fitness_trackers (user_id, provider) - for tracker lookups
- user_rewards (user_id, registration_id) - for rewards queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260529_perf_idx'
down_revision: Union[str, None] = '20260528_multi_reg'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes"""

    # Index for confirmed registrations queries (most common filter)
    # Partial index to save space since we only query confirmed registrations
    op.create_index(
        'idx_registrations_payment_successful_event',
        'registrations',
        ['event_id', 'payment_successful'],
        unique=False,
        postgresql_where=sa.text('payment_successful = TRUE')
    )

    # Composite index for registration status queries per event
    op.create_index(
        'idx_registrations_status_event',
        'registrations',
        ['status', 'event_id'],
        unique=False
    )

    # Index for user activity progress lookups (very common in dashboard)
    op.create_index(
        'idx_activity_progress_user_event',
        'activity_progress',
        ['user_id', 'event_id'],
        unique=False
    )

    # Partial index for featured events (homepage query)
    op.create_index(
        'idx_events_featured_date',
        'events',
        ['is_featured', 'event_date'],
        unique=False,
        postgresql_where=sa.text('is_featured = TRUE')
    )

    # Index for user payment history queries
    op.create_index(
        'idx_payments_status_user',
        'payments',
        ['status', 'user_id'],
        unique=False
    )

    # Partial index for confirmed registration date queries
    op.create_index(
        'idx_registrations_confirmed_at',
        'registrations',
        ['confirmed_at'],
        unique=False,
        postgresql_where=sa.text('confirmed_at IS NOT NULL')
    )

    # Index for fitness tracker provider lookups
    op.create_index(
        'idx_fitness_trackers_user_provider',
        'fitness_trackers',
        ['user_id', 'provider'],
        unique=False
    )

    # Index for user rewards lookups
    op.create_index(
        'idx_user_rewards_user_registration',
        'user_rewards',
        ['user_id', 'registration_id'],
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes"""

    op.drop_index('idx_user_rewards_user_registration', table_name='user_rewards')
    op.drop_index('idx_fitness_trackers_user_provider', table_name='fitness_trackers')
    op.drop_index('idx_registrations_confirmed_at', table_name='registrations')
    op.drop_index('idx_payments_status_user', table_name='payments')
    op.drop_index('idx_events_featured_date', table_name='events')
    op.drop_index('idx_activity_progress_user_event', table_name='activity_progress')
    op.drop_index('idx_registrations_status_event', table_name='registrations')
    op.drop_index('idx_registrations_payment_successful_event', table_name='registrations')
