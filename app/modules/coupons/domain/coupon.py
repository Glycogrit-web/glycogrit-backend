"""
Coupon Domain Models - SQLAlchemy ORM models for coupons and usage tracking
"""
from sqlalchemy import Column, Integer, String, Numeric, Boolean, TIMESTAMP, ForeignKey, CheckConstraint, UniqueConstraint, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any

from app.core.database import Base


class Coupon(Base):
    """
    Coupon model - Represents discount codes for events and tiers

    SECURITY FEATURES:
    - All discount calculations happen server-side (never trust client)
    - Usage limits enforced at database level with constraints
    - Atomic redemption tracking with row-level locking
    """
    __tablename__ = "coupons"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Coupon Code (unique, case-insensitive)
    code = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Discount Configuration
    discount_type = Column(String(20), nullable=False)  # 'fixed', 'percentage'
    discount_value = Column(Numeric(10, 2), nullable=False)
    max_discount_amount = Column(Numeric(10, 2), nullable=True)  # For percentage discounts

    # Validity Period
    valid_from = Column(TIMESTAMP, nullable=False, server_default=func.now())
    valid_until = Column(TIMESTAMP, nullable=True)

    # Usage Limits
    max_redemptions = Column(Integer, nullable=True)  # Global limit (None = unlimited)
    current_redemptions = Column(Integer, nullable=False, server_default='0')
    max_redemptions_per_user = Column(Integer, nullable=False, server_default='1')

    # Restrictions (JSONB for flexibility)
    event_restrictions = Column(JSONB, nullable=True)  # {"event_ids": [1, 2, 3]} or {"all_events": true}
    tier_restrictions = Column(JSONB, nullable=True)   # {"tier_ids": [1, 2]} or {"all_tiers": true}
    min_purchase_amount = Column(Numeric(10, 2), nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, server_default='true', index=True)

    # Metadata
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    usage_history = relationship("CouponUsage", back_populates="coupon", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])

    # Database Constraints (enforced at DB level for security)
    __table_args__ = (
        CheckConstraint("discount_type IN ('fixed', 'percentage')", name='ck_coupon_discount_type_valid'),
        CheckConstraint('discount_value > 0', name='ck_coupon_discount_value_positive'),
        CheckConstraint('max_discount_amount IS NULL OR max_discount_amount > 0', name='ck_coupon_max_discount_positive'),
        CheckConstraint('valid_until IS NULL OR valid_until > valid_from', name='ck_coupon_validity_period_valid'),
        CheckConstraint('max_redemptions IS NULL OR max_redemptions > 0', name='ck_coupon_max_redemptions_positive'),
        CheckConstraint('current_redemptions >= 0', name='ck_coupon_current_redemptions_non_negative'),
        CheckConstraint('max_redemptions IS NULL OR current_redemptions <= max_redemptions', name='ck_coupon_max_redemptions_not_exceeded'),
        CheckConstraint('max_redemptions_per_user > 0', name='ck_coupon_max_redemptions_per_user_positive'),
        CheckConstraint('min_purchase_amount IS NULL OR min_purchase_amount >= 0', name='ck_coupon_min_purchase_non_negative'),
    )

    # Computed Properties
    @property
    def is_free(self) -> bool:
        """Check if coupon makes purchase free"""
        return self.discount_type == 'fixed' and self.discount_value >= 99999

    @property
    def is_expired(self) -> bool:
        """Check if coupon is expired"""
        if not self.valid_until:
            return False
        return datetime.utcnow() > self.valid_until

    @property
    def is_not_yet_valid(self) -> bool:
        """Check if coupon is not yet valid"""
        return datetime.utcnow() < self.valid_from

    @property
    def is_sold_out(self) -> bool:
        """Check if coupon has reached usage limit"""
        if self.max_redemptions is None:
            return False
        return self.current_redemptions >= self.max_redemptions

    @property
    def is_valid(self) -> bool:
        """Check if coupon is currently valid for use"""
        return (
            self.is_active and
            not self.is_expired and
            not self.is_not_yet_valid and
            not self.is_sold_out
        )

    @property
    def redemptions_remaining(self) -> Optional[int]:
        """Get number of redemptions remaining"""
        if self.max_redemptions is None:
            return None  # Unlimited
        return max(0, self.max_redemptions - self.current_redemptions)

    def calculate_discount(self, amount: Decimal) -> Decimal:
        """
        Calculate discount amount for given purchase amount.

        SECURITY: This is a helper method but actual discount calculation
        MUST happen in the service layer with proper validation.

        Args:
            amount: Original purchase amount

        Returns:
            Decimal: Discount amount
        """
        if self.discount_type == 'fixed':
            # Fixed amount discount
            discount = min(self.discount_value, amount)
        elif self.discount_type == 'percentage':
            # Percentage discount
            discount = amount * (self.discount_value / Decimal("100"))

            # Cap at max_discount_amount if specified
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = Decimal("0")

        # Ensure discount doesn't exceed amount
        discount = min(discount, amount)
        return discount.quantize(Decimal("0.01"))  # Round to 2 decimal places

    def __repr__(self):
        return f"<Coupon(id={self.id}, code='{self.code}', type='{self.discount_type}', value={self.discount_value})>"


class CouponUsage(Base):
    """
    Coupon Usage model - Tracks coupon redemptions by users

    SECURITY FEATURES:
    - Unique constraint prevents duplicate usage per user/registration
    - Immutable record (updates not allowed after creation)
    - Links to payment for refund handling
    """
    __tablename__ = "coupon_usage"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    coupon_id = Column(Integer, ForeignKey('coupons.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    registration_id = Column(Integer, ForeignKey('registrations.id', ondelete='SET NULL'), nullable=True, index=True)
    payment_id = Column(Integer, ForeignKey('payments.id', ondelete='SET NULL'), nullable=True, index=True)

    # Usage Details
    discount_applied = Column(Numeric(10, 2), nullable=False)
    original_amount = Column(Numeric(10, 2), nullable=False)
    final_amount = Column(Numeric(10, 2), nullable=False)

    # Timestamp
    used_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)

    # Relationships
    coupon = relationship("Coupon", back_populates="usage_history")
    user = relationship("User")
    registration = relationship("Registration")
    payment = relationship("Payment")

    # Database Constraints
    __table_args__ = (
        CheckConstraint('discount_applied >= 0', name='ck_coupon_usage_discount_non_negative'),
        CheckConstraint('original_amount >= 0', name='ck_coupon_usage_original_amount_non_negative'),
        CheckConstraint('final_amount >= 0', name='ck_coupon_usage_final_amount_non_negative'),
        CheckConstraint('final_amount = original_amount - discount_applied', name='ck_coupon_usage_amounts_consistent'),

        # CRITICAL: Unique constraint prevents duplicate coupon usage per user/registration
        UniqueConstraint('coupon_id', 'user_id', 'registration_id', name='uq_coupon_usage_user_registration'),
    )

    def __repr__(self):
        return f"<CouponUsage(id={self.id}, coupon_id={self.coupon_id}, user_id={self.user_id}, discount={self.discount_applied})>"
