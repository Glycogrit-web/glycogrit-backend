"""
Payment repository for database operations.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    """Repository for Payment model with payment-specific database operations."""

    def __init__(self, db: Session):
        """
        Initialize the PaymentRepository.

        Args:
            db: Database session
        """
        super().__init__(Payment, db)

    def get_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        """
        Retrieve a payment by transaction ID.

        Args:
            transaction_id: Transaction ID to search for

        Returns:
            Payment instance if found, None otherwise
        """
        return self.db.query(Payment).filter(
            Payment.transaction_id == transaction_id
        ).first()

    def get_payments_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Payment]:
        """
        Get all payments for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Payment instances
        """
        return self.db.query(Payment).filter(
            Payment.user_id == user_id
        ).order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()

    def get_payments_by_registration(self, registration_id: int) -> List[Payment]:
        """
        Get all payments for a registration.

        Args:
            registration_id: Registration ID

        Returns:
            List of Payment instances
        """
        return self.db.query(Payment).filter(
            Payment.registration_id == registration_id
        ).order_by(Payment.created_at.desc()).all()

    def get_payments_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Payment]:
        """
        Get payments by status.

        Args:
            status: Payment status (pending, completed, failed, refunded)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Payment instances
        """
        return self.db.query(Payment).filter(
            Payment.status == status
        ).order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()

    def transaction_id_exists(self, transaction_id: str) -> bool:
        """
        Check if a transaction ID already exists.

        Args:
            transaction_id: Transaction ID to check

        Returns:
            True if exists, False otherwise
        """
        return self.db.query(Payment).filter(
            Payment.transaction_id == transaction_id
        ).count() > 0

    def get_by_razorpay_order_id(self, razorpay_order_id: str) -> Optional[Payment]:
        """
        Retrieve a payment by Razorpay order ID.

        Args:
            razorpay_order_id: Razorpay order ID to search for

        Returns:
            Payment instance if found, None otherwise
        """
        return self.db.query(Payment).filter(
            Payment.razorpay_order_id == razorpay_order_id
        ).first()

    def get_by_gateway_order_id(self, gateway_order_id: str) -> Optional[Payment]:
        """
        Retrieve a payment by gateway order ID (generic for any gateway).

        Args:
            gateway_order_id: Gateway order ID to search for

        Returns:
            Payment instance if found, None otherwise
        """
        return self.db.query(Payment).filter(
            Payment.gateway_order_id == gateway_order_id
        ).first()
