"""add primary sync source to users

Revision ID: 20260510_primary_sync
Revises: 20260508_0210_e9670aec43c7
Create Date: 2026-05-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260510_primary_sync'
down_revision = '20260508_0210_e9670aec43c7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add primary_sync_source column to users table"""
    # Add column to users table
    op.add_column('users', sa.Column('primary_sync_source', sa.String(50), nullable=True))

    # Set default value to 'strava' for users who have active Strava connection
    op.execute("""
        UPDATE users
        SET primary_sync_source = 'strava'
        WHERE id IN (
            SELECT user_id FROM strava_connection WHERE is_active = TRUE
        )
    """)

    # Set default value to 'google_fit' for users who have active Google Fit connection but no Strava
    op.execute("""
        UPDATE users
        SET primary_sync_source = 'google_fit'
        WHERE id IN (
            SELECT user_id FROM fitness_tracker_connections
            WHERE provider = 'google_fit' AND is_active = TRUE
        )
        AND primary_sync_source IS NULL
    """)


def downgrade() -> None:
    """Remove primary_sync_source column from users table"""
    op.drop_column('users', 'primary_sync_source')
