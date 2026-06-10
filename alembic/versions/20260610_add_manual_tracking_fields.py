"""Add manual tracking fields and update reward status enum

Revision ID: 20260610_manual_tracking
Revises: 20260609_1430_b2b3683ed41c
Create Date: 2026-06-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260610_manual_tracking'
down_revision = 'b2b3683ed41c'
branch_labels = None
depends_on = None


def upgrade():
    """Add manual tracking fields for Excel-based workflow and update reward status enum"""

    # Add new manual tracking fields
    op.add_column('user_rewards', sa.Column('manual_tracking_id', sa.String(100), nullable=True))
    op.add_column('user_rewards', sa.Column('manual_tracking_url', sa.String(500), nullable=True))
    op.add_column('user_rewards', sa.Column('manual_courier_name', sa.String(100), nullable=True))
    op.add_column('user_rewards', sa.Column('manual_order_reference', sa.String(200), nullable=True))
    op.add_column('user_rewards', sa.Column('tracking_imported_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user_rewards', sa.Column('tracking_imported_by_admin_id', sa.Integer(), nullable=True))

    # Create indexes for performance
    op.create_index('ix_user_rewards_manual_tracking_id', 'user_rewards', ['manual_tracking_id'])

    # Create foreign key for tracking_imported_by_admin_id
    op.create_foreign_key(
        'fk_user_rewards_tracking_imported_by_admin',
        'user_rewards',
        'users',
        ['tracking_imported_by_admin_id'],
        ['id']
    )

    # Update RewardStatus enum to include new values
    # PostgreSQL requires enum values to be added in a separate transaction
    # Use raw connection with autocommit
    connection = op.get_bind()
    connection.execute(sa.text("COMMIT"))
    connection.execute(sa.text("ALTER TYPE rewardstatus ADD VALUE IF NOT EXISTS 'locked'"))
    connection.execute(sa.text("ALTER TYPE rewardstatus ADD VALUE IF NOT EXISTS 'ready_to_ship'"))
    connection.execute(sa.text("ALTER TYPE rewardstatus ADD VALUE IF NOT EXISTS 'tracking_order'"))

    # Start a new transaction for data migration
    # Migrate existing status values to new ones
    # PENDING_DETAILS -> LOCKED (not eligible yet)
    op.execute("UPDATE user_rewards SET status = 'locked' WHERE status = 'pending_details'")

    # PENDING_SHIPMENT -> READY_TO_SHIP (eligible, waiting for shipment)
    op.execute("UPDATE user_rewards SET status = 'ready_to_ship' WHERE status = 'pending_shipment'")

    # SHIPPED -> TRACKING_ORDER (order shipped with tracking)
    op.execute("UPDATE user_rewards SET status = 'tracking_order' WHERE status = 'shipped'")

    # DELIVERED and CANCELLED remain the same


def downgrade():
    """Remove manual tracking fields and revert reward status enum changes"""

    # Drop foreign key
    op.drop_constraint('fk_user_rewards_tracking_imported_by_admin', 'user_rewards', type_='foreignkey')

    # Drop indexes
    op.drop_index('ix_user_rewards_manual_tracking_id', 'user_rewards')

    # Drop columns
    op.drop_column('user_rewards', 'tracking_imported_by_admin_id')
    op.drop_column('user_rewards', 'tracking_imported_at')
    op.drop_column('user_rewards', 'manual_order_reference')
    op.drop_column('user_rewards', 'manual_courier_name')
    op.drop_column('user_rewards', 'manual_tracking_url')
    op.drop_column('user_rewards', 'manual_tracking_id')

    # Revert status values back to old enum
    # LOCKED -> PENDING_DETAILS
    op.execute("UPDATE user_rewards SET status = 'pending_details' WHERE status = 'locked'")

    # READY_TO_SHIP -> PENDING_SHIPMENT
    op.execute("UPDATE user_rewards SET status = 'pending_shipment' WHERE status = 'ready_to_ship'")

    # TRACKING_ORDER -> SHIPPED
    op.execute("UPDATE user_rewards SET status = 'shipped' WHERE status = 'tracking_order'")

    # Note: Can't remove enum values in PostgreSQL without recreating the type
    # This would require dropping and recreating the enum, which is complex
    # The old values (pending_details, pending_shipment, shipped) will remain in the enum
    # but won't be used after the downgrade
