"""
Webhook API Endpoints for Payment Gateway Integrations
"""
import logging
import hmac
import hashlib
from typing import Dict, Any
from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.enums import PaymentStatus, RegistrationStatus
from app.modules.payments import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


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

        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"Error verifying Razorpay signature: {str(e)}")
        return False


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Handle Razorpay webhook events.

    Razorpay sends webhooks for various payment events:
    - payment.authorized: Payment authorized but not captured
    - payment.captured: Payment successfully captured
    - payment.failed: Payment failed
    - order.paid: Order fully paid

    **Security**: Verifies webhook signature before processing

    **Idempotency**: Uses payment_id to prevent duplicate processing

    Returns:
        200: Webhook processed successfully
        400: Invalid signature or payload
        500: Internal error (but still returns 200 to Razorpay)
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

    # Verify signature - CRITICAL: Fail immediately if secret not configured
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.error("SECURITY VIOLATION: RAZORPAY_WEBHOOK_SECRET not configured!")
        logger.error("Rejecting webhook to prevent unauthorized access")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook authentication not configured"
        )

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

    event = payload.get('event')
    payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
    order_entity = payload.get('payload', {}).get('order', {}).get('entity', {})

    logger.info(f"Razorpay webhook event: {event}")

    try:
        payment_service = PaymentService(db)

        if event in ['payment.captured', 'payment.authorized']:
            # Payment successful
            order_id = payment_entity.get('order_id')
            payment_id = payment_entity.get('id')
            amount = payment_entity.get('amount', 0) / 100  # Convert paise to rupees

            if not order_id or not payment_id:
                logger.error(f"Missing order_id or payment_id in webhook payload")
                return {"status": "error", "message": "Missing required fields"}

            logger.info(f"Processing successful payment: {payment_id} for order: {order_id}")

            # Find payment by razorpay_order_id
            payment = payment_service.repository.get_by_razorpay_order_id(order_id)

            if not payment:
                logger.warning(f"Payment not found for order_id: {order_id}")
                return {"status": "ok", "message": "Payment not found"}

            # Check if already processed (idempotency)
            if payment.status == PaymentStatus.COMPLETED.value:
                logger.info(f"Payment {payment.id} already processed, skipping")
                return {"status": "ok", "message": "Already processed"}

            # Update payment with Razorpay payment_id and complete status
            from datetime import datetime
            payment_service.repository.update(payment.id, {
                "razorpay_payment_id": payment_id,
                "gateway_payment_id": payment_id,
                "transaction_id": payment_id,
                "status": PaymentStatus.COMPLETED.value,
                "completed_at": datetime.now()
            })

            # Get registration
            registration = payment_service.registration_repository.get_by_id(payment.registration_id)

            # Record successful payment in registration tracking fields
            registration.record_successful_payment(float(payment.amount))
            db.commit()

            # Handle tier-based payment (using same logic as verify_payment)
            if payment.tier_id:
                from app.services.tier_service import TierService
                tier_service = TierService(db)

                if not payment.is_tier_upgrade:
                    # Initial tier registration
                    payment_service.registration_repository.update(
                        payment.registration_id,
                        {"status": "confirmed", "confirmed_at": datetime.now()}
                    )

                    tier_service.increment_tier_registrations(payment.tier_id)

                    # Increment event participant count
                    from app.repositories.event_repository import EventRepository
                    event_repository = EventRepository(db)
                    event = event_repository.get_by_id(registration.event_id)
                    if event:
                        event_repository.update(
                            event.id,
                            {"current_participants": event.current_participants + 1}
                        )
                        logger.info(f"Webhook: Incremented participant count for event {event.id}")

                    logger.info(f"Webhook: Registration {payment.registration_id} confirmed with tier {payment.tier_id}")

                else:
                    # Tier upgrade - NOW update the tier counts (same as verify_payment)
                    from app.modules.registrations.domain.registration_tier import RegistrationTier
                    upgrade_entry = db.query(RegistrationTier).filter(
                        RegistrationTier.registration_id == registration.id,
                        RegistrationTier.tier_id == payment.tier_id,
                        RegistrationTier.is_upgrade == True
                    ).first()

                    if upgrade_entry and upgrade_entry.upgraded_from_tier_id:
                        old_tier_id = upgrade_entry.upgraded_from_tier_id
                        new_tier_id = payment.tier_id

                        # Update tier counts now that payment is confirmed
                        tier_service.decrement_tier_registrations(old_tier_id)
                        tier_service.increment_tier_registrations(new_tier_id)

                        # Update registration's current_tier_id to new tier
                        payment_service.registration_repository.update(
                            registration.id,
                            {
                                "current_tier_id": new_tier_id,
                                "status": "confirmed",
                                "confirmed_at": datetime.now()
                            }
                        )

                        logger.info(f"Webhook: Tier upgrade payment completed and counts updated for registration {registration.id}: tier {old_tier_id} -> {new_tier_id}")
                    else:
                        logger.warning(f"Webhook: Tier upgrade entry not found for payment {payment.id}, registration {registration.id}")
                        # Still confirm the registration
                        payment_service.registration_repository.update(
                            registration.id,
                            {"status": "confirmed", "confirmed_at": datetime.now()}
                        )

            # Handle legacy non-tier payment
            else:
                payment_service.registration_repository.update(
                    payment.registration_id,
                    {"status": "confirmed", "confirmed_at": datetime.now()}
                )

                # Increment event participant count
                from app.repositories.event_repository import EventRepository
                event_repository = EventRepository(db)
                event = event_repository.get_by_id(registration.event_id)
                if event:
                    event_repository.update(
                        event.id,
                        {"current_participants": event.current_participants + 1}
                    )
                    logger.info(f"Webhook: Incremented participant count for event {event.id}")

                logger.info(f"Webhook: Registration {payment.registration_id} confirmed")

            return {"status": "ok", "message": "Payment processed"}

        elif event == 'payment.failed':
            # Payment failed
            order_id = payment_entity.get('order_id')
            payment_id = payment_entity.get('id')
            error_description = payment_entity.get('error_description', 'Payment failed')

            logger.warning(f"Payment failed: {payment_id} for order: {order_id} - {error_description}")

            if order_id:
                payment = payment_service.repository.get_by_razorpay_order_id(order_id)
                if payment:
                    payment_service.repository.update(payment.id, {
                        "razorpay_payment_id": payment_id,
                        "status": "failed"
                    })

            return {"status": "ok", "message": "Payment failure recorded"}

        else:
            # Other events (log but don't process)
            logger.info(f"Unhandled webhook event: {event}")
            return {"status": "ok", "message": "Event noted"}

    except Exception as e:
        logger.error(f"Error processing Razorpay webhook: {str(e)}", exc_info=True)
        # Return 200 to prevent Razorpay from retrying
        return {"status": "error", "message": str(e)}
