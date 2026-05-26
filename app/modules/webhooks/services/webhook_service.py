"""
Webhook Service

Handles webhook processing from various sources.
"""

import hashlib
import hmac
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.modules.webhooks.domain.webhook_event import WebhookEvent, WebhookSource, WebhookStatus
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class WebhookService(BaseService):
    """Service for webhook operations"""

    def __init__(self, db: Session):
        super().__init__(db)

    def receive_webhook(
        self,
        source: WebhookSource,
        event_type: str,
        event_id: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
        signature: str | None = None,
    ) -> WebhookEvent:
        """
        Receive and store webhook event

        Args:
            source: Webhook source
            event_type: Event type (e.g., payment.captured)
            event_id: External event ID
            payload: Webhook payload
            headers: Request headers
            signature: Webhook signature for verification

        Returns:
            Created WebhookEvent
        """
        # Check for duplicate
        existing = self.db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()

        if existing:
            logger.info(f"Duplicate webhook received: {event_id}")
            return existing

        # Create webhook event
        webhook = WebhookEvent(
            source=source,
            event_type=event_type,
            event_id=event_id,
            payload=json.dumps(payload),
            headers=json.dumps(headers) if headers else None,
            signature=signature,
            status=WebhookStatus.PENDING,
        )

        self.db.add(webhook)
        self.db.commit()
        self.db.refresh(webhook)

        logger.info(f"Webhook received: {source.value}/{event_type} - {event_id}")

        return webhook

    def verify_razorpay_signature(self, webhook: WebhookEvent, secret: str) -> bool:
        """
        Verify Razorpay webhook signature

        Args:
            webhook: WebhookEvent instance
            secret: Razorpay webhook secret

        Returns:
            True if signature is valid
        """
        if not webhook.signature:
            return False

        # Razorpay sends signature as x-razorpay-signature header
        expected_signature = hmac.new(
            secret.encode("utf-8"), webhook.payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        is_valid = hmac.compare_digest(expected_signature, webhook.signature)

        if is_valid:
            webhook.signature_verified = True
            self.db.commit()

        return is_valid

    def process_webhook(self, webhook_id: int) -> None:
        """
        Process webhook event

        Args:
            webhook_id: WebhookEvent ID
        """
        webhook = self.get_or_404(self.db.query(WebhookEvent), webhook_id, "WebhookEvent")

        try:
            webhook.mark_processing()
            self.db.commit()

            payload = json.loads(webhook.payload)

            # Route to appropriate handler
            if webhook.source == WebhookSource.RAZORPAY:
                self._handle_razorpay_webhook(webhook.event_type, payload)
            elif webhook.source == WebhookSource.SHIPROCKET:
                self._handle_shiprocket_webhook(webhook.event_type, payload)
            elif webhook.source in [
                WebhookSource.STRAVA,
                WebhookSource.GARMIN,
                WebhookSource.FITBIT,
            ]:
                self._handle_fitness_tracker_webhook(webhook.source, webhook.event_type, payload)

            webhook.mark_processed()
            self.db.commit()

            logger.info(f"Webhook processed: {webhook.event_id}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Webhook processing failed: {webhook.event_id} - {error_msg}")
            webhook.mark_failed(error_msg)
            self.db.commit()
            raise

    def _handle_razorpay_webhook(self, event_type: str, payload: dict[str, Any]) -> None:
        """Handle Razorpay webhook events"""
        # Import here to avoid circular dependency
        from app.modules.payments.services.payment_service import PaymentService

        PaymentService(self.db)

        if event_type == "payment.captured":
            # Update payment status to captured
            payment_id = payload["payload"]["payment"]["entity"]["id"]
            order_id = payload["payload"]["payment"]["entity"]["order_id"]
            # TODO: Implement payment capture handler
            logger.info(f"Payment captured: {payment_id} for order {order_id}")

        elif event_type == "payment.failed":
            # Update payment status to failed
            payment_id = payload["payload"]["payment"]["entity"]["id"]
            # TODO: Implement payment failure handler
            logger.info(f"Payment failed: {payment_id}")

        elif event_type == "refund.processed":
            # Process refund
            refund_id = payload["payload"]["refund"]["entity"]["id"]
            # TODO: Implement refund handler
            logger.info(f"Refund processed: {refund_id}")

    def _handle_shiprocket_webhook(self, event_type: str, payload: dict[str, Any]) -> None:
        """Handle Shiprocket webhook events"""
        # Import here to avoid circular dependency
        from app.modules.shipping.services.shipping_service import ShippingService

        ShippingService(self.db)

        if event_type == "order/shipped":
            # Update shipment status
            order_id = payload.get("order_id")
            # TODO: Implement shipment status handler
            logger.info(f"Order shipped: {order_id}")

        elif event_type == "order/delivered":
            # Mark as delivered
            order_id = payload.get("order_id")
            # TODO: Implement delivery handler
            logger.info(f"Order delivered: {order_id}")

    def _handle_fitness_tracker_webhook(
        self, source: WebhookSource, event_type: str, payload: dict[str, Any]
    ) -> None:
        """Handle fitness tracker webhook events"""
        # Import here to avoid circular dependency
        from app.modules.fitness_trackers.services.sync_service import SyncService

        SyncService(self.db)

        if event_type == "activity.created":
            # Sync new activity
            athlete_id = payload.get("owner_id") or payload.get("athlete_id")
            # TODO: Implement activity sync handler
            logger.info(f"New activity from {source.value}: athlete {athlete_id}")

    def get_failed_webhooks(self, limit: int = 100):
        """Get failed webhooks for retry"""
        return (
            self.db.query(WebhookEvent)
            .filter(WebhookEvent.status == WebhookStatus.FAILED, WebhookEvent.retry_count < 3)
            .limit(limit)
            .all()
        )
