"""Add coupon system for discounts and promotions

Revision ID: add_coupon_system
Revises: webhook_event_tracking
Create Date: 2026-05-23

This migration adds the complete coupon system infrastructure:
1. coupons table - Store coupon codes, discounts, and usage limits
2. coupon_usage table - Track coupon redemptions by users
3. Add coupon fields to payments table
4. Add coupon fields to registrations table (for tracking)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'add_coupon_system'
down_revision = 'webhook_event_tracking'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add coupon system tables and fields.

    SECURITY FEATURES:
    - Unique constraints prevent coupon code duplication
    - Check constraints enforce valid discount values
    - Unique constraint prevents duplicate coupon usage per user/registration
    - JSONB restrictions allow flexible event/tier targeting
    """

    # ========================================
    # 1. CREATE COUPONS TABLE
    # ========================================
    op.create_table(
        'coupons',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),

        # Discount Configuration
        sa.Column('discount_type', sa.String(length=20), nullable=False),
        sa.Column('discount_value', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('max_discount_amount', sa.Numeric(precision=10, scale=2), nullable=True),

        # Validity Period
        sa.Column('valid_from', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('valid_until', sa.TIMESTAMP(), nullable=True),

        # Usage Limits
        sa.Column('max_redemptions', sa.Integer(), nullable=True),
        sa.Column('current_redemptions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_redemptions_per_user', sa.Integer(), nullable=False, server_default='1'),

        # Restrictions (JSONB for flexibility)
        sa.Column('event_restrictions', JSONB, nullable=True),
        sa.Column('tier_restrictions', JSONB, nullable=True),
        sa.Column('min_purchase_amount', sa.Numeric(precision=10, scale=2), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Metadata
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),

        # Constraints
        sa.CheckConstraint('discount_type IN (\'fixed\', \'percentage\')', name='ck_coupon_discount_type_valid'),
        sa.CheckConstraint('discount_value > 0', name='ck_coupon_discount_value_positive'),
        sa.CheckConstraint('max_discount_amount IS NULL OR max_discount_amount > 0', name='ck_coupon_max_discount_positive'),
        sa.CheckConstraint('valid_until IS NULL OR valid_until > valid_from', name='ck_coupon_validity_period_valid'),
        sa.CheckConstraint('max_redemptions IS NULL OR max_redemptions > 0', name='ck_coupon_max_redemptions_positive'),
        sa.CheckConstraint('current_redemptions >= 0', name='ck_coupon_current_redemptions_non_negative'),
        sa.CheckConstraint('max_redemptions IS NULL OR current_redemptions <= max_redemptions', name='ck_coupon_max_redemptions_not_exceeded'),
        sa.CheckConstraint('max_redemptions_per_user > 0', name='ck_coupon_max_redemptions_per_user_positive'),
        sa.CheckConstraint('min_purchase_amount IS NULL OR min_purchase_amount >= 0', name='ck_coupon_min_purchase_non_negative'),
    )

    # Indexes for efficient lookups
    op.create_index('idx_coupons_code', 'coupons', ['code'], unique=True)
    op.create_index('idx_coupons_is_active', 'coupons', ['is_active'])
    op.create_index('idx_coupons_validity', 'coupons', ['valid_from', 'valid_until'])
    op.create_index('idx_coupons_created_by', 'coupons', ['created_by'])

    # ========================================
    # 2. CREATE COUPON_USAGE TABLE
    # ========================================
    op.create_table(
        'coupon_usage',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('coupon_id', sa.Integer(), sa.ForeignKey('coupons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('registration_id', sa.Integer(), sa.ForeignKey('registrations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('payment_id', sa.Integer(), sa.ForeignKey('payments.id', ondelete='SET NULL'), nullable=True),

        # Usage Details
        sa.Column('discount_applied', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('original_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('final_amount', sa.Numeric(precision=10, scale=2), nullable=False),

        # Timestamp
        sa.Column('used_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),

        # Constraints
        sa.CheckConstraint('discount_applied >= 0', name='ck_coupon_usage_discount_non_negative'),
        sa.CheckConstraint('original_amount >= 0', name='ck_coupon_usage_original_amount_non_negative'),
        sa.CheckConstraint('final_amount >= 0', name='ck_coupon_usage_final_amount_non_negative'),
        sa.CheckConstraint('final_amount = original_amount - discount_applied', name='ck_coupon_usage_amounts_consistent'),

        # Unique Constraint: One coupon per user per registration (prevent stacking)
        sa.UniqueConstraint('coupon_id', 'user_id', 'registration_id', name='uq_coupon_usage_user_registration'),
    )

    # Indexes for efficient lookups
    op.create_index('idx_coupon_usage_coupon_id', 'coupon_usage', ['coupon_id'])
    op.create_index('idx_coupon_usage_user_id', 'coupon_usage', ['user_id'])
    op.create_index('idx_coupon_usage_registration_id', 'coupon_usage', ['registration_id'])
    op.create_index('idx_coupon_usage_payment_id', 'coupon_usage', ['payment_id'])
    op.create_index('idx_coupon_usage_used_at', 'coupon_usage', ['used_at'])

    # ========================================
    # 3. ADD COUPON FIELDS TO PAYMENTS TABLE
    # ========================================
    op.add_column('payments', sa.Column('coupon_id', sa.Integer(), sa.ForeignKey('coupons.id', ondelete='SET NULL'), nullable=True))
    op.add_column('payments', sa.Column('original_amount', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('payments', sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
    op.add_column('payments', sa.Column('idempotency_key', sa.String(length=100), nullable=True, unique=True))

    # Constraints for payment discount validation
    op.create_check_constraint(
        'ck_payment_discount_non_negative',
        'payments',
        'discount_amount >= 0'
    )
    op.create_check_constraint(
        'ck_payment_discount_valid',
        'payments',
        'discount_amount IS NULL OR original_amount IS NULL OR discount_amount <= original_amount'
    )

    # Indexes
    op.create_index('idx_payments_coupon_id', 'payments', ['coupon_id'])
    op.create_index('idx_payments_idempotency_key', 'payments', ['idempotency_key'], unique=True)

    # ========================================
    # 4. ADD RESERVED_SPOTS TO TIERS TABLE
    # ========================================
    # This field tracks pending reservations before payment completion
    # to prevent race conditions in tier capacity
    op.add_column(
        'event_registration_tiers',
        sa.Column('reserved_spots', sa.Integer(), nullable=False, server_default='0')
    )

    # Constraint: reserved_spots must be non-negative
    op.create_check_constraint(
        'ck_tier_reserved_spots_non_negative',
        'event_registration_tiers',
        'reserved_spots >= 0'
    )

    # Update capacity constraint to include reserved spots
    # Drop existing constraint first
    op.drop_constraint('ck_tier_capacity_limit', 'event_registration_tiers', type_='check')

    # Recreate with updated logic
    op.create_check_constraint(
        'ck_tier_capacity_limit',
        'event_registration_tiers',
        'max_registrations IS NULL OR (current_registrations + reserved_spots) <= max_registrations'
    )


def downgrade():
    """
    Remove coupon system tables and fields.

    WARNING: This will delete all coupon data. Use with caution.
    """

    # Drop constraints first
    op.drop_constraint('ck_tier_capacity_limit', 'event_registration_tiers', type_='check')
    op.drop_constraint('ck_tier_reserved_spots_non_negative', 'event_registration_tiers', type_='check')
    op.drop_constraint('ck_payment_discount_valid', 'payments', type_='check')
    op.drop_constraint('ck_payment_discount_non_negative', 'payments', type_='check')

    # Drop indexes
    op.drop_index('idx_payments_idempotency_key', 'payments')
    op.drop_index('idx_payments_coupon_id', 'payments')
    op.drop_index('idx_coupon_usage_used_at', 'coupon_usage')
    op.drop_index('idx_coupon_usage_payment_id', 'coupon_usage')
    op.drop_index('idx_coupon_usage_registration_id', 'coupon_usage')
    op.drop_index('idx_coupon_usage_user_id', 'coupon_usage')
    op.drop_index('idx_coupon_usage_coupon_id', 'coupon_usage')
    op.drop_index('idx_coupons_created_by', 'coupons')
    op.drop_index('idx_coupons_validity', 'coupons')
    op.drop_index('idx_coupons_is_active', 'coupons')
    op.drop_index('idx_coupons_code', 'coupons')

    # Drop columns
    op.drop_column('event_registration_tiers', 'reserved_spots')
    op.drop_column('payments', 'idempotency_key')
    op.drop_column('payments', 'discount_amount')
    op.drop_column('payments', 'original_amount')
    op.drop_column('payments', 'coupon_id')

    # Drop tables
    op.drop_table('coupon_usage')
    op.drop_table('coupons')

    # Recreate old capacity constraint
    op.create_check_constraint(
        'ck_tier_capacity_limit',
        'event_registration_tiers',
        'max_registrations IS NULL OR current_registrations <= max_registrations'
    )
