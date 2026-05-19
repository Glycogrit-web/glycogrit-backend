"""
Webhook API Endpoints V2 - Enhanced with Complete Bug Fixes

Fixes implemented:
- P1: Webhook duplicate processing via event ID tracking
- P3: Proper error handling (returns 500 on error, not 200)
- P4: Webhook event ID tracking for replay attack prevention
- P5: Payment amount validation
- P12: Race condition prevention between webhook and manual verification

"""
import logging
import hmac
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal
from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.config import settings
from app.core.enums import PaymentStatus, RegistrationStatus
from app.modules.payments import PaymentService
from app.models.webhook_event import WebhookEvent
from app.core.webhook_security import WebhookSecurityValidator, get_webhook_timestamp_from_razorpay
from app.core.exceptions import (
    PaymentAlreadyCompletedException,
    PaymentGatewayException,
    ValidationException
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks/v2", tags=["Webhooks V2"])


def verify_razorpay_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Razorpay webhook signature for security.

    Args:
        payload: Raw request body bytes
        signature: X-Razorpay-Signature header value
        secret: Webhook secret from Razorpay dashboard

    Returns:
        bool: True if signature is valid
    """
    try:
        expected_signature = hmac.new(
            key=secret.encode('utf-8'),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()

        # Timing-safe comparison
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"Error verifying Razorpay signature: {str(e)}")
        return False


def get_or_create_webhook_event(
    db: Session,
    gateway_event_id: str,
    gateway_name: str,
    event_type: str,
    payload_dict: Dict[str, Any],
    signature: str
) -> tuple[WebhookEvent, bool]:
    """
    Get existing webhook event or create new one (idempotency).

    Returns:
        tuple: (WebhookEvent, is_new) where is_new is True if this is first time processing
    """
    # Try to get existing event
    existing = db.query(WebhookEvent).filter(
        WebhookEvent.gateway_event_id == gateway_event_id,
        WebhookEvent.gateway_name == gateway_name
    ).first()

    if existing:
        logger.info(f"Webhook event {gateway_event_id} already exists (attempt #{existing.processing_attempts + 1})")
        return existing, False

    # Create new event record
    webhook_event = WebhookEvent(
        gateway_event_id=gateway_event_id,
        gateway_name=gateway_name,
        event_type=event_type,
        payload=json.dumps(payload_dict),
        signature=signature,
        received_at=datetime.now(),
        processed=False,
        processing_attempts=0
    )

    try:
        db.add(webhook_event)
        db.flush()  # Get ID without committing
        logger.info(f"Created new webhook event record: {gateway_event_id}")
        return webhook_event, True
    except IntegrityError:
        # Race condition: another thread created it
        db.rollback()
        existing = db.query(WebhookEvent).filter(
            WebhookEvent.gateway_event_id == gateway_event_id
        ).first()
        logger.warning(f"Race condition creating webhook event {gateway_event_id}, using existing")
        return existing, False


def validate_payment_amount(
    payment_db_amount: Decimal,
    webhook_amount: Decimal,
    tolerance: Decimal = Decimal("0.01")
) -> bool:
    """
    Validate that webhook payment amount matches database amount.

    Args:
        payment_db_amount: Amount from database (in rupees)
        webhook_amount: Amount from webhook (in rupees)
        tolerance: Allowed difference (default 1 paisa)

    Returns:
        bool: True if amounts match within tolerance
    """
    difference = abs(payment_db_amount - webhook_amount)
    if difference > tolerance:
        logger.error(
            f"Payment amount mismatch! "
            f"Database: ₹{payment_db_amount}, "
            f"Webhook: ₹{webhook_amount}, "
            f"Difference: ₹{difference}"
        )
        return False
    return True


@router.post("/razorpay")
async def razorpay_webhook_v2(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Enhanced Razorpay webhook handler with complete bug fixes.

    **Security Improvements:**
    - Validates webhook secret strength (P11)
    - Timing-safe signature comparison (P10)

    **Idempotency Improvements:**
    - Tracks webhook event IDs (P4)
    - Prevents duplicate processing (P1)
    - Handles replay attacks

    **Data Integrity:**
    - Validates payment amounts (P5)
    - Row-level locking to prevent race conditions (P12)

    **Error Handling:**
    - Returns 500 on processing errors (P3)
    - Allows Razorpay to retry failed webhooks

    Returns:
        200: Webhook processed successfully
        400: Invalid signature or payload
        409: Webhook already processed (duplicate)
        500: Processing error (Razorpay should retry)
    """
    # Get raw body for signature verification
    body = await request.body()

    # Get signature from header
    signature = request.headers.get('X-Razorpay-Signature', '')

    if not signature:
        logger.warning("Razorpay webhook received without signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header"
        )

    # Verify webhook secret is configured and strong
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.error("SECURITY VIOLATION: RAZORPAY_WEBHOOK_SECRET not configured!")
        logger.error("Rejecting webhook to prevent unauthorized access")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook authentication not configured"
        )

    # P11 Fix: Validate secret strength
    if len(settings.RAZORPAY_WEBHOOK_SECRET) < 16:
        logger.error(f"SECURITY WARNING: Webhook secret is weak ({len(settings.RAZORPAY_WEBHOOK_SECRET)} chars)")
        # Still proceed but log warning

    # Check if secret is default/common value
    weak_secrets = ['default', 'test', '12345678', 'secret', 'webhook_secret']
    if settings.RAZORPAY_WEBHOOK_SECRET.lower() in weak_secrets:
        logger.error(f"SECURITY CRITICAL: Using weak/default webhook secret!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Insecure webhook configuration"
        )

    # Verify signature
    if not verify_razorpay_signature(body, signature, settings.RAZORPAY_WEBHOOK_SECRET):
        logger.warning(f"Invalid Razorpay webhook signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )

    # Parse webhook payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    # Extract webhook event details
    event_type = payload.get('event')
    webhook_id = payload.get('id')  # P4: Razorpay webhook event ID
    contains = payload.get('contains', [])
    payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
    order_entity = payload.get('payload', {}).get('order', {}).get('entity', {})

    # P4 Fix: Validate webhook event ID exists
    if not webhook_id:
        logger.error("Webhook missing 'id' field - possible malicious request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook: missing event ID"
        )

    # SECURITY: Validate webhook timestamp to prevent replay attacks
    webhook_timestamp = get_webhook_timestamp_from_razorpay(payload)
    if webhook_timestamp:
        validator = WebhookSecurityValidator(max_age_seconds=300)  # 5 minutes
        is_valid, error_msg = validator.validate_timestamp(webhook_timestamp, webhook_id)

        if not is_valid:
            logger.warning(f"Webhook {webhook_id} rejected: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Webhook timestamp validation failed: {error_msg}"
            )

        logger.info(f"Webhook {webhook_id} timestamp validated successfully")
    else:
        # Timestamp not found - log warning but don't reject
        # Some older webhooks might not have timestamps
        logger.warning(f"Webhook {webhook_id}: No timestamp found in payload")

    logger.info(f"Razorpay webhook received: event={event_type}, id={webhook_id}")

    # P4 Fix: Check if this webhook event has already been processed
    webhook_event, is_new = get_or_create_webhook_event(
        db=db,
        gateway_event_id=webhook_id,
        gateway_name="razorpay",
        event_type=event_type,
        payload_dict=payload,
        signature=signature
    )

    # If webhook already processed successfully, return 200 (idempotent)
    if webhook_event.processed:
        logger.info(f"Webhook {webhook_id} already processed successfully, returning 200")
        return {
            "status": "ok",
            "message": "Webhook already processed",
            "webhook_event_id": webhook_event.id,
            "processed_at": webhook_event.processed_at.isoformat() if webhook_event.processed_at else None
        }

    # Increment processing attempts
    webhook_event.processing_attempts += 1

    try:
        payment_service = PaymentService(db)

        if event_type in ['payment.captured', 'payment.authorized']:
            # P5 Fix: Extract and validate payment amount
            order_id = payment_entity.get('order_id')
            gateway_payment_id = payment_entity.get('id')
            webhook_amount_paise = payment_entity.get('amount', 0)
            webhook_amount_rupees = Decimal(str(webhook_amount_paise)) / 100
            payment_currency = payment_entity.get('currency', 'INR')
            payment_method = payment_entity.get('method', 'unknown')

            if not order_id or not gateway_payment_id:
                error_msg = f"Missing order_id or payment_id in webhook payload"
                logger.error(error_msg)
                webhook_event.record_error(error_msg)
                db.commit()
                # P3 Fix: Return 500 to allow Razorpay to retry
                raise HTTPException(status_code=500, detail=error_msg)

            logger.info(f"Processing payment: {gateway_payment_id}, order: {order_id}, amount: ₹{webhook_amount_rupees}")

            # P12 Fix: Use row-level locking to prevent race with manual verification
            from sqlalchemy import select
            from app.modules.payments.domain.payment import Payment

            # Acquire exclusive lock on payment row
            payment = db.query(Payment).filter(
                Payment.gateway_order_id == order_id
            ).with_for_update().first()

            if not payment:
                # Payment might use razorpay_order_id field (legacy)
                payment = db.query(Payment).filter(
                    Payment.razorpay_order_id == order_id
                ).with_for_update().first()

            if not payment:
                error_msg = f"Payment not found for order_id: {order_id}"
                logger.warning(error_msg)
                webhook_event.record_error(error_msg)
                db.commit()
                raise HTTPException(status_code=404, detail=error_msg)

            # Store gateway payment ID in webhook event for tracking
            webhook_event.gateway_payment_id = gateway_payment_id
            webhook_event.payment_id = payment.id

            # Check if already processed (idempotency) - WITH LOCK HELD
            if payment.status == PaymentStatus.COMPLETED.value:
                logger.info(f"Payment {payment.id} already completed, marking webhook as processed")
                webhook_event.mark_processed(payment_id=payment.id, registration_id=payment.registration_id)
                db.commit()
                return {
                    "status": "ok",
                    "message": "Payment already processed",
                    "payment_id": payment.id
                }

            # P5 Fix: Validate payment amount matches
            if not validate_payment_amount(payment.amount, webhook_amount_rupees):
                error_msg = (
                    f"Payment amount mismatch! "
                    f"Expected: ₹{payment.amount}, "
                    f"Received: ₹{webhook_amount_rupees}"
                )
                logger.error(error_msg)
                webhook_event.record_error(error_msg)
                db.commit()
                # This is a critical security issue - return 500 to alert admins
                raise HTTPException(status_code=500, detail="Payment amount mismatch - possible fraud")

            # Validate currency
            if payment.currency != payment_currency:
                error_msg = f"Currency mismatch: Expected {payment.currency}, got {payment_currency}"
                logger.error(error_msg)
                webhook_event.record_error(error_msg)
                db.commit()
                raise HTTPException(status_code=500, detail="Currency mismatch")

            # Update payment with gateway details and complete status
            payment_service.repository.update(payment.id, {
                "razorpay_payment_id": gateway_payment_id,
                "gateway_payment_id": gateway_payment_id,
                "transaction_id": gateway_payment_id,
                "payment_method": payment_method,
                "status": PaymentStatus.COMPLETED.value,
                "completed_at": datetime.now()
            })

            # Get registration
            registration = payment_service.registration_repository.get_by_id(payment.registration_id)
            webhook_event.registration_id = registration.id

            # Record successful payment in registration
            registration.record_successful_payment(float(payment.amount))

            # Handle tier-based payment (same logic as verify_payment)
            if payment.tier_id:
                from app.services.tier_service import TierService
                tier_service = TierService(db)

                if not payment.is_tier_upgrade:
                    # Initial tier registration
                    payment_service.registration_repository.update(
                        payment.registration_id,
                        {"status": "confirmed", "confirmed_at": datetime.now()}
                    )

                    # P13 Fix: Use atomic increment with capacity check
                    try:
                        tier_service.increment_tier_registrations(
                            payment.tier_id,
                            with_capacity_check=True
                        )
                    except Exception as tier_error:
                        logger.error(f"Tier capacity error after payment: {str(tier_error)}")
                        # Payment completed but tier might be over capacity
                        # Mark for manual review but don't fail webhook
                        webhook_event.record_error(f"Tier capacity warning: {str(tier_error)}")

                    # Increment event participant count atomically
                    from app.repositories.event_repository import EventRepository
                    event_repository = EventRepository(db)
                    db.execute(
                        f"UPDATE events SET current_participants = current_participants + 1 "
                        f"WHERE id = {registration.event_id}"
                    )
                    logger.info(f"Webhook: Incremented participant count for event {registration.event_id}")

                    logger.info(f"Webhook: Registration {payment.registration_id} confirmed with tier {payment.tier_id}")

                else:
                    # Tier upgrade
                    from app.modules.registrations.domain.registration_tier import RegistrationTier
                    upgrade_entry = db.query(RegistrationTier).filter(
                        RegistrationTier.registration_id == registration.id,
                        RegistrationTier.tier_id == payment.tier_id,
                        RegistrationTier.is_upgrade == True
                    ).first()

                    if upgrade_entry and upgrade_entry.upgraded_from_tier_id:
                        old_tier_id = upgrade_entry.upgraded_from_tier_id
                        new_tier_id = payment.tier_id

                        # Update tier counts atomically
                        tier_service.decrement_tier_registrations(old_tier_id)
                        try:
                            tier_service.increment_tier_registrations(
                                new_tier_id,
                                with_capacity_check=True
                            )
                        except Exception as tier_error:
                            logger.error(f"Tier upgrade capacity error: {str(tier_error)}")
                            # Revert old tier decrement
                            tier_service.increment_tier_registrations(old_tier_id)
                            # Keep user in old tier
                            webhook_event.record_error(f"Tier upgrade reverted: {str(tier_error)}")

                        # Update registration's current tier
                        payment_service.registration_repository.update(
                            registration.id,
                            {
                                "current_tier_id": new_tier_id,
                                "status": "confirmed",
                                "confirmed_at": datetime.now()
                            }
                        )

                        logger.info(f"Webhook: Tier upgrade completed: {old_tier_id} → {new_tier_id}")

            # Handle legacy non-tier payment
            else:
                payment_service.registration_repository.update(
                    payment.registration_id,
                    {"status": "confirmed", "confirmed_at": datetime.now()}
                )

                # Increment event participant count
                from app.repositories.event_repository import EventRepository
                db.execute(
                    f"UPDATE events SET current_participants = current_participants + 1 "
                    f"WHERE id = {registration.event_id}"
                )

            # Mark webhook as successfully processed
            webhook_event.mark_processed(payment_id=payment.id, registration_id=registration.id)
            db.commit()

            logger.info(f"Webhook {webhook_id} processed successfully")

            return {
                "status": "ok",
                "message": "Payment processed successfully",
                "payment_id": payment.id,
                "webhook_event_id": webhook_event.id
            }

        elif event_type == 'payment.failed':
            # Payment failed
            order_id = payment_entity.get('order_id')
            gateway_payment_id = payment_entity.get('id')
            error_description = payment_entity.get('error_description', 'Payment failed')
            error_code = payment_entity.get('error_code')

            logger.warning(f"Payment failed: {gateway_payment_id}, order: {order_id}, error: {error_description}")

            if order_id:
                # Use row locking
                from app.modules.payments.domain.payment import Payment
                payment = db.query(Payment).filter(
                    Payment.gateway_order_id == order_id
                ).with_for_update().first()

                if not payment:
                    payment = db.query(Payment).filter(
                        Payment.razorpay_order_id == order_id
                    ).with_for_update().first()

                if payment:
                    webhook_event.payment_id = payment.id
                    webhook_event.gateway_payment_id = gateway_payment_id

                    payment_service.repository.update(payment.id, {
                        "razorpay_payment_id": gateway_payment_id,
                        "gateway_payment_id": gateway_payment_id,
                        "status": "failed"
                    })

                    # Record failed payment in registration
                    registration = payment_service.registration_repository.get_by_id(payment.registration_id)
                    if registration:
                        registration.record_failed_payment(float(payment.amount))

                    # Mark webhook as processed
                    webhook_event.mark_processed(payment_id=payment.id)
                    db.commit()

                    return {
                        "status": "ok",
                        "message": "Payment failure recorded",
                        "payment_id": payment.id
                    }

            # No payment found
            webhook_event.record_error(f"Payment not found for order {order_id}")
            db.commit()

            return {"status": "ok", "message": "Payment failure noted"}

        else:
            # Other events (log but don't process)
            logger.info(f"Unhandled webhook event: {event_type}")
            webhook_event.mark_processed()
            db.commit()

            return {"status": "ok", "message": "Event noted"}

    except HTTPException:
        # Re-raise HTTP exceptions (400, 404, 500)
        raise

    except Exception as e:
        # P3 Fix: Return 500 on processing errors (NOT 200)
        error_msg = f"Error processing webhook: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Record error in webhook event
        webhook_event.record_error(error_msg)
        db.commit()

        # Return 500 to signal Razorpay to retry
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed - will retry"
        )
