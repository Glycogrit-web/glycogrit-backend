"""
Coupon Service - Secure coupon validation and redemption logic

SECURITY PRINCIPLES:
- All validation happens server-side (never trust client)
- Row-level locking prevents concurrent redemption exploits
- Atomic operations ensure consistency
- Server-side discount calculation only
"""

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.coupons.domain.coupon import Coupon, CouponUsage

logger = logging.getLogger(__name__)


class CouponService:
    """Service for secure coupon validation and redemption"""

    def __init__(self, db: Session):
        self.db = db

    def validate_and_calculate_discount(
        self, coupon_code: str, user_id: int, event_id: int, tier_id: int | None, amount: Decimal
    ) -> tuple[Coupon, Decimal]:
        """
        Validate coupon and calculate discount amount.

        CRITICAL SECURITY:
        - Uses row-level locking to prevent concurrent redemptions
        - Server-side validation (NEVER trust client)
        - Atomic check-and-increment of usage count

        Args:
            coupon_code: Coupon code to validate
            user_id: User attempting to use coupon
            event_id: Event ID for registration
            tier_id: Tier ID (optional)
            amount: Original payment amount

        Returns:
            Tuple[Coupon, Decimal]: (Validated coupon, discount amount)

        Raises:
            ValidationException: If coupon is invalid or cannot be used
            NotFoundException: If coupon not found
        """
        # Lock coupon row for update (prevent concurrent usage)
        coupon = (
            self.db.query(Coupon)
            .filter(Coupon.code == coupon_code.upper().strip())  # Case-insensitive, trimmed
            .with_for_update()
            .first()
        )

        if not coupon:
            raise NotFoundException("Coupon", coupon_code)

        # VALIDATION 1: Check if coupon is active
        if not coupon.is_active:
            raise ValidationException("Coupon is no longer active", "coupon_inactive")

        # VALIDATION 2: Check validity period
        now = datetime.utcnow()
        if coupon.valid_from and now < coupon.valid_from:
            raise ValidationException("Coupon is not yet valid", "coupon_not_yet_valid")
        if coupon.valid_until and now > coupon.valid_until:
            raise ValidationException("Coupon has expired", "coupon_expired")

        # VALIDATION 3: Check global usage limit (with lock held - atomic)
        if coupon.max_redemptions is not None:
            if coupon.current_redemptions >= coupon.max_redemptions:
                raise ValidationException("Coupon usage limit reached", "coupon_limit_reached")

        # VALIDATION 4: Check per-user usage limit
        user_usage_count = (
            self.db.query(CouponUsage)
            .filter(CouponUsage.coupon_id == coupon.id, CouponUsage.user_id == user_id)
            .count()
        )

        if coupon.max_redemptions_per_user and user_usage_count >= coupon.max_redemptions_per_user:
            raise ValidationException(
                f"You have already used this coupon {user_usage_count} time(s)",
                "coupon_user_limit_reached",
            )

        # VALIDATION 5: Check event restrictions
        if coupon.event_restrictions:
            if "event_ids" in coupon.event_restrictions:
                allowed_events = coupon.event_restrictions["event_ids"]
                if event_id not in allowed_events:
                    raise ValidationException(
                        "Coupon not valid for this event", "coupon_event_restriction"
                    )
            # If all_events: true, no restriction

        # VALIDATION 6: Check tier restrictions
        if tier_id and coupon.tier_restrictions:
            if "tier_ids" in coupon.tier_restrictions:
                allowed_tiers = coupon.tier_restrictions["tier_ids"]
                if tier_id not in allowed_tiers:
                    raise ValidationException(
                        "Coupon not valid for this tier", "coupon_tier_restriction"
                    )
            # If all_tiers: true, no restriction

        # VALIDATION 7: Check minimum purchase amount
        if coupon.min_purchase_amount and amount < coupon.min_purchase_amount:
            raise ValidationException(
                f"Minimum purchase amount of ₹{coupon.min_purchase_amount} required",
                "coupon_min_amount",
            )

        # Calculate discount (SERVER-SIDE ONLY)
        discount_amount = self._calculate_discount(coupon, amount)

        logger.info(
            f"Coupon {coupon_code} validated for user {user_id}: "
            f"discount ₹{discount_amount} on ₹{amount}"
        )

        return coupon, discount_amount

    def _calculate_discount(self, coupon: Coupon, amount: Decimal) -> Decimal:
        """
        Calculate discount amount based on coupon type.

        SECURITY: All discount calculations MUST happen server-side.
        NEVER trust discount amounts from the client.

        Args:
            coupon: Validated coupon
            amount: Original amount

        Returns:
            Decimal: Discount amount
        """
        if coupon.discount_type == "fixed":
            # Fixed amount discount (e.g., ₹100 off)
            discount = min(coupon.discount_value, amount)
        elif coupon.discount_type == "percentage":
            # Percentage discount (e.g., 20% off)
            discount = amount * (coupon.discount_value / Decimal("100"))

            # Cap at max_discount_amount if specified
            if coupon.max_discount_amount:
                discount = min(discount, coupon.max_discount_amount)
        else:
            logger.error(f"Unknown discount type: {coupon.discount_type}")
            discount = Decimal("0")

        # Ensure discount doesn't exceed amount
        discount = min(discount, amount)
        return discount.quantize(Decimal("0.01"))  # Round to 2 decimal places

    def redeem_coupon(
        self,
        coupon: Coupon,
        user_id: int,
        registration_id: int,
        payment_id: int,
        discount_applied: Decimal,
        original_amount: Decimal,
        final_amount: Decimal,
    ) -> CouponUsage:
        """
        Record coupon redemption after successful payment.

        CRITICAL: Only call this AFTER payment is confirmed.
        This method atomically increments usage count.

        Args:
            coupon: Coupon being redeemed
            user_id: User redeeming coupon
            registration_id: Registration ID
            payment_id: Payment ID
            discount_applied: Discount amount applied
            original_amount: Original payment amount
            final_amount: Final amount paid

        Returns:
            CouponUsage: Created usage record
        """
        # Lock coupon for update
        coupon = self.db.query(Coupon).filter(Coupon.id == coupon.id).with_for_update().first()

        if not coupon:
            raise NotFoundException("Coupon", coupon.id)

        # Increment usage count (atomic with lock held)
        coupon.current_redemptions += 1

        # Create usage record
        usage = CouponUsage(
            coupon_id=coupon.id,
            user_id=user_id,
            registration_id=registration_id,
            payment_id=payment_id,
            discount_applied=discount_applied,
            original_amount=original_amount,
            final_amount=final_amount,
        )
        self.db.add(usage)
        self.db.flush()

        logger.info(
            f"Coupon {coupon.code} redeemed by user {user_id} "
            f"for registration {registration_id} (discount: ₹{discount_applied})"
        )

        return usage

    def release_coupon_reservation(self, coupon_id: int) -> None:
        """
        Release a coupon reservation (on payment failure).

        This decrements the usage count if it was incremented prematurely.

        NOTE: In current implementation, we don't reserve coupons -
        we only redeem after payment success. This method is here for
        future enhancement if we add reservation support.

        Args:
            coupon_id: Coupon ID to release
        """
        coupon = self.db.query(Coupon).filter(Coupon.id == coupon_id).with_for_update().first()

        if coupon and coupon.current_redemptions > 0:
            coupon.current_redemptions -= 1
            self.db.flush()
            logger.info(f"Released coupon reservation for coupon {coupon_id}")

    def get_coupon_by_code(self, code: str) -> Coupon | None:
        """
        Get coupon by code (without locking).

        Args:
            code: Coupon code

        Returns:
            Coupon or None
        """
        return self.db.query(Coupon).filter(Coupon.code == code.upper().strip()).first()

    def get_coupon_by_id(self, coupon_id: int) -> Coupon | None:
        """
        Get coupon by ID.

        Args:
            coupon_id: Coupon ID

        Returns:
            Coupon or None
        """
        return self.db.query(Coupon).filter(Coupon.id == coupon_id).first()

    def get_user_coupon_usage(self, user_id: int, coupon_code: str | None = None):
        """
        Get coupon usage history for a user.

        Args:
            user_id: User ID
            coupon_code: Optional coupon code to filter

        Returns:
            List of CouponUsage records
        """
        query = self.db.query(CouponUsage).filter(CouponUsage.user_id == user_id)

        if coupon_code:
            coupon = self.get_coupon_by_code(coupon_code)
            if coupon:
                query = query.filter(CouponUsage.coupon_id == coupon.id)

        return query.order_by(CouponUsage.used_at.desc()).all()

    def check_coupon_eligibility(
        self, coupon_code: str, user_id: int, event_id: int | None = None
    ) -> dict:
        """
        Check if user is eligible to use a coupon (without locking).

        Useful for frontend validation before payment.

        Args:
            coupon_code: Coupon code
            user_id: User ID
            event_id: Optional event ID for restriction check

        Returns:
            Dict with eligibility status and reason
        """
        coupon = self.get_coupon_by_code(coupon_code)

        if not coupon:
            return {"eligible": False, "reason": "Coupon not found"}

        if not coupon.is_valid:
            if not coupon.is_active:
                return {"eligible": False, "reason": "Coupon is inactive"}
            if coupon.is_expired:
                return {"eligible": False, "reason": "Coupon has expired"}
            if coupon.is_not_yet_valid:
                return {"eligible": False, "reason": "Coupon is not yet valid"}
            if coupon.is_sold_out:
                return {"eligible": False, "reason": "Coupon usage limit reached"}

        # Check per-user limit
        user_usage_count = (
            self.db.query(CouponUsage)
            .filter(CouponUsage.coupon_id == coupon.id, CouponUsage.user_id == user_id)
            .count()
        )

        if coupon.max_redemptions_per_user and user_usage_count >= coupon.max_redemptions_per_user:
            return {
                "eligible": False,
                "reason": f"You have already used this coupon {user_usage_count} time(s)",
            }

        # Check event restriction
        if event_id and coupon.event_restrictions:
            if "event_ids" in coupon.event_restrictions:
                if event_id not in coupon.event_restrictions["event_ids"]:
                    return {"eligible": False, "reason": "Coupon not valid for this event"}

        return {
            "eligible": True,
            "coupon": {
                "code": coupon.code,
                "discount_type": coupon.discount_type,
                "discount_value": float(coupon.discount_value),
                "min_purchase_amount": (
                    float(coupon.min_purchase_amount) if coupon.min_purchase_amount else None
                ),
                "redemptions_remaining": coupon.redemptions_remaining,
            },
        }
