"""
Command objects for Payment Service.

Commands represent write operations that modify state.
They encapsulate all data needed to perform an operation.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class CreatePaymentOrderCommand:
    """
    Command to create a payment order.

    This command encapsulates all data needed to initiate a new payment.
    """

    registration_id: int
    user_id: int
    amount: Decimal | None = None  # If None, fetch from event/tier
    currency: str = "INR"
    tier_id: int | None = None
    is_tier_upgrade: bool = False
    notes: dict[str, Any] | None = None
    gateway: str | None = None  # If None, use default gateway

    def __post_init__(self):
        """Validate command data"""
        if self.registration_id <= 0:
            raise ValueError("registration_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.amount is not None and self.amount <= 0:
            raise ValueError("amount must be positive")
        if self.tier_id is not None and self.tier_id <= 0:
            raise ValueError("tier_id must be positive")


@dataclass
class VerifyPaymentCommand:
    """
    Command to verify a payment signature.

    This command encapsulates payment verification data from the gateway.
    """

    order_id: str
    payment_id: str
    signature: str
    user_id: int
    gateway: str = "razorpay"

    def __post_init__(self):
        """Validate command data"""
        if not self.order_id:
            raise ValueError("order_id is required")
        if not self.payment_id:
            raise ValueError("payment_id is required")
        if not self.signature:
            raise ValueError("signature is required")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if not self.gateway:
            raise ValueError("gateway is required")


@dataclass
class CreateRefundCommand:
    """
    Command to create a refund.

    This command encapsulates refund creation data.
    """

    payment_id: int
    user_id: int
    amount: Decimal | None = None  # If None, full refund
    reason: str | None = None
    notes: dict[str, Any] | None = None

    def __post_init__(self):
        """Validate command data"""
        if self.payment_id <= 0:
            raise ValueError("payment_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.amount is not None and self.amount <= 0:
            raise ValueError("amount must be positive")


@dataclass
class UpdatePaymentStatusCommand:
    """
    Command to update payment status.

    This command is used to manually update payment status
    (usually from admin or webhook).
    """

    payment_id: int
    status: str
    transaction_id: str | None = None
    gateway_reference: str | None = None
    gateway_name: str | None = None
    user_id: int | None = None  # For permission check

    def __post_init__(self):
        """Validate command data"""
        if self.payment_id <= 0:
            raise ValueError("payment_id must be positive")
        if not self.status:
            raise ValueError("status is required")
        # Validate status is a valid enum value
        from app.core.enums import PaymentStatus

        valid_statuses = [s.value for s in PaymentStatus]
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")


@dataclass
class InitiatePaymentCommand:
    """
    Command to initiate a simple payment (legacy).

    Simpler version for direct payment initiation without order creation.
    """

    registration_id: int
    user_id: int
    amount: float
    payment_method: str
    currency: str = "INR"

    def __post_init__(self):
        """Validate command data"""
        if self.registration_id <= 0:
            raise ValueError("registration_id must be positive")
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.amount <= 0:
            raise ValueError("amount must be positive")
        if not self.payment_method:
            raise ValueError("payment_method is required")
