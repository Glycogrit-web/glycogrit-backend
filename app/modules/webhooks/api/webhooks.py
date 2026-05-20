"""
Webhook API Endpoints
"""

from fastapi import APIRouter, Depends, Request, Header, status
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.database import get_db
from app.modules.webhooks.services.webhook_service import WebhookService
from app.modules.webhooks.domain.webhook_event import WebhookSource
from app.core.config import settings

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Receive Razorpay webhook

    Razorpay sends webhooks for payment events
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

        # Store webhook
        webhook = service.receive_webhook(
            source=WebhookSource.RAZORPAY,
            event_type=event_type,
            event_id=event_id or "unknown",
            payload=payload,
            headers=headers,
            signature=x_razorpay_signature
        )

        # Verify signature
        if x_razorpay_signature and hasattr(settings, 'RAZORPAY_WEBHOOK_SECRET'):
            is_valid = service.verify_razorpay_signature(
                webhook,
                settings.RAZORPAY_WEBHOOK_SECRET
            )
            if not is_valid:
                logger.warning(f"Invalid Razorpay signature: {event_id}")
                return {"status": "signature_verification_failed"}

        # Process webhook asynchronously
        # TODO: Use background task or queue
        service.process_webhook(webhook.id)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Razorpay webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.post("/shiprocket", status_code=status.HTTP_200_OK)
async def shiprocket_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
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
            headers=headers
        )

        # Process webhook
        service.process_webhook(webhook.id)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Shiprocket webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.post("/strava", status_code=status.HTTP_200_OK)
async def strava_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
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
            headers=headers
        )

        # Process webhook
        service.process_webhook(webhook.id)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Strava webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.get("/strava", status_code=status.HTTP_200_OK)
async def strava_webhook_verify(
    hub_mode: str = None,
    hub_challenge: str = None,
    hub_verify_token: str = None
):
    """
    Verify Strava webhook subscription

    Strava sends GET request to verify webhook endpoint
    """
    if hub_mode == "subscribe" and hasattr(settings, 'STRAVA_VERIFY_TOKEN'):
        if hub_verify_token == settings.STRAVA_VERIFY_TOKEN:
            return {"hub.challenge": hub_challenge}

    return {"error": "verification_failed"}


@router.post("/garmin", status_code=status.HTTP_200_OK)
async def garmin_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
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
            headers=headers
        )

        # Process webhook
        service.process_webhook(webhook.id)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Garmin webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}
