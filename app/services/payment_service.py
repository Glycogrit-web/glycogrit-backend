"""
Payment service for business logic.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
import logging

from app.models.payment import Payment
from app.repositories.payment_repository import PaymentRepository
from app.repositories.registration_repository import RegistrationRepository
from app.services.base import BaseService
from app.services.payment_gateway import get_payment_gateway
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    PermissionDeniedException,
    ValidationException
)

logger = logging.getLogger(__name__)


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

    def create_payment_order(
        self,
        registration_id: int,
        user_id: int,
        notes: Optional[Dict[str, Any]] = None,
        gateway: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a payment order for a registration using any payment gateway.

        Args:
            registration_id: Registration ID
            user_id: User ID making the payment
            notes: Additional notes/metadata
            gateway: Payment gateway to use ('razorpay', 'stripe', etc.). Uses default if None.

        Returns:
            Dict with order details and payment instance

        Raises:
            NotFoundException: If registration not found
            PermissionDeniedException: If user doesn't own the registration
            ValidationException: If payment already completed or order creation fails
        """
        # Get payment gateway instance
        payment_gateway = get_payment_gateway(gateway)
        gateway_name = payment_gateway.get_gateway_name()
        # Get registration with event details
        registration = self.registration_repository.get_by_id(registration_id)
        if not registration:
            raise NotFoundException("Registration", registration_id)

        # Check ownership
        self.check_ownership(registration.user_id, user_id, "registration")

        # Check if payment already completed
        existing_payments = self.repository.get_payments_by_registration(registration_id)
        for payment in existing_payments:
            if payment.status == "completed":
                raise ValidationException("Payment already completed for this registration")

        # Get amount from event or event category
        amount = Decimal("0")
        if registration.event_category_id and registration.category:
            amount = registration.category.registration_fee or Decimal("0")
        elif registration.event:
            amount = registration.event.registration_fee or Decimal("0")

        if amount <= 0:
            raise ValidationException("Registration fee not set for this event")

        # Create receipt ID
        receipt = f"reg_{registration_id}_user_{user_id}"

        # Add registration details to notes
        if notes is None:
            notes = {}
        notes.update({
            "registration_id": registration_id,
            "user_id": user_id,
            "event_id": registration.event_id
        })

        # Create payment order through gateway
        gateway_order = payment_gateway.create_order(
            amount=amount,
            currency="INR",
            receipt=receipt,
            notes=notes
        )

        # Normalize gateway response
        normalized_order = payment_gateway.normalize_order_response(gateway_order)

        # Create payment record
        payment_data = {
            "user_id": user_id,
            "registration_id": registration_id,
            "amount": amount,
            "currency": "INR",
            "payment_method": gateway_name,
            "status": "pending",
            "gateway_name": gateway_name,
            "gateway_order_id": normalized_order["order_id"],
            # Keep Razorpay-specific fields for backward compatibility
            "razorpay_order_id": normalized_order["order_id"] if gateway_name == "razorpay" else None
        }

        payment = self.repository.create(payment_data)
        logger.info(f"{gateway_name.title()} order created: {normalized_order['order_id']} for registration: {registration_id}")

        return {
            "order_id": normalized_order["order_id"],
            "amount": normalized_order["amount"],
            "currency": normalized_order["currency"],
            "gateway": gateway_name,
            "payment": payment
        }

    def verify_payment(
        self,
        order_id: str,
        payment_id: str,
        signature: str,
        user_id: int,
        gateway: Optional[str] = None
    ) -> Payment:
        """
        Verify and complete a payment using any payment gateway.

        Args:
            order_id: Gateway order ID
            payment_id: Gateway payment ID
            signature: Payment signature
            user_id: User ID making the payment
            gateway: Payment gateway used (auto-detected if None)

        Returns:
            Updated Payment instance

        Raises:
            NotFoundException: If payment not found
            ValidationException: If signature verification fails
            PermissionDeniedException: If user doesn't own the payment
        """
        # Find payment by gateway order ID
        payment = self.repository.get_by_gateway_order_id(order_id)
        if not payment:
            raise NotFoundException("Payment", f"order_id: {order_id}")

        # Check ownership
        self.check_ownership(payment.user_id, user_id, "payment")

        # Get payment gateway instance (use same gateway as the payment was created with)
        if gateway is None:
            gateway = payment.gateway_name or "razorpay"

        payment_gateway = get_payment_gateway(gateway)

        # Verify signature
        is_valid = payment_gateway.verify_payment_signature(
            order_id=order_id,
            payment_id=payment_id,
            signature=signature
        )

        if not is_valid:
            # Update payment status to failed
            self.repository.update(payment.id, {"status": "failed"})
            raise ValidationException("Invalid payment signature")

        # Update payment with gateway details
        update_data = {
            "status": "completed",
            "gateway_payment_id": payment_id,
            "gateway_signature": signature,
            "transaction_id": payment_id,
            "completed_at": datetime.now(),
            # Keep Razorpay-specific fields for backward compatibility
            "razorpay_payment_id": payment_id if gateway == "razorpay" else None,
            "razorpay_signature": signature if gateway == "razorpay" else None
        }

        updated_payment = self.repository.update(payment.id, update_data)

        # Update registration status to confirmed
        registration = self.registration_repository.update(
            updated_payment.registration_id,
            {"status": "confirmed", "confirmed_at": datetime.now()}
        )

        # Increment event participant count
        from app.repositories.event_repository import EventRepository
        event_repository = EventRepository(self.db)
        event = event_repository.get_by_id(registration.event_id)
        if event:
            event_repository.update(
                event.id,
                {"current_participants": event.current_participants + 1}
            )
            logger.info(f"Incremented participant count for event {event.id}: {event.current_participants} -> {event.current_participants + 1}")

        logger.info(f"Payment verified and completed: {payment.id} for order: {order_id}")

        return updated_payment

    def create_refund(
        self,
        payment_id: int,
        user_id: int,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None
    ) -> Payment:
        """
        Create a refund for a payment.

        Args:
            payment_id: Payment ID to refund
            user_id: User ID requesting refund
            amount: Amount to refund (None for full refund)
            reason: Reason for refund
            notes: Additional notes

        Returns:
            Updated Payment instance with refund details

        Raises:
            NotFoundException: If payment not found
            ValidationException: If payment cannot be refunded
            PermissionDeniedException: If user doesn't own the payment
        """
        # Get payment
        payment = self.get_payment_by_id(payment_id)

        # Check ownership
        self.check_ownership(payment.user_id, user_id, "payment")

        # Validate payment status
        if payment.status != "completed":
            raise ValidationException("Only completed payments can be refunded")

        if payment.refund_status == "processed":
            raise ValidationException("Payment already refunded")

        # Validate amount
        if amount and amount > payment.amount:
            raise ValidationException("Refund amount cannot exceed payment amount")

        # Add reason to notes
        if notes is None:
            notes = {}
        if reason:
            notes["reason"] = reason

        # Get payment gateway
        gateway = payment.gateway_name or "razorpay"
        payment_gateway = get_payment_gateway(gateway)

        # Create refund via gateway
        gateway_payment_id = payment.gateway_payment_id or payment.razorpay_payment_id
        if not gateway_payment_id:
            raise ValidationException(f"Cannot refund: {gateway} payment ID not found")

        refund = payment_gateway.create_refund(
            payment_id=gateway_payment_id,
            amount=amount,
            notes=notes
        )

        if not refund:
            raise ValidationException("Failed to create refund")

        # Normalize refund response
        normalized_refund = payment_gateway.normalize_refund_response(refund)

        # Update payment with refund details
        update_data = {
            "refund_id": normalized_refund["refund_id"],
            "refund_amount": Decimal(normalized_refund["amount"]) / 100,  # Convert from smallest unit
            "refund_status": "processed",
            "refunded_at": datetime.now(),
            "status": "refunded"
        }

        updated_payment = self.repository.update(payment_id, update_data)

        # Update registration status to cancelled
        self.registration_repository.update(
            payment.registration_id,
            {"status": "cancelled"}
        )

        logger.info(f"Refund created: {refund['id']} for payment: {payment_id}")

        return updated_payment
