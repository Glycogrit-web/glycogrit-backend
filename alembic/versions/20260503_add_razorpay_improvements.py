"""Add Razorpay improvements - payment capture, links, settlements

Revision ID: 20260503_razorpay
Revises: 20260419_1418_36343d051da4
Create Date: 2026-05-03

This migration adds:
1. New payment statuses (AUTHORIZED, VOIDED)
2. Payment links table
3. Settlements tables
4. Refund speed tracking fields
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260503_razorpay'
down_revision = '764f6e5cb521'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration"""

    # 1. Skip enum modification - database uses VARCHAR for status
    # New statuses (authorized, voided) can be stored in existing VARCHAR(50) column
    # No schema changes needed for status field

    # 2. Create payment_links table
    op.create_table(
        'payment_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('registration_id', sa.Integer(), nullable=True),
        sa.Column('razorpay_link_id', sa.String(255), nullable=False),
        sa.Column('short_url', sa.Text(), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('reference_id', sa.String(255), nullable=True),
        sa.Column('customer_name', sa.String(255), nullable=True),
        sa.Column('customer_email', sa.String(255), nullable=True),
        sa.Column('customer_contact', sa.String(20), nullable=True),
        sa.Column('callback_url', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['registration_id'], ['registrations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('razorpay_link_id')
    )
    op.create_index('ix_payment_links_user_id', 'payment_links', ['user_id'])
    op.create_index('ix_payment_links_status', 'payment_links', ['status'])
    op.create_index('ix_payment_links_reference_id', 'payment_links', ['reference_id'])

    # 3. Create settlements table
    op.create_table(
        'settlements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('razorpay_settlement_id', sa.String(255), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('fees', sa.Numeric(10, 2), nullable=True),
        sa.Column('tax', sa.Numeric(10, 2), nullable=True),
        sa.Column('utr', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('settled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('razorpay_settlement_id')
    )
    op.create_index('ix_settlements_status', 'settlements', ['status'])
    op.create_index('ix_settlements_settled_at', 'settlements', ['settled_at'])
    op.create_index('ix_settlements_utr', 'settlements', ['utr'])

    # 4. Create payment_settlements junction table
    op.create_table(
        'payment_settlements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=False),
        sa.Column('settlement_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['settlement_id'], ['settlements.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('payment_id', 'settlement_id', name='uq_payment_settlement')
    )
    op.create_index('ix_payment_settlements_payment_id', 'payment_settlements', ['payment_id'])
    op.create_index('ix_payment_settlements_settlement_id', 'payment_settlements', ['settlement_id'])

    # 5. Add refund speed tracking columns to payments table
    op.add_column('payments', sa.Column('refund_speed', sa.String(20), nullable=True))
    op.add_column('payments', sa.Column('refund_speed_processed', sa.String(20), nullable=True))

    # 6. Add payment capture related columns
    op.add_column('payments', sa.Column('authorized_at', sa.DateTime(), nullable=True))
    op.add_column('payments', sa.Column('captured_at', sa.DateTime(), nullable=True))
    op.add_column('payments', sa.Column('voided_at', sa.DateTime(), nullable=True))
    op.add_column('payments', sa.Column('auto_capture', sa.Boolean(), nullable=False, server_default='true'))

    # 7. Create webhook_events table for better webhook handling
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(255), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_retry_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )
    op.create_index('ix_webhook_events_event_type', 'webhook_events', ['event_type'])
    op.create_index('ix_webhook_events_status', 'webhook_events', ['status'])
    op.create_index('ix_webhook_events_created_at', 'webhook_events', ['created_at'])


def downgrade() -> None:
    """Revert migration"""

    # Drop tables in reverse order
    op.drop_table('webhook_events')
    op.drop_table('payment_settlements')
    op.drop_table('settlements')
    op.drop_table('payment_links')

    # Remove columns from payments
    op.drop_column('payments', 'refund_speed')
    op.drop_column('payments', 'refund_speed_processed')
    op.drop_column('payments', 'authorized_at')
    op.drop_column('payments', 'captured_at')
    op.drop_column('payments', 'voided_at')
    op.drop_column('payments', 'auto_capture')

    # Note: Cannot remove enum values in PostgreSQL without recreating the type
    # This would require dropping all dependent columns first
    # For safety, we leave the enum values in place
