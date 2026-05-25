"""add payment tracking fields to registrations

Revision ID: 20260429_1700
Revises: 20260429_0420
Create Date: 2026-04-29 17:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_payment_tracking'
down_revision = 'add_proof_image_url'
branch_labels = None
depends_on = None


def upgrade():
    """Add payment tracking fields to registrations table"""

    # Add total_amount_paid - sum of all successful payments
    op.add_column('registrations',
        sa.Column('total_amount_paid', sa.Numeric(10, 2), nullable=False, server_default='0.00')
    )

    # Add successful_payments_count - number of successful payment transactions
    op.add_column('registrations',
        sa.Column('successful_payments_count', sa.Integer, nullable=False, server_default='0')
    )

    # Add last_payment_status - status of most recent payment attempt
    # Values: null (no payment attempted), 'pending', 'success', 'failed', 'refunded'
    op.add_column('registrations',
        sa.Column('last_payment_status', sa.String(20), nullable=True)
    )

    # Add last_payment_amount - amount of most recent payment attempt
    op.add_column('registrations',
        sa.Column('last_payment_amount', sa.Numeric(10, 2), nullable=True)
    )

    # Add last_payment_date - timestamp of most recent payment attempt
    op.add_column('registrations',
        sa.Column('last_payment_date', sa.TIMESTAMP(timezone=True), nullable=True)
    )

    # Create index for querying by payment status
    op.create_index(
        'ix_registrations_last_payment_status',
        'registrations',
        ['last_payment_status']
    )


def downgrade():
    """Remove payment tracking fields from registrations table"""

    # Drop index
    op.drop_index('ix_registrations_last_payment_status', table_name='registrations')

    # Drop columns
    op.drop_column('registrations', 'last_payment_date')
    op.drop_column('registrations', 'last_payment_amount')
    op.drop_column('registrations', 'last_payment_status')
    op.drop_column('registrations', 'successful_payments_count')
    op.drop_column('registrations', 'total_amount_paid')
