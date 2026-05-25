"""rename_provider_user_id_to_athlete_id

Revision ID: c3a2156c4d0f
Revises: bb7b4d03c40d
Create Date: 2026-05-26 04:07:48.149832

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3a2156c4d0f'
down_revision: Union[str, None] = 'bb7b4d03c40d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename provider_user_id column to athlete_id in fitness_tracker_connections table"""
    op.alter_column(
        'fitness_tracker_connections',
        'provider_user_id',
        new_column_name='athlete_id'
    )


def downgrade() -> None:
    """Rollback: Rename athlete_id back to provider_user_id"""
    op.alter_column(
        'fitness_tracker_connections',
        'athlete_id',
        new_column_name='provider_user_id'
    )
