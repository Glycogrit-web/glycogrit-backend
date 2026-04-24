"""add_challenge_tracking_enhancements

Revision ID: b096bd29fb22
Revises: a1b2c3d4e5f6
Create Date: 2026-04-24 04:13:13.416271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'b096bd29fb22'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new fitness tracker connections table (for non-Strava sources)
    op.create_table(
        'fitness_tracker_connections',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('provider', sa.String(50), nullable=False, index=True),  # google_fit, apple_health, nike_run_club
        sa.Column('provider_user_id', sa.String(255), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scope', sa.String(500), nullable=True),
        sa.Column('provider_data', sa.Text(), nullable=True),  # JSON string with provider-specific data
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
    )
    op.create_index('idx_fitness_tracker_user_provider', 'fitness_tracker_connections', ['user_id', 'provider'], unique=True)

    # Enhance challenge_activities to support multiple sources
    op.add_column('challenge_activities', sa.Column('source_provider', sa.String(50), nullable=True))  # strava, google_fit, etc
    op.add_column('challenge_activities', sa.Column('external_activity_id', sa.String(255), nullable=True))
    op.create_index('idx_challenge_activity_external', 'challenge_activities', ['source_provider', 'external_activity_id'])

    # Add completion tracking to user_challenge_progress
    op.add_column('user_challenge_progress', sa.Column('completion_status', sa.String(50), nullable=True))  # failed, completed, exceeded, outstanding
    op.add_column('user_challenge_progress', sa.Column('completion_percentage', sa.Integer(), default=0))
    op.add_column('user_challenge_progress', sa.Column('evaluation_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user_challenge_progress', sa.Column('badge_earned', sa.String(100), nullable=True))

    # Add challenge lifecycle tracking to events table
    op.add_column('events', sa.Column('auto_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('events', sa.Column('auto_completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('events', sa.Column('sync_enabled', sa.Boolean(), default=True))  # Enable/disable auto-sync
    op.add_column('events', sa.Column('completion_criteria', JSONB, nullable=True))  # {"min_distance": 100, "min_activities": 10}


def downgrade() -> None:
    # Remove columns from events
    op.drop_column('events', 'completion_criteria')
    op.drop_column('events', 'sync_enabled')
    op.drop_column('events', 'auto_completed_at')
    op.drop_column('events', 'auto_started_at')

    # Remove columns from user_challenge_progress
    op.drop_column('user_challenge_progress', 'badge_earned')
    op.drop_column('user_challenge_progress', 'evaluation_date')
    op.drop_column('user_challenge_progress', 'completion_percentage')
    op.drop_column('user_challenge_progress', 'completion_status')

    # Remove columns from challenge_activities
    op.drop_index('idx_challenge_activity_external', 'challenge_activities')
    op.drop_column('challenge_activities', 'external_activity_id')
    op.drop_column('challenge_activities', 'source_provider')

    # Drop fitness_tracker_connections table
    op.drop_index('idx_fitness_tracker_user_provider', 'fitness_tracker_connections')
    op.drop_table('fitness_tracker_connections')
