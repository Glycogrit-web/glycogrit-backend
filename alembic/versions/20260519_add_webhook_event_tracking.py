"""Add webhook event tracking for idempotency

Revision ID: webhook_event_tracking
Revises: data_integrity_constraints
Create Date: 2026-05-19

This migration adds webhook_events table to track processed webhook events
and prevent duplicate processing (replay attacks, network retries).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'webhook_event_tracking'
down_revision = 'data_integrity_constraints'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create webhook_events table for idempotency tracking.
    """
    op.create_table(
        'webhook_events',

        # Primary Key
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),

        # Webhook Event Identity
        sa.Column('gateway_event_id', sa.String(length=255), nullable=False, unique=True),
        sa.Column('gateway_name', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),

        # Processing Status
        sa.Column('processed', sa.Boolean(), nullable=False, default=False),
        sa.Column('processed_at', sa.TIMESTAMP(), nullable=True),

        # Related Entity IDs
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('registration_id', sa.Integer(), nullable=True),
        sa.Column('gateway_payment_id', sa.String(length=100), nullable=True),

        # Webhook Data
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('signature', sa.String(length=255), nullable=True),

        # Error Tracking
        sa.Column('processing_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('last_error', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('received_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),

        sa.PrimaryKeyConstraint('id')
    )

    # Indexes
    op.create_index('idx_webhook_gateway_event_id', 'webhook_events', ['gateway_event_id'])
    op.create_index('idx_webhook_gateway_name', 'webhook_events', ['gateway_name'])
    op.create_index('idx_webhook_event_type', 'webhook_events', ['event_type'])
    op.create_index('idx_webhook_processed', 'webhook_events', ['processed'])
    op.create_index('idx_webhook_payment_id', 'webhook_events', ['payment_id'])
    op.create_index('idx_webhook_registration_id', 'webhook_events', ['registration_id'])
    op.create_index('idx_webhook_gateway_payment_id', 'webhook_events', ['gateway_payment_id'])
    op.create_index('idx_webhook_received_at', 'webhook_events', ['received_at'])

    # Composite indexes
    op.create_index(
        'idx_webhook_gateway_event',
        'webhook_events',
        ['gateway_name', 'gateway_event_id']
    )

    op.create_index(
        'idx_webhook_processing',
        'webhook_events',
        ['processed', 'received_at']
    )

    op.create_index(
        'idx_webhook_payment_lookup',
        'webhook_events',
        ['gateway_payment_id', 'gateway_name']
    )


def downgrade():
    """
    Drop webhook_events table.
    """
    op.drop_index('idx_webhook_payment_lookup', table_name='webhook_events')
    op.drop_index('idx_webhook_processing', table_name='webhook_events')
    op.drop_index('idx_webhook_gateway_event', table_name='webhook_events')
    op.drop_index('idx_webhook_received_at', table_name='webhook_events')
    op.drop_index('idx_webhook_gateway_payment_id', table_name='webhook_events')
    op.drop_index('idx_webhook_registration_id', table_name='webhook_events')
    op.drop_index('idx_webhook_payment_id', table_name='webhook_events')
    op.drop_index('idx_webhook_processed', table_name='webhook_events')
    op.drop_index('idx_webhook_event_type', table_name='webhook_events')
    op.drop_index('idx_webhook_gateway_name', table_name='webhook_events')
    op.drop_index('idx_webhook_gateway_event_id', table_name='webhook_events')

    op.drop_table('webhook_events')
