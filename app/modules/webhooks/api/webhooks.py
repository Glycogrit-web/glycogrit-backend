"""
Webhook API Endpoints
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import HTTPHeaders
from app.core.database import get_db
from app.core.rate_limit import limiter  # Import rate limiter for webhook protection
from app.modules.webhooks.domain.webhook_event import WebhookSource
from app.modules.webhooks.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/razorpay", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")  # SECURITY: Rate limiting to prevent webhook flooding
async def razorpay_webhook(
    request: Request,
    response: Response,
    x_razorpay_signature: str | None = Header(None, alias=HTTPHeaders.X_RAZORPAY_SIGNATURE),
    db: Session = Depends(get_db),
):
    """
    Receive Razorpay webhook with MANDATORY signature verification.

    SECURITY ENHANCEMENTS:
    - Mandatory signature verification in production (prevents fake webhooks)
    - Rate limiting (30 requests/minute per IP)
    - Security event logging for failed verifications
    - Idempotency via webhook_events table

    Razorpay sends webhooks for payment events:
    - payment.captured
    - payment.failed
    - refund.processed
    """
    try:
        payload = await request.json()
        headers = dict(request.headers)

        service = WebhookService(db)

        # Extract event details
        event_type = payload.get("event")
        event_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id")

        if not event_id:
            event_id = payload.get("payload", {}).get("refund", {}).get("entity", {}).get("id")

        # Store webhook (always log incoming webhooks for audit trail)
        webhook = service.receive_webhook(
            source=WebhookSource.RAZORPAY,
            event_type=event_type,
            event_id=event_id or "unknown",
            payload=payload,
            headers=headers,
            signature=x_razorpay_signature,
        )

        # CRITICAL SECURITY FIX: Make signature verification MANDATORY
        if not x_razorpay_signature:
            logger.error(f"Webhook {webhook.id} rejected: Missing signature header")
            webhook.mark_failed("Missing signature")
            db.commit()

            # Log security event (will be implemented in audit logging phase)
            # This flags potential attack attempts
            client_ip = request.client.host if request.client else "unknown"
            logger.critical(
                f"SECURITY: Webhook received without signature | "
                f"webhook_id={webhook.id} event_type={event_type} ip={client_ip}"
            )

            # Return 401 for authentication failure
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature header"
            )

        # Check if webhook secret is configured
        if not hasattr(settings, "RAZORPAY_WEBHOOK_SECRET") or not settings.RAZORPAY_WEBHOOK_SECRET:
            logger.critical("RAZORPAY_WEBHOOK_SECRET not configured - webhook processing disabled!")
            webhook.mark_failed("Webhook secret not configured")
            db.commit()

            # In production, this should NEVER happen - it's a configuration error
            if settings.ENVIRONMENT == "production":
                logger.critical(
                    f"SECURITY: Webhook received but secret not configured in PRODUCTION | "
                    f"webhook_id={webhook.id} event_type={event_type}"
                )
                return {"status": "error", "reason": "configuration_error"}

            # In development, allow processing but log warning
            logger.warning("Processing webhook without verification (development mode only)")
        else:
            # Verify signature (CRITICAL SECURITY CHECK)
            is_valid = service.verify_razorpay_signature(webhook, settings.RAZORPAY_WEBHOOK_SECRET)

            if not is_valid:
                logger.error(f"Webhook {webhook.id} signature verification FAILED: {event_id}")
                webhook.mark_failed("Invalid signature")
                db.commit()

                # Log security event (potential attack or replay)
                client_ip = request.client.host if request.client else "unknown"
                logger.critical(
                    f"SECURITY: Invalid webhook signature detected | "
                    f"webhook_id={webhook.id} event_type={event_type} "
                    f"ip={client_ip} user_agent={headers.get('user-agent', 'unknown')}"
                )

                # Return 401 for authentication failure
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature"
                )

        # Signature verified successfully - process webhook
        logger.info(f"Webhook {webhook.id} signature verified, processing...")
        service.process_webhook(webhook.id)

        return {"status": "ok"}

    except HTTPException:
        # Re-raise HTTPExceptions (authentication/validation errors)
        raise
    except Exception as e:
        logger.error(f"Razorpay webhook error: {str(e)}", exc_info=True)
        return {"status": "error", "message": "Internal server error"}


@router.post("/shiprocket", status_code=status.HTTP_200_OK)
async def shiprocket_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive Shiprocket webhook

    Shiprocket sends webhooks for shipment events
    """
    try:
        payload = await request.json()
        headers = dict(request.headers)

        service = WebhookService(db)

        # Extract event details
        event_type = payload.get("event_type") or "order/status_update"
        order_id = payload.get("order_id") or payload.get("awb")

        # Store webhook
        webhook = service.receive_webhook(
            source=WebhookSource.SHIPROCKET,
            event_type=event_type,
            event_id=str(order_id),
            payload=payload,
            headers=headers,
        )

        # Process webhook
        service.process_webhook(webhook.id)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Shiprocket webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.post("/strava", status_code=status.HTTP_200_OK)
async def strava_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive Strava webhook

    Strava sends webhooks for activity events
    """
    try:
        payload = await request.json()
        headers = dict(request.headers)

        service = WebhookService(db)

        # Extract event details
        event_type = payload.get("aspect_type")  # create, update, delete
        object_type = payload.get("object_type")  # activity, athlete
        object_id = payload.get("object_id")

        event_id = f"{object_type}_{object_id}_{event_type}"

        # Store webhook
        webhook = service.receive_webhook(
            source=WebhookSource.STRAVA,
            event_type=f"{object_type}.{event_type}",
            event_id=event_id,
            payload=payload,
            headers=headers,
        )

        # Process webhook
        service.process_webhook(webhook.id)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Strava webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.get("/strava", status_code=status.HTTP_200_OK)
async def strava_webhook_verify(
    hub_mode: str = None, hub_challenge: str = None, hub_verify_token: str = None
):
    """
    Verify Strava webhook subscription

    Strava sends GET request to verify webhook endpoint
    """
    if hub_mode == "subscribe" and hasattr(settings, "STRAVA_VERIFY_TOKEN"):
        if hub_verify_token == settings.STRAVA_VERIFY_TOKEN:
            return {"hub.challenge": hub_challenge}

    return {"error": "verification_failed"}


@router.post("/garmin", status_code=status.HTTP_200_OK)
async def garmin_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive Garmin webhook

    Garmin sends webhooks for activity events
    """
    try:
        payload = await request.json()
        headers = dict(request.headers)

        service = WebhookService(db)

        # Extract event details
        event_type = payload.get("eventType") or "activity.created"
        activity_id = payload.get("activityId")

        # Store webhook
        webhook = service.receive_webhook(
            source=WebhookSource.GARMIN,
            event_type=event_type,
            event_id=str(activity_id),
            payload=payload,
            headers=headers,
        )

        # Process webhook
        service.process_webhook(webhook.id)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Garmin webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}
