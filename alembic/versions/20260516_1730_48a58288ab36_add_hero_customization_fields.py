"""add_hero_customization_fields

Revision ID: 48a58288ab36
Revises: 691b93cc90b3
Create Date: 2026-05-16 17:30:52.335176

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '48a58288ab36'
down_revision: str | None = '691b93cc90b3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add hero customization fields to events table
    op.add_column('events', sa.Column('hero_title', sa.String(length=200), nullable=True))
    op.add_column('events', sa.Column('hero_subtitle', sa.String(length=200), nullable=True))
    op.add_column('events', sa.Column('hero_tagline', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('medal_image_url', sa.String(length=500), nullable=True))
    op.add_column('events', sa.Column('hero_background_pattern', sa.String(length=50), nullable=True))


def downgrade() -> None:
    # Remove hero customization fields from events table
    op.drop_column('events', 'hero_background_pattern')
    op.drop_column('events', 'medal_image_url')
    op.drop_column('events', 'hero_tagline')
    op.drop_column('events', 'hero_subtitle')
    op.drop_column('events', 'hero_title')
