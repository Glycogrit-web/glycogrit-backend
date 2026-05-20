"""
Webhook Handler Base Classes

Provides reusable base classes for webhook handling to reduce duplication.
"""

import logging
import hashlib
import hmac
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class WebhookHandler(ABC):
    """
    Abstract base class for webhook handlers.

    Provides common functionality for verifying signatures, logging,
    and processing webhooks from external services.
    """

    def __init__(self, webhook_secret: str):
        """
        Initialize webhook handler

        Args:
            webhook_secret: Secret key for signature verification
        """
        self.webhook_secret = webhook_secret

    @abstractmethod
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature

        Args:
            payload: Raw request payload
            signature: Signature from request headers

        Returns:
            True if signature is valid, False otherwise
        """
        pass

    @abstractmethod
    async def handle_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle webhook event

        Args:
            event_type: Type of webhook event
            payload: Event payload

        Returns:
            Response dictionary

        Raises:
            HTTPException: If event handling fails
        """
        pass

    def log_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any],
        status: str = "received"
    ) -> None:
        """
        Log webhook event

        Args:
            event_type: Event type
            payload: Event payload
            status: Processing status
        """
        logger.info(
            f"Webhook {status}: type={event_type}, "
            f"timestamp={datetime.utcnow().isoformat()}"
        )
        logger.debug(f"Webhook payload: {payload}")

    async def process(
        self,
        payload: bytes,
        signature: str,
        event_type: str
    ) -> Dict[str, Any]:
        """
        Process webhook with signature verification

        Args:
            payload: Raw request payload
            signature: Signature from headers
            event_type: Event type

        Returns:
            Processing result

        Raises:
            HTTPException: If signature is invalid or processing fails
        """
        # Verify signature
        if not self.verify_signature(payload, signature):
            logger.warning(f"Invalid webhook signature for event: {event_type}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )

        # Parse payload
        import json
        try:
            payload_dict = json.loads(payload)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse webhook payload: {payload}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload format"
            )

        # Log receipt
        self.log_webhook(event_type, payload_dict, "received")

        # Handle event
        try:
            result = await self.handle_event(event_type, payload_dict)
            self.log_webhook(event_type, payload_dict, "processed")
            return result
        except Exception as e:
            self.log_webhook(event_type, payload_dict, "failed")
            logger.error(f"Webhook processing failed: {str(e)}")
            raise


class RazorpayWebhookHandler(WebhookHandler):
    """
    Webhook handler for Razorpay payment webhooks
    """

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Razorpay webhook signature

        Args:
            payload: Raw request payload
            signature: X-Razorpay-Signature header value

        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning("Razorpay webhook secret not configured")
            return False

        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    async def handle_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Razorpay webhook event

        Args:
            event_type: Event type (e.g., "payment.captured")
            payload: Event payload

        Returns:
            Processing result
        """
        event = payload.get("event")
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

        if event == "payment.captured":
            return await self._handle_payment_captured(payment_entity)
        elif event == "payment.failed":
            return await self._handle_payment_failed(payment_entity)
        elif event == "refund.processed":
            return await self._handle_refund_processed(payment_entity)
        else:
            logger.warning(f"Unhandled Razorpay event type: {event}")
            return {"status": "ignored", "event": event}

    async def _handle_payment_captured(self, payment_entity: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment captured event"""
        # To be implemented by specific service
        raise NotImplementedError("Subclass must implement payment captured handler")

    async def _handle_payment_failed(self, payment_entity: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment failed event"""
        # To be implemented by specific service
        raise NotImplementedError("Subclass must implement payment failed handler")

    async def _handle_refund_processed(self, payment_entity: Dict[str, Any]) -> Dict[str, Any]:
        """Handle refund processed event"""
        # To be implemented by specific service
        raise NotImplementedError("Subclass must implement refund processed handler")


class ShiprocketWebhookHandler(WebhookHandler):
    """
    Webhook handler for Shiprocket shipping webhooks
    """

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Shiprocket webhook signature

        Args:
            payload: Raw request payload
            signature: Signature header value

        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning("Shiprocket webhook secret not configured")
            return True  # Shiprocket may not use signatures

        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    async def handle_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Shiprocket webhook event

        Args:
            event_type: Event type (e.g., "order_status_update")
            payload: Event payload

        Returns:
            Processing result
        """
        if event_type == "order_status_update":
            return await self._handle_order_status_update(payload)
        elif event_type == "shipment_created":
            return await self._handle_shipment_created(payload)
        elif event_type == "shipment_delivered":
            return await self._handle_shipment_delivered(payload)
        else:
            logger.warning(f"Unhandled Shiprocket event type: {event_type}")
            return {"status": "ignored", "event": event_type}

    async def _handle_order_status_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle order status update"""
        # To be implemented by specific service
        raise NotImplementedError("Subclass must implement order status update handler")

    async def _handle_shipment_created(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shipment created event"""
        # To be implemented by specific service
        raise NotImplementedError("Subclass must implement shipment created handler")

    async def _handle_shipment_delivered(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shipment delivered event"""
        # To be implemented by specific service
        raise NotImplementedError("Subclass must implement shipment delivered handler")


class WebhookEventLogger:
    """
    Utility class for logging webhook events to database
    """

    def __init__(self, db):
        """
        Initialize webhook event logger

        Args:
            db: Database session
        """
        self.db = db

    async def log_event(
        self,
        provider: str,
        event_type: str,
        payload: Dict[str, Any],
        status: str = "received",
        error: Optional[str] = None
    ) -> None:
        """
        Log webhook event to database

        Args:
            provider: Webhook provider (razorpay, shiprocket, etc.)
            event_type: Event type
            payload: Event payload
            status: Processing status
            error: Optional error message
        """
        # This would create a WebhookLog record
        # Implementation depends on your WebhookLog model
        logger.info(
            f"Webhook event logged: provider={provider}, "
            f"type={event_type}, status={status}"
        )
