"""
Payment service for business logic.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import PaymentStatus, RefundStatus
from app.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
    ValidationException,
)
from app.modules.payments.domain.payment import Payment
from app.modules.payments.repositories.payment_repository import PaymentRepository
from app.modules.registrations.repositories.registration_repository import RegistrationRepository
from app.services.base import BaseService
from app.modules.payments.services.payment_gateway import get_payment_gateway

logger = logging.getLogger(__name__)


def validate_payment_amount(
    expected_amount: Decimal, received_amount: Decimal, tolerance: Decimal = Decimal("0.01")
) -> bool:
    """
    Validate payment amount with tolerance.

    Prevents fraud where attacker manipulates webhook amount.
    Allows small differences due to payment gateway rounding.

    Args:
        expected_amount: Amount stored in database
        received_amount: Amount reported in webhook/verification
        tolerance: Maximum allowed difference (default: 1 paisa/cent)

    Returns:
        True if amounts match within tolerance, False otherwise

    Examples:
        >>> validate_payment_amount(Decimal("500.00"), Decimal("500.00"))
        True
        >>> validate_payment_amount(Decimal("500.00"), Decimal("500.01"))
        True
        >>> validate_payment_amount(Decimal("500.00"), Decimal("501.00"))
        False
        >>> validate_payment_amount(Decimal("500.00"), Decimal("-500.00"))
        False
    """
    # Reject negative amounts
    if received_amount < 0 or expected_amount < 0:
        return False

    # Calculate absolute difference
    difference = abs(expected_amount - received_amount)

    # Check if difference is within tolerance
    return difference <= tolerance


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
        currency: str = "INR",
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
            "status": PaymentStatus.PENDING.value,
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
        transaction_id: str | None = None,
        gateway_reference: str | None = None,
        gateway_name: str | None = None,
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
        if status == PaymentStatus.COMPLETED.value:
            update_data["completed_at"] = datetime.now()

        # Update payment
        updated_payment = self.repository.update(payment_id, update_data)

        return updated_payment

    def get_payments_by_user(
        self, user_id: int, current_user_id: int, skip: int = 0, limit: int = 100
    ) -> list[Payment]:
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
    ) -> list[Payment]:
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
        amount: Decimal | None = None,
        currency: str = "INR",
        user_id: int | None = None,
        tier_id: int | None = None,
        is_tier_upgrade: bool = False,
        notes: dict[str, Any] | None = None,
        gateway: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a payment order for a registration using any payment gateway.

        Args:
            registration_id: Registration ID
            amount: Payment amount (if None, fetches from event/tier)
            currency: Currency code (default: INR)
            user_id: User ID making the payment (if None, uses registration.user_id)
            tier_id: Optional tier ID for tier-based payment
            is_tier_upgrade: Whether this is a tier upgrade payment
            notes: Additional notes/metadata
            gateway: Payment gateway to use ('razorpay', 'stripe', etc.). Uses default if None.

        Returns:
            Dict with order details and payment instance

        Raises:
            NotFoundException: If registration not found
            PermissionDeniedException: If user doesn't own the registration
            ValidationException: If payment already completed or order creation fails
        """
        # Get registration with event details
        registration = self.registration_repository.get_by_id(registration_id)
        if not registration:
            raise NotFoundException("Registration", registration_id)

        # Use registration's user_id if user_id not provided
        if user_id is None:
            user_id = registration.user_id

        # Check ownership
        self.check_ownership(registration.user_id, user_id, "registration")

        # Check if payment already exists
        if not is_tier_upgrade:
            existing_payments = self.repository.get_payments_by_registration(registration_id)
            for payment in existing_payments:
                # Don't allow duplicate payments for same registration
                if payment.status == PaymentStatus.COMPLETED.value and not payment.is_tier_upgrade:
                    raise ValidationException("Payment already completed for this registration")
                # If there's already a pending payment, return existing order instead of creating new one
                if payment.status == PaymentStatus.PENDING.value and not payment.is_tier_upgrade:
                    logger.info(
                        f"Found existing pending payment {payment.id} for registration {registration_id}, returning existing order"
                    )
                    return {
                        "id": payment.id,
                        "order_id": payment.razorpay_order_id or payment.gateway_order_id,
                        "amount": int(payment.amount * 100),  # Convert to paise
                        "currency": payment.currency,
                        "gateway": payment.gateway_name or gateway,
                    }

        # Get amount
        if amount is None:
            # If tier_id provided, get amount from tier
            if tier_id:
                from app.modules.registrations.domain.event_registration_tier import (
                    EventRegistrationTier,
                )

                tier = (
                    self.db.query(EventRegistrationTier)
                    .filter(EventRegistrationTier.id == tier_id)
                    .first()
                )
                if not tier:
                    raise NotFoundException("Tier", tier_id)
                amount = tier.price
                currency = tier.currency
            # Otherwise, get from event or event activity
            elif registration.event_activity_id and registration.activity:
                amount = registration.activity.registration_fee or Decimal("0")
            elif registration.event:
                amount = registration.event.registration_fee or Decimal("0")
            else:
                amount = Decimal("0")

        if amount <= 0:
            raise ValidationException("Payment amount must be greater than 0")

        # Create receipt ID
        receipt = f"reg_{registration_id}_user_{user_id}"
        if is_tier_upgrade:
            receipt += "_upgrade"

        # Add registration details to notes
        if notes is None:
            notes = {}
        notes.update(
            {
                "registration_id": registration_id,
                "user_id": user_id,
                "event_id": registration.event_id,
            }
        )
        if tier_id:
            notes["tier_id"] = tier_id
        if is_tier_upgrade:
            notes["is_tier_upgrade"] = True

        # Create payment gateway instance (deferred until all validations pass)
        payment_gateway = get_payment_gateway(gateway)
        gateway_name = payment_gateway.get_gateway_name()

        # Create payment order through gateway
        gateway_order = payment_gateway.create_order(
            amount=amount, currency=currency, receipt=receipt, notes=notes
        )

        # Normalize gateway response
        normalized_order = payment_gateway.normalize_order_response(gateway_order)

        # Create payment record
        payment_data = {
            "user_id": user_id,
            "registration_id": registration_id,
            "amount": amount,
            "currency": currency,
            "payment_method": gateway_name,
            "status": PaymentStatus.PENDING.value,
            "gateway_name": gateway_name,
            "gateway_order_id": normalized_order["order_id"],
            "tier_id": tier_id,
            "is_tier_upgrade": is_tier_upgrade,
            # Keep Razorpay-specific fields for backward compatibility
            "razorpay_order_id": (
                normalized_order["order_id"] if gateway_name == "razorpay" else None
            ),
        }

        payment = self.repository.create(payment_data)
        logger.info(
            f"{gateway_name.title()} order created: {normalized_order['order_id']} for registration: {registration_id} (tier_upgrade={is_tier_upgrade})"
        )

        return {
            "id": payment.id,
            "order_id": normalized_order["order_id"],
            "amount": normalized_order["amount"],
            "currency": normalized_order["currency"],
            "gateway": gateway_name,
            "payment": payment,
        }

    def verify_payment(
        self,
        order_id: str,
        payment_id: str,
        signature: str,
        user_id: int,
        gateway: str | None = None,
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
        # P2, P12 Fix: Find payment with row-level locking to prevent race conditions
        from app.modules.payments.domain.payment import Payment as PaymentModel

        payment = (
            self.db.query(PaymentModel)
            .filter(PaymentModel.gateway_order_id == order_id)
            .with_for_update()
            .first()
        )

        if not payment:
            # Try legacy razorpay_order_id field
            payment = (
                self.db.query(PaymentModel)
                .filter(PaymentModel.razorpay_order_id == order_id)
                .with_for_update()
                .first()
            )

        if not payment:
            raise NotFoundException("Payment", f"order_id: {order_id}")

        # Check ownership
        self.check_ownership(payment.user_id, user_id, "payment")

        # P12 Fix: Check if already completed (idempotency with lock held)
        if payment.status == PaymentStatus.COMPLETED.value:
            logger.info(f"Payment {payment.id} already completed (idempotent call)")
            return payment

        # Get payment gateway instance (use same gateway as the payment was created with)
        if gateway is None:
            gateway = payment.gateway_name or "razorpay"

        payment_gateway = get_payment_gateway(gateway)

        # Verify signature
        is_valid = payment_gateway.verify_payment_signature(
            order_id=order_id, payment_id=payment_id, signature=signature
        )

        if not is_valid:
            # Update payment status to failed
            self.repository.update(payment.id, {"status": PaymentStatus.FAILED.value})
            raise ValidationException("Invalid payment signature")

        # Update payment with gateway details
        update_data = {
            "status": PaymentStatus.COMPLETED.value,
            "gateway_payment_id": payment_id,
            "gateway_signature": signature,
            "transaction_id": payment_id,
            "completed_at": datetime.now(),
            # Keep Razorpay-specific fields for backward compatibility
            "razorpay_payment_id": payment_id if gateway == "razorpay" else None,
            "razorpay_signature": signature if gateway == "razorpay" else None,
        }

        updated_payment = self.repository.update(payment.id, update_data)

        # Get registration
        registration = self.registration_repository.get_by_id(updated_payment.registration_id)

        # Record successful payment in registration tracking fields
        registration.record_successful_payment(float(updated_payment.amount))
        self.db.commit()

        # Handle tier-based payment
        if updated_payment.tier_id:
            # If this is NOT a tier upgrade, update registration status and increment counts
            if not updated_payment.is_tier_upgrade:
                # Update registration status to confirmed
                registration = self.registration_repository.update(
                    updated_payment.registration_id,
                    {"status": "confirmed", "confirmed_at": datetime.now()},
                )

                # CRITICAL FIX: Create ActivityProgress for paid tier after payment confirmation
                # This should have been created during registration but was skipped for PENDING status
                if registration.event_activity_id and not registration.activity_progress:
                    from app.models.activity_progress import ActivityProgress
                    from app.modules.events.domain.event import EventActivity
                    from decimal import Decimal

                    activity = self.db.query(EventActivity).filter(
                        EventActivity.id == registration.event_activity_id
                    ).first()

                    if activity and activity.distance:
                        activity_progress = ActivityProgress(
                            user_id=registration.user_id,
                            registration_id=registration.id,
                            event_id=registration.event_id,
                            activity_id=registration.event_activity_id,
                            target_distance=activity.distance,
                            distance_completed=Decimal("0.00"),
                        )
                        self.db.add(activity_progress)
                        self.db.commit()
                        logger.info(
                            f"Created ActivityProgress for registration {registration.id} after payment confirmation (target: {activity.distance} km)"
                        )

                # Increment tier registration count (with atomic capacity check)
                from app.modules.registrations.services.tier_service import TierService

                tier_service = TierService(self.db)
                try:
                    tier_service.increment_tier_registrations(
                        updated_payment.tier_id, with_capacity_check=True
                    )
                except Exception as e:
                    # If capacity check fails AFTER payment, this is a race condition
                    # Log error but don't fail payment - handle manually
                    logger.error(
                        f"Tier capacity exceeded after payment verification for tier {updated_payment.tier_id}: {str(e)}"
                    )
                    # Payment is still completed, but tier count may be over limit
                    # This should trigger manual review

                # Increment event participant count
                from app.modules.events.repositories.event_repository import EventRepository

                event_repository = EventRepository(self.db)
                event = event_repository.get_by_id(registration.event_id)
                if event:
                    event_repository.update(
                        event.id, {"current_participants": event.current_participants + 1}
                    )
                    logger.info(
                        f"Incremented participant count for event {event.id}: {event.current_participants} -> {event.current_participants + 1}"
                    )
            # If it's a tier upgrade, NOW update the tier counts (AFTER payment verified)
            # This fixes the critical bug where counts were updated before payment completion
            else:
                # Get the tier upgrade details to find old and new tiers
                from app.modules.registrations.domain.registration_tier import RegistrationTier

                upgrade_entry = (
                    self.db.query(RegistrationTier)
                    .filter(
                        RegistrationTier.registration_id == registration.id,
                        RegistrationTier.tier_id == updated_payment.tier_id,
                        RegistrationTier.is_upgrade,
                    )
                    .first()
                )

                if upgrade_entry and upgrade_entry.upgraded_from_tier_id:
                    # Update tier counts now that payment is confirmed
                    from app.modules.registrations.services.tier_service import TierService

                    tier_service = TierService(self.db)

                    old_tier_id = upgrade_entry.upgraded_from_tier_id
                    new_tier_id = updated_payment.tier_id

                    # Decrement old tier, confirm new tier reservation (convert to registration)
                    tier_service.decrement_tier_registrations(old_tier_id)
                    try:
                        tier_service.confirm_tier_reservation(new_tier_id)
                        logger.info(f"Confirmed tier reservation for payment {updated_payment.id}")
                    except Exception as e:
                        # Should not happen since capacity was reserved, but handle gracefully
                        logger.error(
                            f"Failed to confirm tier reservation for tier {new_tier_id}: {str(e)}"
                        )
                        # Revert old tier decrement
                        tier_service.increment_tier_registrations(old_tier_id)
                        # Release the reservation that couldn't be confirmed
                        tier_service.release_tier_reservation(new_tier_id)
                        # Keep registration in old tier
                        self.registration_repository.update(
                            registration.id, {"status": "confirmed", "confirmed_at": datetime.now()}
                        )
                        logger.warning(f"Tier upgrade reverted for registration {registration.id}")
                        return updated_payment

                    # Update registration's current_tier_id to new tier
                    self.registration_repository.update(
                        registration.id,
                        {
                            "current_tier_id": new_tier_id,
                            "status": "confirmed",
                            "confirmed_at": datetime.now(),
                        },
                    )

                    logger.info(
                        f"Tier upgrade payment completed and counts updated for registration {registration.id}: tier {old_tier_id} -> {new_tier_id}"
                    )
                else:
                    logger.warning(
                        f"Tier upgrade entry not found for payment {updated_payment.id}, registration {registration.id}"
                    )
                    # Still confirm the registration
                    self.registration_repository.update(
                        registration.id, {"status": "confirmed", "confirmed_at": datetime.now()}
                    )

        # Handle legacy non-tier payment
        else:
            # Update registration status to confirmed
            registration = self.registration_repository.update(
                updated_payment.registration_id,
                {"status": "confirmed", "confirmed_at": datetime.now()},
            )

            # Increment event participant count
            from app.modules.events.repositories.event_repository import EventRepository

            event_repository = EventRepository(self.db)
            event = event_repository.get_by_id(registration.event_id)
            if event:
                event_repository.update(
                    event.id, {"current_participants": event.current_participants + 1}
                )
                logger.info(
                    f"Incremented participant count for event {event.id}: {event.current_participants} -> {event.current_participants + 1}"
                )

        logger.info(f"Payment verified and completed: {payment.id} for order: {order_id}")

        return updated_payment

    def create_refund(
        self,
        payment_id: int,
        user_id: int,
        amount: Decimal | None = None,
        reason: str | None = None,
        notes: dict[str, Any] | None = None,
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
        if payment.status != PaymentStatus.COMPLETED.value:
            raise ValidationException("Only completed payments can be refunded")

        if payment.refund_status == RefundStatus.PROCESSED.value:
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
            payment_id=gateway_payment_id, amount=amount, notes=notes
        )

        if not refund:
            raise ValidationException("Failed to create refund")

        # Normalize refund response
        normalized_refund = payment_gateway.normalize_refund_response(refund)

        # Update payment with refund details
        update_data = {
            "refund_id": normalized_refund["refund_id"],
            "refund_amount": Decimal(normalized_refund["amount"])
            / 100,  # Convert from smallest unit
            "refund_status": RefundStatus.PROCESSED.value,
            "refunded_at": datetime.now(),
            "status": PaymentStatus.REFUNDED.value,
        }

        updated_payment = self.repository.update(payment_id, update_data)

        # Get registration to check if we need to update tier counts
        registration = self.registration_repository.get_by_id(payment.registration_id)

        # Handle tier count updates for refunds
        if payment.tier_id:
            from app.modules.registrations.services.tier_service import TierService

            tier_service = TierService(self.db)

            if payment.is_tier_upgrade:
                # Tier upgrade refund: Revert tier changes
                # Decrement new tier count, increment old tier count
                from app.modules.registrations.domain.registration_tier import RegistrationTier

                upgrade_entry = (
                    self.db.query(RegistrationTier)
                    .filter(
                        RegistrationTier.registration_id == registration.id,
                        RegistrationTier.tier_id == payment.tier_id,
                        RegistrationTier.is_upgrade,
                    )
                    .first()
                )

                if upgrade_entry and upgrade_entry.upgraded_from_tier_id:
                    # Revert tier counts
                    tier_service.decrement_tier_registrations(payment.tier_id)  # Decrement new tier
                    tier_service.increment_tier_registrations(
                        upgrade_entry.upgraded_from_tier_id
                    )  # Increment old tier

                    # Revert registration back to old tier
                    self.registration_repository.update(
                        registration.id,
                        {
                            "current_tier_id": upgrade_entry.upgraded_from_tier_id,
                            "status": "confirmed",  # Keep confirmed, just downgrade tier
                        },
                    )
                    logger.info(
                        f"Reverted tier upgrade for refunded payment {payment_id}: tier {payment.tier_id} -> {upgrade_entry.upgraded_from_tier_id}"
                    )
                else:
                    # No upgrade entry found, just cancel registration
                    self.registration_repository.update(
                        payment.registration_id, {"status": "cancelled"}
                    )
                    tier_service.decrement_tier_registrations(payment.tier_id)
            else:
                # Initial tier registration refund: Cancel registration and decrement tier count
                self.registration_repository.update(
                    payment.registration_id, {"status": "cancelled"}
                )
                tier_service.decrement_tier_registrations(payment.tier_id)

                # Also decrement event participant count
                from app.modules.events.repositories.event_repository import EventRepository

                event_repository = EventRepository(self.db)
                event = event_repository.get_by_id(registration.event_id)
                if event and event.current_participants > 0:
                    event_repository.update(
                        event.id, {"current_participants": event.current_participants - 1}
                    )
                    logger.info(f"Decremented participant count for event {event.id} due to refund")
        else:
            # Legacy non-tier refund: Just cancel registration and decrement event count
            self.registration_repository.update(payment.registration_id, {"status": "cancelled"})

            from app.modules.events.repositories.event_repository import EventRepository

            event_repository = EventRepository(self.db)
            event = event_repository.get_by_id(registration.event_id)
            if event and event.current_participants > 0:
                event_repository.update(
                    event.id, {"current_participants": event.current_participants - 1}
                )
                logger.info(f"Decremented participant count for event {event.id} due to refund")

        logger.info(f"Refund created: {refund['id']} for payment: {payment_id}")

        return updated_payment
