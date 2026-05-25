"""rename_provider_data_to_athlete_data

Revision ID: be1342ef7505
Revises: 966c44cafe8e
Create Date: 2026-05-26 04:20:24.180697

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'be1342ef7505'
down_revision: str | None = '966c44cafe8e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename provider_data column to athlete_data in fitness_tracker_connections table"""
    op.alter_column(
        'fitness_tracker_connections',
        'provider_data',
        new_column_name='athlete_data'
    )


def downgrade() -> None:
    """Rollback: Rename athlete_data back to provider_data"""
    op.alter_column(
        'fitness_tracker_connections',
        'athlete_data',
        new_column_name='provider_data'
    )
