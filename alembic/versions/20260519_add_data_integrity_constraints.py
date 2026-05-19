"""Add data integrity constraints for tier capacity and payment validation

Revision ID: data_integrity_constraints
Revises: fix_tier_payment
Create Date: 2026-05-19

This migration adds database-level constraints to enforce data integrity:
1. Tier capacity constraints (prevent negative counts, enforce capacity limits)
2. Payment amount constraints (prevent negative amounts)
3. Registration payment tracking constraints
4. Unique constraints for pending payment orders
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'data_integrity_constraints'
down_revision = 'fix_tier_payment'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add database constraints to enforce data integrity.

    These constraints work together with application-level locking
    to prevent data corruption from race conditions and invalid states.
    """

    # ========================================
    # 1. EVENT_REGISTRATION_TIERS CONSTRAINTS
    # ========================================

    # Constraint: current_registrations must be non-negative
    op.create_check_constraint(
        'ck_tier_current_registrations_non_negative',
        'event_registration_tiers',
        'current_registrations >= 0'
    )

    # Constraint: max_registrations must be positive (if set)
    op.create_check_constraint(
        'ck_tier_max_registrations_positive',
        'event_registration_tiers',
        'max_registrations IS NULL OR max_registrations > 0'
    )

    # Constraint: current_registrations cannot exceed max_registrations
    # This is the PRIMARY constraint preventing tier overselling
    op.create_check_constraint(
        'ck_tier_capacity_limit',
        'event_registration_tiers',
        'max_registrations IS NULL OR current_registrations <= max_registrations'
    )

    # Constraint: price must be non-negative
    op.create_check_constraint(
        'ck_tier_price_non_negative',
        'event_registration_tiers',
        'price >= 0'
    )

    # Constraint: tier_order must be non-negative
    op.create_check_constraint(
        'ck_tier_order_non_negative',
        'event_registration_tiers',
        'tier_order >= 0'
    )

    # Constraint: requires_payment consistency with price
    # If price = 0, requires_payment must be FALSE
    # If price > 0, requires_payment must be TRUE
    op.create_check_constraint(
        'ck_tier_requires_payment_consistency',
        'event_registration_tiers',
        '(price = 0 AND requires_payment = FALSE) OR (price > 0 AND requires_payment = TRUE)'
    )

    # ========================================
    # 2. PAYMENTS CONSTRAINTS
    # ========================================

    # Constraint: amount must be non-negative
    op.create_check_constraint(
        'ck_payment_amount_non_negative',
        'payments',
        'amount >= 0'
    )

    # Constraint: refund_amount must be non-negative (if set)
    op.create_check_constraint(
        'ck_payment_refund_amount_non_negative',
        'payments',
        'refund_amount IS NULL OR refund_amount >= 0'
    )

    # Constraint: refund_amount cannot exceed original amount
    op.create_check_constraint(
        'ck_payment_refund_amount_limit',
        'payments',
        'refund_amount IS NULL OR refund_amount <= amount'
    )

    # Constraint: valid payment status values
    op.create_check_constraint(
        'ck_payment_status_valid',
        'payments',
        "status IN ('pending', 'authorized', 'completed', 'failed', 'refunded', 'voided')"
    )

    # Constraint: valid refund status values (if set)
    op.create_check_constraint(
        'ck_payment_refund_status_valid',
        'payments',
        "refund_status IS NULL OR refund_status IN ('pending', 'processed', 'failed')"
    )

    # Constraint: if is_tier_upgrade is TRUE, tier_id must be set
    op.create_check_constraint(
        'ck_payment_tier_upgrade_requires_tier',
        'payments',
        'is_tier_upgrade = FALSE OR tier_id IS NOT NULL'
    )

    # Constraint: completed_at timestamp constraints
    # If status = 'completed', completed_at must be set
    # We can't enforce this at DB level perfectly, but we can check completed_at >= initiated_at
    op.create_check_constraint(
        'ck_payment_completed_at_after_initiated',
        'payments',
        'completed_at IS NULL OR completed_at >= initiated_at'
    )

    # Constraint: timestamp ordering for payment capture workflow
    # authorized_at must be after initiated_at
    op.create_check_constraint(
        'ck_payment_authorized_at_after_initiated',
        'payments',
        'authorized_at IS NULL OR authorized_at >= initiated_at'
    )

    # captured_at must be after authorized_at
    op.create_check_constraint(
        'ck_payment_captured_at_after_authorized',
        'payments',
        'captured_at IS NULL OR authorized_at IS NULL OR captured_at >= authorized_at'
    )

    # Unique constraint: Only one pending payment per registration+tier combination
    # This prevents users from creating multiple pending payments for the same tier upgrade
    # Note: Partial unique index (only applies to pending payments)
    op.execute("""
        CREATE UNIQUE INDEX idx_unique_pending_payment_per_registration_tier
        ON payments (registration_id, tier_id, is_tier_upgrade)
        WHERE status = 'pending'
    """)

    # ========================================
    # 3. REGISTRATIONS CONSTRAINTS
    # ========================================

    # Constraint: total_amount_paid must be non-negative
    op.create_check_constraint(
        'ck_registration_total_amount_paid_non_negative',
        'registrations',
        'total_amount_paid >= 0'
    )

    # Constraint: last_payment_amount must be non-negative (if set)
    op.create_check_constraint(
        'ck_registration_last_payment_amount_non_negative',
        'registrations',
        'last_payment_amount IS NULL OR last_payment_amount >= 0'
    )

    # Constraint: successful_payments_count must be non-negative
    op.create_check_constraint(
        'ck_registration_successful_payments_count_non_negative',
        'registrations',
        'successful_payments_count >= 0'
    )

    # Constraint: age must be positive (if set)
    op.create_check_constraint(
        'ck_registration_age_positive',
        'registrations',
        'age IS NULL OR age > 0'
    )

    # Constraint: valid registration status values
    op.create_check_constraint(
        'ck_registration_status_valid',
        'registrations',
        "status IN ('pending', 'confirmed', 'payment_completed', 'cancelled')"
    )

    # Constraint: valid last_payment_status values (if set)
    op.create_check_constraint(
        'ck_registration_last_payment_status_valid',
        'registrations',
        "last_payment_status IS NULL OR last_payment_status IN ('pending', 'success', 'failed', 'refunded')"
    )

    # Constraint: if uses_tier_system is TRUE, current_tier_id must be set
    op.create_check_constraint(
        'ck_registration_tier_system_requires_tier',
        'registrations',
        'uses_tier_system = FALSE OR current_tier_id IS NOT NULL'
    )

    # Constraint: confirmed_at must be after registered_at (if set)
    op.create_check_constraint(
        'ck_registration_confirmed_at_after_registered',
        'registrations',
        'confirmed_at IS NULL OR confirmed_at >= registered_at'
    )

    # ========================================
    # 4. EVENTS CONSTRAINTS (if applicable)
    # ========================================

    # Constraint: current_participants must be non-negative
    op.create_check_constraint(
        'ck_event_current_participants_non_negative',
        'events',
        'current_participants >= 0'
    )

    # Constraint: max_participants must be positive (if set)
    op.create_check_constraint(
        'ck_event_max_participants_positive',
        'events',
        'max_participants IS NULL OR max_participants > 0'
    )

    # Constraint: current_participants cannot exceed max_participants
    op.create_check_constraint(
        'ck_event_participant_capacity_limit',
        'events',
        'max_participants IS NULL OR current_participants <= max_participants'
    )


