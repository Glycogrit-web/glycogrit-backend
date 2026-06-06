"""add external certificate fields to registrations

Revision ID: 20260606_external_cert
Revises: 20260602_champion_gallery
Create Date: 2026-06-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260606_external_cert'
down_revision = '20260602_champion_gallery'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add external certificate fields to registrations table
    for bulk certificate distribution via Google Drive
    """
    # Add new columns
    op.add_column('registrations',
        sa.Column('external_certificate_url', sa.Text(), nullable=True)
    )
    op.add_column('registrations',
        sa.Column('external_certificate_unlocked', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('registrations',
        sa.Column('external_certificate_uploaded_at', sa.TIMESTAMP(), nullable=True)
    )
    op.add_column('registrations',
        sa.Column('external_certificate_uploaded_by', sa.Integer(), nullable=True)
    )

    # Add foreign key constraint for admin who uploaded
    op.create_foreign_key(
        'fk_registrations_external_cert_uploaded_by',
        'registrations', 'users',
        ['external_certificate_uploaded_by'], ['id'],
        ondelete='SET NULL'
    )

    # Add index for faster lookups of unlocked certificates
    op.create_index(
        'idx_registrations_external_cert_unlocked',
        'registrations',
        ['external_certificate_unlocked']
    )

    # Add composite index for event + unlocked status queries
    op.create_index(
        'idx_registrations_event_external_cert',
        'registrations',
        ['event_id', 'external_certificate_unlocked']
    )


def downgrade():
    """
    Remove external certificate fields
    """
    # Drop indexes
    op.drop_index('idx_registrations_event_external_cert', table_name='registrations')
    op.drop_index('idx_registrations_external_cert_unlocked', table_name='registrations')

    # Drop foreign key
    op.drop_constraint('fk_registrations_external_cert_uploaded_by', 'registrations', type_='foreignkey')

    # Drop columns
    op.drop_column('registrations', 'external_certificate_uploaded_by')
    op.drop_column('registrations', 'external_certificate_uploaded_at')
    op.drop_column('registrations', 'external_certificate_unlocked')
    op.drop_column('registrations', 'external_certificate_url')
