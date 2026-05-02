"""
Query objects for Payment Service.

Queries represent read operations that don't modify state.
They encapsulate all data needed to retrieve information.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class GetPaymentByIdQuery:
    """
    Query to get a payment by ID.
    """
    payment_id: int
    user_id: Optional[int] = None  # For permission check

    def __post_init__(self):
        """Validate query data"""
        if self.payment_id <= 0:
            raise ValueError("payment_id must be positive")
        if self.user_id is not None and self.user_id <= 0:
            raise ValueError("user_id must be positive")


@dataclass
class GetUserPaymentsQuery:
    """
    Query to get all payments for a user.
    """
    user_id: int
    current_user_id: int  # For permission check
    skip: int = 0
    limit: int = 100

    def __post_init__(self):
        """Validate query data"""
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.current_user_id <= 0:
            raise ValueError("current_user_id must be positive")
        if self.skip < 0:
            raise ValueError("skip cannot be negative")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")


@dataclass
class GetRegistrationPaymentsQuery:
    """
    Query to get all payments for a registration.
    """
    registration_id: int
    current_user_id: int  # For permission check

    def __post_init__(self):
        """Validate query data"""
        if self.registration_id <= 0:
            raise ValueError("registration_id must be positive")
        if self.current_user_id <= 0:
            raise ValueError("current_user_id must be positive")


@dataclass
class GetPaymentByOrderIdQuery:
    """
    Query to get a payment by gateway order ID.
    """
    order_id: str
    gateway: Optional[str] = None  # razorpay, stripe, etc.

    def __post_init__(self):
        """Validate query data"""
        if not self.order_id:
            raise ValueError("order_id is required")


@dataclass
class GetPaymentByTransactionIdQuery:
    """
    Query to get a payment by transaction ID.
    """
    transaction_id: str

    def __post_init__(self):
        """Validate query data"""
        if not self.transaction_id:
            raise ValueError("transaction_id is required")


@dataclass
class GetPaymentStatsQuery:
    """
    Query to get payment statistics for a user or event.
    """
    user_id: Optional[int] = None
    event_id: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    def __post_init__(self):
        """Validate query data"""
        if self.user_id is None and self.event_id is None:
            raise ValueError("Either user_id or event_id must be provided")
        if self.user_id is not None and self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.event_id is not None and self.event_id <= 0:
            raise ValueError("event_id must be positive")