def downgrade():
    """
    Remove data integrity constraints.

    WARNING: Removing these constraints may allow data corruption.
    Only do this if you're certain you need to.
    """

    # Drop event constraints
    op.drop_constraint('ck_event_participant_capacity_limit', 'events', type_='check')
    op.drop_constraint('ck_event_max_participants_positive', 'events', type_='check')
    op.drop_constraint('ck_event_current_participants_non_negative', 'events', type_='check')

    # Drop registration constraints
    op.drop_constraint('ck_registration_confirmed_at_after_registered', 'registrations', type_='check')
    op.drop_constraint('ck_registration_tier_system_requires_tier', 'registrations', type_='check')
    op.drop_constraint('ck_registration_last_payment_status_valid', 'registrations', type_='check')
    op.drop_constraint('ck_registration_status_valid', 'registrations', type_='check')
    op.drop_constraint('ck_registration_age_positive', 'registrations', type_='check')
    op.drop_constraint('ck_registration_successful_payments_count_non_negative', 'registrations', type_='check')
    op.drop_constraint('ck_registration_last_payment_amount_non_negative', 'registrations', type_='check')
    op.drop_constraint('ck_registration_total_amount_paid_non_negative', 'registrations', type_='check')

    # Drop payment unique index
    op.execute("DROP INDEX IF EXISTS idx_unique_pending_payment_per_registration_tier")

    # Drop payment constraints
    op.drop_constraint('ck_payment_captured_at_after_authorized', 'payments', type_='check')
    op.drop_constraint('ck_payment_authorized_at_after_initiated', 'payments', type_='check')
    op.drop_constraint('ck_payment_completed_at_after_initiated', 'payments', type_='check')
    op.drop_constraint('ck_payment_tier_upgrade_requires_tier', 'payments', type_='check')
    op.drop_constraint('ck_payment_refund_status_valid', 'payments', type_='check')
    op.drop_constraint('ck_payment_status_valid', 'payments', type_='check')
    op.drop_constraint('ck_payment_refund_amount_limit', 'payments', type_='check')
    op.drop_constraint('ck_payment_refund_amount_non_negative', 'payments', type_='check')
    op.drop_constraint('ck_payment_amount_non_negative', 'payments', type_='check')

    # Drop tier constraints
    op.drop_constraint('ck_tier_requires_payment_consistency', 'event_registration_tiers', type_='check')
    op.drop_constraint('ck_tier_order_non_negative', 'event_registration_tiers', type_='check')
    op.drop_constraint('ck_tier_price_non_negative', 'event_registration_tiers', type_='check')
    op.drop_constraint('ck_tier_capacity_limit', 'event_registration_tiers', type_='check')
    op.drop_constraint('ck_tier_max_registrations_positive', 'event_registration_tiers', type_='check')
    op.drop_constraint('ck_tier_current_registrations_non_negative', 'event_registration_tiers', type_='check')
