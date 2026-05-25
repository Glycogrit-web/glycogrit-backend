"""
Razorpay Gateway Implementation with Retry Logic
"""
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
from decimal import Decimal

from app.core.config import settings
from app.core.exceptions import ValidationException, PaymentGatewayException
from app.core.retry import with_payment_gateway_retry
from app.services.payment_gateway.base import PaymentGatewayInterface

# Lazy import razorpay to avoid pkg_resources error in tests
if TYPE_CHECKING:
    import razorpay

logger = logging.getLogger(__name__)


class RazorpayGateway(PaymentGatewayInterface):
    """Razorpay payment gateway implementation"""

    def __init__(self):
        """Initialize Razorpay client"""
        # Lazy import razorpay here to avoid module-level import
        import razorpay
        self.razorpay = razorpay  # Store reference for exception handling

        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            logger.warning("Razorpay credentials not configured")
            self.client = None
        else:
            import os
            import requests

            # Check if SSL verification should be disabled (development only)
            disable_ssl = os.getenv("RAZORPAY_DISABLE_SSL_VERIFY", "false").lower() == "true"
            is_production = settings.ENVIRONMENT.lower() == "production"

            # CRITICAL SECURITY: Never disable SSL in production
            if disable_ssl and is_production:
                logger.error("⛔ SECURITY ERROR: Cannot disable SSL verification in production!")
                raise ValueError("SSL verification cannot be disabled in production environment")

            # Create session with appropriate SSL settings
            session = requests.Session()

            if disable_ssl:
                # Development only: Disable SSL verification
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                session.verify = False
                logger.warning("⚠️  SSL verification DISABLED for Razorpay (development only)")
            else:
                # Production: Enable SSL verification (secure)
                session.verify = True
                logger.info("✅ SSL verification ENABLED for Razorpay (secure)")

            # Initialize Razorpay client with custom session
            self.client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                session=session
            )

            # Only disable cert_path if SSL verification is disabled
            if disable_ssl:
                # CRITICAL FIX: Razorpay hardcodes verify=self.cert_path in requests,
                # which overrides session.verify. We need to set cert_path to False.
                self.client.cert_path = False

            logger.info("Razorpay gateway initialized successfully")

    def get_gateway_name(self) -> str:
        """Get gateway name"""
        return "razorpay"

    @with_payment_gateway_retry(max_attempts=3, min_wait=1.0, max_wait=8.0)
    def create_order(
        self,
        amount: Decimal,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Razorpay order with automatic retry on transient failures.

        Retries on network errors, timeouts, and gateway server errors.
        Does not retry on authentication or validation errors.

        Args:
            amount: Amount in rupees (will be converted to paise)
            currency: Currency code (default: INR)
            receipt: Optional receipt identifier
            notes: Optional metadata

        Returns:
            Dict with order details

        Raises:
            ValidationException: On client errors (invalid data, auth failures)
            PaymentGatewayException: On transient gateway errors (after retries exhausted)
        """
        if not self.client:
            raise ValidationException("Razorpay is not configured")

        try:
            # Convert amount to paise (Razorpay expects amount in smallest currency unit)
            amount_in_paise = int(amount * 100)

            order_data = {
                "amount": amount_in_paise,
                "currency": currency,
                "payment_capture": 1,  # Auto-capture payment
            }

            if receipt:
                order_data["receipt"] = receipt

            if notes:
                order_data["notes"] = notes

            order = self.client.order.create(data=order_data)
            logger.info(f"Razorpay order created: {order['id']}")

            return order

        except self.self.razorpay.errors.BadRequestError as e:
            # Client error (invalid request) - don't retry
            logger.error(f"Razorpay order creation failed (client error): {str(e)}")
            raise ValidationException(f"Failed to create payment order: {str(e)}")
        except self.self.razorpay.errors.ServerError as e:
            # Server error - will be retried by decorator
            logger.warning(f"Razorpay server error (will retry): {str(e)}")
            raise PaymentGatewayException(f"Gateway server error: {str(e)}")
        except self.self.razorpay.errors.GatewayError as e:
            # Gateway error - will be retried by decorator
            logger.warning(f"Razorpay gateway error (will retry): {str(e)}")
            raise PaymentGatewayException(f"Gateway connection error: {str(e)}")
        except Exception as e:
            # Unexpected error - treat as transient and retry
            logger.error(f"Unexpected error creating Razorpay order: {str(e)}")
            raise PaymentGatewayException(f"Unexpected gateway error: {str(e)}")

    def verify_payment_signature(
        self,
        order_id: str,
        payment_id: str,
        signature: str
    ) -> bool:
        """Verify Razorpay payment signature"""
        if not self.client:
            logger.error("Razorpay client not configured")
            return False

        try:
            # Create signature verification payload
            payload = f"{order_id}|{payment_id}"

            # Generate expected signature
            expected_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()

            # Compare signatures
            is_valid = hmac.compare_digest(expected_signature, signature)

            if is_valid:
                logger.info(f"Payment signature verified for order: {order_id}")
            else:
                logger.warning(f"Invalid payment signature for order: {order_id}")

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying payment signature: {str(e)}")
            return False

    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify Razorpay webhook signature"""
        if not settings.RAZORPAY_WEBHOOK_SECRET:
            logger.error("Razorpay webhook secret not configured")
            return False

        try:
            expected_signature = hmac.new(
                settings.RAZORPAY_WEBHOOK_SECRET.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()

            is_valid = hmac.compare_digest(expected_signature, signature)

            if is_valid:
                logger.info("Webhook signature verified successfully")
            else:
                logger.warning("Invalid webhook signature")

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False

    @with_payment_gateway_retry(max_attempts=3, min_wait=1.0, max_wait=8.0)
    def fetch_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch payment details from Razorpay with automatic retry.

        Args:
            payment_id: Razorpay payment ID

        Returns:
            Payment details dict or None if payment not found

        Raises:
            PaymentGatewayException: On transient gateway errors (after retries)
        """
        if not self.client:
            logger.error("Razorpay client not configured")
            return None

        try:
            payment = self.client.payment.fetch(payment_id)
            logger.info(f"Fetched payment details for: {payment_id}")
            return payment

        except self.self.razorpay.errors.BadRequestError as e:
            # Payment not found or invalid ID - don't retry
            logger.error(f"Failed to fetch payment {payment_id}: {str(e)}")
            return None
        except (self.self.razorpay.errors.ServerError, self.self.razorpay.errors.GatewayError) as e:
            # Server/gateway error - will retry
            logger.warning(f"Razorpay error fetching payment (will retry): {str(e)}")
            raise PaymentGatewayException(f"Gateway error: {str(e)}")
        except Exception as e:
            # Unexpected error - treat as transient
            logger.error(f"Unexpected error fetching payment: {str(e)}")
            raise PaymentGatewayException(f"Unexpected gateway error: {str(e)}")

    @with_payment_gateway_retry(max_attempts=3, min_wait=1.0, max_wait=8.0)
    def create_refund(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        notes: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a refund for a payment with automatic retry.

        Args:
            payment_id: Payment ID to refund
            amount: Amount to refund (None for full refund)
            notes: Optional refund notes

        Returns:
            Refund details dict or None on failure

        Raises:
            PaymentGatewayException: On transient gateway errors (after retries)
        """
        if not self.client:
            logger.error("Razorpay client not configured")
            return None

        try:
            refund_data = {}

            if amount is not None:
                # Convert to paise
                refund_data["amount"] = int(amount * 100)

            if notes:
                refund_data["notes"] = notes

            refund = self.client.payment.refund(payment_id, refund_data)
            logger.info(f"Refund created: {refund['id']} for payment: {payment_id}")

            return refund

        except self.razorpay.errors.BadRequestError as e:
            # Invalid refund request - don't retry
            logger.error(f"Failed to create refund for payment {payment_id}: {str(e)}")
            return None
        except (self.razorpay.errors.ServerError, self.razorpay.errors.GatewayError) as e:
            # Server/gateway error - will retry
            logger.warning(f"Razorpay error creating refund (will retry): {str(e)}")
            raise PaymentGatewayException(f"Gateway error: {str(e)}")
        except Exception as e:
            # Unexpected error - treat as transient
            logger.error(f"Unexpected error creating refund: {str(e)}")
            raise PaymentGatewayException(f"Unexpected gateway error: {str(e)}")

    def fetch_refund(self, payment_id: str, refund_id: str) -> Optional[Dict[str, Any]]:
        """Fetch refund details"""
        if not self.client:
            logger.error("Razorpay client not configured")
            return None

        try:
            refund = self.client.refund.fetch(refund_id)
            logger.info(f"Fetched refund details: {refund_id}")
            return refund

        except self.razorpay.errors.BadRequestError as e:
            logger.error(f"Failed to fetch refund {refund_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching refund: {str(e)}")
            return None

    def capture_payment(
        self,
        payment_id: str,
        amount: Decimal,
        currency: str = "INR"
    ) -> Optional[Dict[str, Any]]:
        """
        Manually capture an authorized payment.

        Use this when payment_capture was set to 0 during order creation.
        Must be captured within 5 days of authorization.

        Args:
            payment_id: Razorpay payment ID to capture
            amount: Amount to capture (must match or be less than authorized amount)
            currency: Currency code (default: INR)

        Returns:
            Captured payment details or None on failure
        """
        if not self.client:
            logger.error("Razorpay client not configured")
            return None

        try:
            # Convert to paise
            amount_in_paise = int(amount * 100)

            capture_data = {
                "amount": amount_in_paise,
                "currency": currency
            }

            payment = self.client.payment.capture(payment_id, amount_in_paise, capture_data)
            logger.info(f"Payment captured successfully: {payment_id}, amount: {amount}")

            return payment

        except self.razorpay.errors.BadRequestError as e:
            logger.error(f"Failed to capture payment {payment_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error capturing payment: {str(e)}")
            return None

    def create_instant_refund(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        speed: str = "optimum",
        notes: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create an instant refund.

        Instant refunds are processed in 5-10 minutes (if available).
        Falls back to normal refund (3-7 days) if instant not available.

        Args:
            payment_id: Payment ID to refund
            amount: Amount to refund (None for full refund)
            speed: 'normal' or 'optimum' (tries instant, falls back to normal)
            notes: Additional notes for the refund

        Returns:
            Refund details with actual speed used
        """
        if not self.client:
            logger.error("Razorpay client not configured")
            return None

        try:
            refund_data = {
                "speed": speed
            }

            if amount is not None:
                refund_data["amount"] = int(amount * 100)  # Convert to paise

            if notes:
                refund_data["notes"] = notes

            refund = self.client.payment.refund(payment_id, refund_data)

            actual_speed = refund.get("speed_processed", speed)
            logger.info(
                f"Refund created: {refund['id']} for payment: {payment_id}, "
                f"requested speed: {speed}, actual speed: {actual_speed}"
            )

            return refund

        except self.razorpay.errors.BadRequestError as e:
            logger.error(f"Failed to create instant refund for payment {payment_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating instant refund: {str(e)}")
            return None

    def create_payment_link(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        customer_name: str,
        customer_email: str,
        customer_contact: str,
        reference_id: str,
        callback_url: Optional[str] = None,
        expire_by: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a shareable payment link.

        Payment links can be shared via email, SMS, or WhatsApp.
        Users can pay without logging into your application.

        Args:
            amount: Amount in rupees
            currency: Currency code (INR)
            description: Payment description shown to customer
            customer_name: Customer's name
            customer_email: Customer's email
            customer_contact: Customer's phone number
            reference_id: Your internal reference ID
            callback_url: Redirect URL after payment
            expire_by: Unix timestamp for expiry (default: 7 days)

        Returns:
            Payment link details with short_url
        """
        if not self.client:
            logger.error("Razorpay client not configured")
            return None

        try:
            import time

            # Default expiry: 7 days from now
            if not expire_by:
                expire_by = int(time.time()) + (7 * 24 * 60 * 60)

            link_data = {
                "amount": int(amount * 100),  # Convert to paise
                "currency": currency,
                "description": description,
                "customer": {
                    "name": customer_name,
                    "email": customer_email,
                    "contact": customer_contact
                },
                "reference_id": reference_id,
                "expire_by": expire_by,
                "notify": {
                    "sms": True,
                    "email": True
                }
            }

            if callback_url:
                link_data["callback_url"] = callback_url
                link_data["callback_method"] = "get"

            payment_link = self.client.payment_link.create(data=link_data)
            logger.info(f"Payment link created: {payment_link['id']}, short_url: {payment_link.get('short_url')}")

            return payment_link

        except self.razorpay.errors.BadRequestError as e:
            logger.error(f"Failed to create payment link: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating payment link: {str(e)}")
            return None

    def fetch_settlement(self, settlement_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch details of a specific settlement.

        Args:
            settlement_id: Razorpay settlement ID

        Returns:
            Settlement details
        """
        if not self.client:
            logger.error("Razorpay client not configured")
            return None

        try:
            settlement = self.client.settlement.fetch(settlement_id)
            logger.info(f"Fetched settlement details: {settlement_id}")
            return settlement

        except self.razorpay.errors.BadRequestError as e:
            logger.error(f"Failed to fetch settlement {settlement_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching settlement: {str(e)}")
            return None

    def fetch_settlements(
        self,
        from_timestamp: int,
        to_timestamp: int,
        count: int = 100,
        skip: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch settlements for a date range.

        Use this to reconcile payments with actual bank deposits.

        Args:
            from_timestamp: Start date (Unix timestamp)
            to_timestamp: End date (Unix timestamp)
            count: Number of records to fetch (max 100)
            skip: Number of records to skip (for pagination)

        Returns:
            List of settlements
        """
        if not self.client:
            logger.error("Razorpay client not configured")
            return None

        try:
            params = {
                "from": from_timestamp,
                "to": to_timestamp,
                "count": min(count, 100),  # Max 100 per request
                "skip": skip
            }

            settlements = self.client.settlement.all(params)
            logger.info(f"Fetched {len(settlements.get('items', []))} settlements")

            return settlements

        except self.razorpay.errors.BadRequestError as e:
            logger.error(f"Failed to fetch settlements: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching settlements: {str(e)}")
            return None

    def normalize_order_response(self, gateway_response: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Razorpay order response to common format"""
        return {
            "order_id": gateway_response.get("id"),
            "amount": gateway_response.get("amount"),  # Already in paise
            "currency": gateway_response.get("currency"),
            "status": gateway_response.get("status"),
            "gateway_data": gateway_response  # Keep original response for reference
        }

    def normalize_refund_response(self, gateway_response: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Razorpay refund response to common format"""
        return {
            "refund_id": gateway_response.get("id"),
            "amount": gateway_response.get("amount"),  # In paise
            "status": gateway_response.get("status"),
            "gateway_data": gateway_response  # Keep original response for reference
        }
