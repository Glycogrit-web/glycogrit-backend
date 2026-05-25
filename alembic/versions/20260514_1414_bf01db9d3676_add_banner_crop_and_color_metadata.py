"""add_banner_crop_and_color_metadata

Revision ID: bf01db9d3676
Revises: b81347af92a6
Create Date: 2026-05-14 14:14:24.377805

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bf01db9d3676'
down_revision: str | None = 'b81347af92a6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add JSONB column to store banner image crop metadata
    # Example: {"x": 0, "y": 0, "width": 100, "height": 100, "zoom": 1, "rotation": 0}
    op.add_column('events', sa.Column('banner_crop_data', sa.dialects.postgresql.JSONB, nullable=True))

    # Add column to store dominant color extracted from banner image
    # Example: "#FF5733" or "rgb(255, 87, 51)"
    op.add_column('events', sa.Column('banner_dominant_color', sa.String(length=50), nullable=True))

    # Add column to store secondary/accent color from banner image
    op.add_column('events', sa.Column('banner_accent_color', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('events', 'banner_accent_color')
    op.drop_column('events', 'banner_dominant_color')
    op.drop_column('events', 'banner_crop_data')
