"""add_sync_metadata_tracking

Revision ID: add_sync_metadata
Revises: 20260429_cleanup_fields
Create Date: 2026-04-29 03:59:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_sync_metadata'
down_revision = '20260429_cleanup_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add sync metadata tracking fields to user_challenge_progress
    op.add_column('user_challenge_progress',
        sa.Column('last_sync_source', sa.String(length=50), nullable=True,
                 comment='Source of last sync: strava, apple_health, google_fit, admin_manual'))

    op.add_column('user_challenge_progress',
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True,
                 comment='Timestamp of last sync'))

    op.add_column('user_challenge_progress',
        sa.Column('last_synced_by_user_id', sa.Integer(), nullable=True,
                 comment='User ID who performed the sync (for admin manual updates)'))

    # Add foreign key constraint for last_synced_by_user_id
    op.create_foreign_key(
        'fk_user_challenge_progress_last_synced_by_user',
        'user_challenge_progress', 'users',
        ['last_synced_by_user_id'], ['id']
    )


def downgrade():
    # Drop foreign key constraint
    op.drop_constraint('fk_user_challenge_progress_last_synced_by_user',
                      'user_challenge_progress', type_='foreignkey')

    # Drop columns
    op.drop_column('user_challenge_progress', 'last_synced_by_user_id')
    op.drop_column('user_challenge_progress', 'last_sync_at')
    op.drop_column('user_challenge_progress', 'last_sync_source')
