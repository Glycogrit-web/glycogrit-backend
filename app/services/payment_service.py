"""
Payment service for business logic.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.payment import Payment
from app.repositories.payment_repository import PaymentRepository
from app.repositories.registration_repository import RegistrationRepository
from app.services.base import BaseService
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    PermissionDeniedException,
    ValidationException
)


class PaymentService(BaseService):
    """Service for payment-related business logic and operations."""

    def __init__(self, db: Session):
        """
        Initialize the PaymentService.

        Args:
            db: Database session
        """
        super().__init__(db)
        self.repository = PaymentRepository(db)
        self.registration_repository = RegistrationRepository(db)

    def initiate_payment(
        self,
        registration_id: int,
        user_id: int,
        amount: float,
        payment_method: str,
        currency: str = "INR"
    ) -> Payment:
        """
        Initiate a payment for a registration.

        Args:
            registration_id: Registration ID
            user_id: User ID making the payment
            amount: Payment amount
            payment_method: Payment method (credit_card, upi, net_banking, etc.)
            currency: Currency code (default: INR)

        Returns:
            Created Payment instance

        Raises:
            NotFoundException: If registration not found
            PermissionDeniedException: If user doesn't own the registration
        """
        # Get registration
        registration = self.registration_repository.get_by_id(registration_id)
        if not registration:
            raise NotFoundException("Registration", registration_id)

        # Check ownership
        self.check_ownership(registration.user_id, user_id, "registration")

        # Create payment
        payment_data = {
            "user_id": user_id,
            "registration_id": registration_id,
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
            "status": "pending"
        }

        payment = self.repository.create(payment_data)
        return payment

    def get_payment_by_id(self, payment_id: int) -> Payment:
        """
        Get a payment by ID.

        Args:
            payment_id: Payment ID

        Returns:
            Payment instance

        Raises:
            NotFoundException: If payment not found
        """
        return self.get_or_404(self.repository, payment_id, "Payment")

    def update_payment_status(
        self,
        payment_id: int,
        status: str,
        transaction_id: Optional[str] = None,
        gateway_reference: Optional[str] = None,
        gateway_name: Optional[str] = None
    ) -> Payment:
        """
        Update payment status.

        Args:
            payment_id: Payment ID
            status: New status (pending, completed, failed, refunded)
            transaction_id: Optional transaction ID
            gateway_reference: Optional gateway reference
            gateway_name: Optional gateway name

        Returns:
            Updated Payment instance

        Raises:
            NotFoundException: If payment not found
            ValidationException: If transaction ID already exists
        """
        # Get payment
        payment = self.get_payment_by_id(payment_id)

        # Check transaction ID uniqueness if provided
        if transaction_id and transaction_id != payment.transaction_id:
            if self.repository.transaction_id_exists(transaction_id):
                raise AlreadyExistsException("Payment", "transaction_id", transaction_id)

        # Prepare update data
        update_data = {"status": status}

        if transaction_id:
            update_data["transaction_id"] = transaction_id
        if gateway_reference:
            update_data["gateway_reference"] = gateway_reference
        if gateway_name:
            update_data["gateway_name"] = gateway_name

        # Set completed_at timestamp if status is completed
        if status == "completed":
            update_data["completed_at"] = datetime.now()

        # Update payment
        updated_payment = self.repository.update(payment_id, update_data)

        return updated_payment

    def get_payments_by_user(self, user_id: int, current_user_id: int, skip: int = 0, limit: int = 100) -> List[Payment]:
        """
        Get all payments for a user.

        Args:
            user_id: User ID
            current_user_id: ID of the user making the request
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Payment instances

        Raises:
            PermissionDeniedException: If current user doesn't match user_id
        """
        # Check permission - users can only view their own payments
        self.check_ownership(user_id, current_user_id, "payments")

        return self.repository.get_payments_by_user(user_id, skip, limit)

    def get_payments_by_registration(
        self, registration_id: int, current_user_id: int
    ) -> List[Payment]:
        """
        Get all payments for a registration.

        Args:
            registration_id: Registration ID
            current_user_id: ID of the user making the request

        Returns:
            List of Payment instances

        Raises:
            NotFoundException: If registration not found
            PermissionDeniedException: If user doesn't own the registration
        """
        # Get registration
        registration = self.registration_repository.get_by_id(registration_id)
        if not registration:
            raise NotFoundException("Registration", registration_id)

        # Check ownership
        self.check_ownership(registration.user_id, current_user_id, "registration")

        return self.repository.get_payments_by_registration(registration_id)
