"""make_progress_percentage_and_is_completed_computed

Revision ID: 0d45922d16b5
Revises: e9f4a2b1c5d3
Create Date: 2026-04-30 14:43:40.784736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d45922d16b5'
down_revision: Union[str, None] = 'e9f4a2b1c5d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Drop progress_percentage and is_completed columns from activity_progress.
    These are now computed properties based on distance_completed and target_distance.
    """
    # Drop computed columns
    op.drop_column('activity_progress', 'progress_percentage')
    op.drop_column('activity_progress', 'is_completed')


def downgrade() -> None:
    """
    Restore progress_percentage and is_completed as stored columns.
    """
    # Re-add the columns
    op.add_column('activity_progress',
                  sa.Column('progress_percentage', sa.Numeric(precision=5, scale=2),
                           nullable=False, server_default='0.00'))
    op.add_column('activity_progress',
                  sa.Column('is_completed', sa.Boolean(),
                           nullable=False, server_default='false'))

    # Backfill values based on distance_completed and target_distance
    from sqlalchemy import text
    op.execute(text("""
        UPDATE activity_progress
        SET progress_percentage = CASE
            WHEN target_distance > 0 THEN
                LEAST((distance_completed / target_distance * 100), 100)
            ELSE 0
        END,
        is_completed = (distance_completed >= target_distance)
    """))
