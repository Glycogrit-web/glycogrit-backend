"""
Razorpay Gateway Implementation
"""
import razorpay
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional
from decimal import Decimal

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.services.payment_gateway.base import PaymentGatewayInterface

logger = logging.getLogger(__name__)


class RazorpayGateway(PaymentGatewayInterface):
    """Razorpay payment gateway implementation"""

    def __init__(self):
        """Initialize Razorpay client"""
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            logger.warning("Razorpay credentials not configured")
            self.client = None
        else:
            # Disable SSL verification for development (fixes certificate issues)
            # WARNING: Only use in development, not production
            import urllib3
            import requests
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # Create a custom session with SSL verification disabled
            session = requests.Session()
            session.verify = False

            # Initialize Razorpay client with custom session
            self.client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                session=session
            )

            # CRITICAL FIX: Razorpay hardcodes verify=self.cert_path in requests,
            # which overrides session.verify. We need to set cert_path to False.
            self.client.cert_path = False

            logger.info("Razorpay gateway initialized successfully (SSL verification disabled)")

    def get_gateway_name(self) -> str:
        """Get gateway name"""
        return "razorpay"

    def create_order(
        self,
        amount: Decimal,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a Razorpay order"""
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

        except razorpay.errors.BadRequestError as e:
            logger.error(f"Razorpay order creation failed: {str(e)}")
            raise ValidationException(f"Failed to create payment order: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating Razorpay order: {str(e)}")
            raise ValidationException(f"Failed to create payment order: {str(e)}")

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

    def fetch_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Fetch payment details from Razorpay"""
        if not self.client:
            logger.error("Razorpay client not configured")
            return None

        try:
            payment = self.client.payment.fetch(payment_id)
            logger.info(f"Fetched payment details for: {payment_id}")
            return payment

        except razorpay.errors.BadRequestError as e:
            logger.error(f"Failed to fetch payment {payment_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching payment: {str(e)}")
            return None

    def create_refund(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        notes: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a refund for a payment"""
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

        except razorpay.errors.BadRequestError as e:
            logger.error(f"Failed to create refund for payment {payment_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating refund: {str(e)}")
            return None

    def fetch_refund(self, payment_id: str, refund_id: str) -> Optional[Dict[str, Any]]:
        """Fetch refund details"""
        if not self.client:
            logger.error("Razorpay client not configured")
            return None

        try:
            refund = self.client.refund.fetch(refund_id)
            logger.info(f"Fetched refund details: {refund_id}")
            return refund

        except razorpay.errors.BadRequestError as e:
            logger.error(f"Failed to fetch refund {refund_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching refund: {str(e)}")
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
