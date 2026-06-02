"""add_champion_gallery_urls

Revision ID: 20260602_champion_gallery
Revises: 20260529_perf_idx
Create Date: 2026-06-02 00:00:00.000000

This migration adds champion_gallery_urls column to store admin-provided photo URLs
for the "Real Champions" section on event pages.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20260602_champion_gallery'
down_revision: Union[str, None] = '20260529_perf_idx'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add champion_gallery_urls column to events table"""
    op.add_column('events',
        sa.Column('champion_gallery_urls',
                  postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True))


def downgrade() -> None:
    """Remove champion_gallery_urls column from events table"""
    op.drop_column('events', 'champion_gallery_urls')
