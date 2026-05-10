"""Remove challenge_activities table - use only ActivityProgress

Revision ID: 20260510_remove_challenge_activities
Revises: 20260510_add_primary_sync_source
Create Date: 2026-05-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260510_remove_challenge_activities'
down_revision = '20260510_primary_sync'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Drop challenge_activities table.

    We're removing this table because:
    1. Individual activity records create database bloat
    2. We only need aggregated progress in ActivityProgress
    3. ActivityProgress already tracks all necessary metadata:
       - distance_completed (highest value)
       - sync_source, last_sync_at (when/where updated)
       - distance_by_source (JSONB - each source's contribution)
       - total_activities, total_duration_minutes (stats)
    """
    # Drop the challenge_activities table
    op.drop_table('challenge_activities')


def downgrade() -> None:
    """Recreate challenge_activities table if needed"""
    op.create_table(
        'challenge_activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('challenge_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('strava_connection_id', sa.Integer(), nullable=True),
        sa.Column('source_provider', sa.String(50), nullable=True),
        sa.Column('external_activity_id', sa.String(255), nullable=True),
        sa.Column('strava_activity_id', sa.BigInteger(), nullable=True),
        sa.Column('activity_type', sa.String(50), nullable=False),
        sa.Column('activity_name', sa.String(500), nullable=True),
        sa.Column('distance_meters', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('elevation_gain_meters', sa.Integer(), nullable=True),
        sa.Column('average_speed', sa.Integer(), nullable=True),
        sa.Column('max_speed', sa.Integer(), nullable=True),
        sa.Column('activity_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['challenge_id'], ['events.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['strava_connection_id'], ['strava_connections.id'], ),
    )
    op.create_index('ix_challenge_activities_activity_date', 'challenge_activities', ['activity_date'])
    op.create_index('ix_challenge_activities_strava_activity_id', 'challenge_activities', ['strava_activity_id'], unique=True)
