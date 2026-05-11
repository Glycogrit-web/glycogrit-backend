"""remove_redundant_activity_progress_columns

Phase 2 of database cleanup: Remove redundant columns from activity_progress

Removes:
- total_activities: Now computed from distance_by_source[highest_distance_source].activity_count
- total_duration_minutes: Now computed from distance_by_source[highest_distance_source].total_duration_minutes

These fields are redundant because the same data is already stored in the
distance_by_source JSONB column with per-source granularity.

The ActivityProgress model now has get_total_activities() and
get_total_duration_minutes() methods that extract this data from distance_by_source.

Revision ID: e3fc025475e9
Revises: d0aec29d0c00
Create Date: 2026-05-11 03:36:17.351113

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3fc025475e9'
down_revision: Union[str, None] = 'd0aec29d0c00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop redundant columns from activity_progress table
    op.drop_column('activity_progress', 'total_activities')
    op.drop_column('activity_progress', 'total_duration_minutes')


def downgrade() -> None:
    # Restore columns (data will be lost, must be recalculated)
    op.add_column('activity_progress',
        sa.Column('total_activities', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('activity_progress',
        sa.Column('total_duration_minutes', sa.Integer(), nullable=False, server_default='0'))
