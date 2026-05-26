"""
Payment Gateway Base Interface
Abstract base class for all payment gateway implementations
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any


class PaymentGatewayInterface(ABC):
    """
    Abstract interface for payment gateways.
    All payment gateway implementations must implement these methods.
    """

    @abstractmethod
    def create_order(
        self,
        amount: Decimal,
        currency: str = "INR",
        receipt: str | None = None,
        notes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a payment order.

        Args:
            amount: Order amount in currency units
            currency: Currency code (default: INR)
            receipt: Receipt ID for reference
            notes: Additional notes/metadata

        Returns:
            Dict containing order details with order_id

        Raises:
            ValidationException: If order creation fails
        """
        pass

    @abstractmethod
    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """
        Verify payment signature for security.

        Args:
            order_id: Order ID from gateway
            payment_id: Payment ID from gateway
            signature: Signature to verify

        Returns:
            True if signature is valid, False otherwise
        """
        pass

    @abstractmethod
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: Webhook payload as string
            signature: Signature header value

        Returns:
            True if signature is valid, False otherwise
        """
        pass

    @abstractmethod
    def fetch_payment(self, payment_id: str) -> dict[str, Any] | None:
        """
        Fetch payment details from gateway.

        Args:
            payment_id: Payment ID

        Returns:
            Payment details dict or None if fetch fails
        """
        pass

    @abstractmethod
    def create_refund(
        self, payment_id: str, amount: Decimal | None = None, notes: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """
        Create a refund for a payment.

        Args:
            payment_id: Payment ID to refund
            amount: Amount to refund (None for full refund)
            notes: Additional notes for the refund

        Returns:
            Refund details dict or None if refund fails
        """
        pass

    @abstractmethod
    def fetch_refund(self, payment_id: str, refund_id: str) -> dict[str, Any] | None:
        """
        Fetch refund details.

        Args:
            payment_id: Payment ID
            refund_id: Refund ID

        Returns:
            Refund details dict or None if fetch fails
        """
        pass

    @abstractmethod
    def get_gateway_name(self) -> str:
        """
        Get the name of the payment gateway.

        Returns:
            Gateway name (e.g., "razorpay", "stripe", "paypal")
        """
        pass

    @abstractmethod
    def normalize_order_response(self, gateway_response: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize gateway-specific order response to common format.

        Args:
            gateway_response: Raw response from gateway

        Returns:
            Normalized dict with keys: order_id, amount, currency
        """
        pass

    @abstractmethod
    def normalize_refund_response(self, gateway_response: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize gateway-specific refund response to common format.

        Args:
            gateway_response: Raw response from gateway

        Returns:
            Normalized dict with keys: refund_id, amount, status
        """
        pass
