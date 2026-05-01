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
from app.services.payment_service import PaymentService

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

    # Verify signature
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.error("RAZORPAY_WEBHOOK_SECRET not configured")
        # Still return 200 to prevent webhook retries
        return {"status": "error", "message": "Webhook secret not configured"}

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
            if payment.status == "completed":
                logger.info(f"Payment {payment.id} already processed, skipping")
                return {"status": "ok", "message": "Already processed"}

            # Update payment with Razorpay payment_id
            payment_service.repository.update(payment.id, {
                "razorpay_payment_id": payment_id,
                "status": "completed"
            })

            # Confirm registration
            if payment.registration:
                from app.services.registration_service import RegistrationService
                registration_service = RegistrationService(db)

                try:
                    registration_service.confirm_registration(payment.registration_id)
                    logger.info(f"Registration {payment.registration_id} confirmed via webhook")
                except Exception as e:
                    logger.error(f"Failed to confirm registration: {str(e)}")
                    # Don't fail the webhook - payment is still successful

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
