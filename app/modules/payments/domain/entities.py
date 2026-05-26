"""
Domain Entities for Payment Module

Domain entities encapsulate business rules and behavior.
They represent core business concepts with identity.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.core.enums import PaymentStatus, RefundStatus
from app.modules.payments.domain.value_objects import Money, RefundAmount

if TYPE_CHECKING:
    from app.modules.payments.domain.payment import Payment


class PaymentEntity:
    """
    Domain entity for Payment with business rules.

    This entity encapsulates payment business logic and rules,
    separating domain concerns from data persistence.
    """

    def __init__(self, payment: "Payment"):
        """
        Initialize PaymentEntity from ORM model.

        Args:
            payment: Payment ORM model instance
        """
        self._payment = payment

    @property
    def id(self) -> int:
        """Payment ID"""
        return self._payment.id

    @property
    def amount(self) -> Money:
        """Payment amount as Money value object"""
        return Money(amount=self._payment.amount, currency=self._payment.currency)

    @property
    def status(self) -> str:
        """Payment status"""
        return self._payment.status

    @property
    def is_completed(self) -> bool:
        """Check if payment is completed"""
        return self._payment.status == PaymentStatus.COMPLETED.value

    @property
    def is_pending(self) -> bool:
        """Check if payment is pending"""
        return self._payment.status == PaymentStatus.PENDING.value

    @property
    def is_failed(self) -> bool:
        """Check if payment failed"""
        return self._payment.status == PaymentStatus.FAILED.value

    @property
    def is_refunded(self) -> bool:
        """Check if payment is refunded"""
        return self._payment.status == PaymentStatus.REFUNDED.value

    @property
    def is_refundable(self) -> bool:
        """
        Business rule: Check if payment can be refunded.

        A payment can be refunded if:
        1. Payment status is COMPLETED
        2. Payment has not already been refunded
        3. Refund status is not PROCESSED

        Returns:
            True if payment can be refunded
        """
        return (
            self._payment.status == PaymentStatus.COMPLETED.value
            and self._payment.refund_status != RefundStatus.PROCESSED.value
        )

    @property
    def can_verify_signature(self) -> bool:
        """
        Business rule: Check if payment signature can be verified.

        Signature verification is only valid for pending payments.

        Returns:
            True if signature can be verified
        """
        return self._payment.status == PaymentStatus.PENDING.value

    @property
    def has_gateway_details(self) -> bool:
        """Check if payment has gateway order details"""
        return bool(self._payment.gateway_order_id or self._payment.razorpay_order_id)

    @property
    def gateway_order_id(self) -> str | None:
        """Get gateway order ID (generic or Razorpay)"""
        return self._payment.gateway_order_id or self._payment.razorpay_order_id

    @property
    def gateway_payment_id(self) -> str | None:
        """Get gateway payment ID (generic or Razorpay)"""
        return self._payment.gateway_payment_id or self._payment.razorpay_payment_id

    def get_refund_error_message(self) -> str:
        """
        Get appropriate error message if payment cannot be refunded.

        Returns:
            Error message explaining why refund is not possible
        """
        if self._payment.status != PaymentStatus.COMPLETED.value:
            return (
                f"Only completed payments can be refunded. Current status: {self._payment.status}"
            )

        if self._payment.refund_status == RefundStatus.PROCESSED.value:
            return "Payment already refunded"

        return "Payment cannot be refunded"

    def validate_refund_amount(self, refund_amount: Decimal) -> tuple[bool, str | None]:
        """
        Validate refund amount against business rules.

        Args:
            refund_amount: Amount to refund

        Returns:
            Tuple of (is_valid, error_message)
        """
        if refund_amount <= 0:
            return False, "Refund amount must be positive"

        if refund_amount > self._payment.amount:
            return False, (
                f"Refund amount ({refund_amount}) cannot exceed "
                f"payment amount ({self._payment.amount})"
            )

        if not self.is_refundable:
            return False, self.get_refund_error_message()

        return True, None

    def create_refund_amount(self, amount: Decimal | None = None) -> RefundAmount:
        """
        Create RefundAmount value object.

        Args:
            amount: Refund amount (if None, full refund)

        Returns:
            RefundAmount value object

        Raises:
            ValueError: If refund amount is invalid
        """
        refund_amt = amount if amount is not None else self._payment.amount

        is_valid, error = self.validate_refund_amount(refund_amt)
        if not is_valid:
            raise ValueError(error)

        return RefundAmount(
            amount=refund_amt,
            currency=self._payment.currency,
            original_payment_amount=self._payment.amount,
        )

    @property
    def is_tier_upgrade_payment(self) -> bool:
        """Check if this is a tier upgrade payment"""
        return self._payment.is_tier_upgrade

    @property
    def has_tier(self) -> bool:
        """Check if payment is associated with a tier"""
        return self._payment.tier_id is not None

    @property
    def age_in_hours(self) -> float:
        """
        Calculate payment age in hours.

        Useful for business rules like "cancel pending payment after 24 hours".

        Returns:
            Age in hours since payment initiation
        """
        if not self._payment.initiated_at:
            return 0.0

        now = datetime.now()
        delta = now - self._payment.initiated_at
        return delta.total_seconds() / 3600

    def is_stale(self, max_age_hours: int = 24) -> bool:
        """
        Check if pending payment is stale.

        Business rule: Pending payments older than max_age_hours should be cancelled.

        Args:
            max_age_hours: Maximum age in hours (default: 24)

        Returns:
            True if payment is pending and older than max_age_hours
        """
        return self.is_pending and self.age_in_hours > max_age_hours

    def can_create_order_for_registration(self, registration_id: int) -> bool:
        """
        Business rule: Check if a new payment order can be created for registration.

        Args:
            registration_id: Registration ID to check

        Returns:
            True if new order can be created
        """
        # If this payment is for a different registration, allow new order
        if self._payment.registration_id != registration_id:
            return True

        # If payment is completed, don't allow duplicate
        if self.is_completed:
            return False

        # If payment is failed or refunded, allow new order
        if self.is_failed or self.is_refunded:
            return True

        # If payment is pending but stale, allow new order
        if self.is_stale():
            return True

        return False

    def __repr__(self) -> str:
        return f"PaymentEntity(id={self.id}, " f"amount={self.amount}, " f"status='{self.status}')"
