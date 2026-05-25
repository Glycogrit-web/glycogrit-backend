"""drop_backup_and_legacy_tables

Phase 1 of database cleanup: Remove backup tables and empty legacy tables
- Drops event_registration_tiers_backup (11 rows - old backup)
- Drops events_backup (26 rows - old backup)
- Drops challenge_activities (0 rows - replaced by user_activity_logs)

These tables have no code dependencies and are safe to remove.

Revision ID: d0aec29d0c00
Revises: 20260510_add_wahoo_integration
Create Date: 2026-05-11 03:24:13.429295

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd0aec29d0c00'
down_revision: str | None = '20260510_add_wahoo_integration'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop backup tables (no code dependencies)
    op.execute("DROP TABLE IF EXISTS event_registration_tiers_backup CASCADE")
    op.execute("DROP TABLE IF EXISTS events_backup CASCADE")

    # Drop legacy challenge_activities table (replaced by user_activity_logs)
    op.execute("DROP TABLE IF EXISTS challenge_activities CASCADE")


def downgrade() -> None:
    # Note: Cannot restore data, only table structure
    # If needed, restore from database backup

    # Recreate challenge_activities table structure
    op.create_table(
        'challenge_activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('challenge_id', sa.Integer(), nullable=False),
        sa.Column('strava_activity_id', sa.BigInteger(), nullable=True),
        sa.Column('strava_connection_id', sa.Integer(), nullable=True),
        sa.Column('activity_type', sa.String(length=50), nullable=False),
        sa.Column('distance_meters', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('elevation_gain_meters', sa.Integer(), nullable=True),
        sa.Column('activity_date', sa.DateTime(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Note: Backup tables cannot be recreated without original data
    # event_registration_tiers_backup and events_backup must be restored from backup
