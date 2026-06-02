"""add_certificate_template_fields

Revision ID: 20260602_cert_template
Revises: 20260602_champion_gallery
Create Date: 2026-06-02 12:00:00.000000

This migration adds certificate template support to events table:
- certificate_template_url: URL to template image in R2
- certificate_template_config: JSON config with OCR-detected tag positions
- uses_custom_template: Flag to enable template-based generation
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20260602_cert_template'
down_revision: Union[str, None] = '20260602_champion_gallery'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add certificate template fields to events table"""
    # Add certificate_template_url column
    op.add_column('events',
        sa.Column('certificate_template_url',
                  sa.String(500),
                  nullable=True))

    # Add certificate_template_config column (JSONB for tag positions)
    op.add_column('events',
        sa.Column('certificate_template_config',
                  postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True))

    # Add uses_custom_template flag
    op.add_column('events',
        sa.Column('uses_custom_template',
                  sa.Boolean(),
                  nullable=False,
                  server_default='false'))


def downgrade() -> None:
    """Remove certificate template fields from events table"""
    op.drop_column('events', 'uses_custom_template')
    op.drop_column('events', 'certificate_template_config')
    op.drop_column('events', 'certificate_template_url')
