"""add distance and activity type to external certificates

Revision ID: 20260607_cert_distance_sport
Revises: 20260606_external_cert
Create Date: 2026-06-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260607_cert_distance_sport'
down_revision = '20260606_external_cert'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add distance and activity_type fields to external certificates
    for enhanced certificate data from CSV import
    """
    # Add external_certificate_distance column
    op.add_column('registrations',
        sa.Column('external_certificate_distance', sa.Numeric(precision=10, scale=2), nullable=True)
    )

    # Add external_certificate_activity_type column
    op.add_column('registrations',
        sa.Column('external_certificate_activity_type', sa.String(length=50), nullable=True)
    )

    # Add index for activity_type to support filtering/grouping by sport
    op.create_index(
        'idx_registrations_external_cert_activity_type',
        'registrations',
        ['external_certificate_activity_type']
    )


def downgrade():
    """
    Remove distance and activity_type fields from external certificates
    """
    # Drop index
    op.drop_index('idx_registrations_external_cert_activity_type', table_name='registrations')

    # Drop columns
    op.drop_column('registrations', 'external_certificate_activity_type')
    op.drop_column('registrations', 'external_certificate_distance')
