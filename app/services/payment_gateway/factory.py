"""
Payment Gateway Factory
Factory pattern for creating payment gateway instances
"""
import logging
from typing import Optional

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.services.payment_gateway.base import PaymentGatewayInterface

logger = logging.getLogger(__name__)


class PaymentGatewayFactory:
    """
    Factory class for creating payment gateway instances.
    Supports multiple payment providers and easy switching between them.
    """

    _instances = {}  # Cache gateway instances

    @classmethod
    def create_gateway(cls, provider: Optional[str] = None) -> PaymentGatewayInterface:
        """
        Create a payment gateway instance for the specified provider.

        Args:
            provider: Payment provider name ('razorpay', 'stripe', 'paypal', etc.)
                     If None, uses the default provider from settings

        Returns:
            PaymentGatewayInterface: Configured gateway instance

        Raises:
            ValidationException: If provider is not supported or not configured
        """
        # Use default provider if none specified
        if provider is None:
            provider = getattr(settings, 'DEFAULT_PAYMENT_GATEWAY', 'razorpay')

        # Return cached instance if exists
        if provider in cls._instances:
            return cls._instances[provider]

        # Create new instance based on provider
        if provider == 'razorpay':
            from app.services.payment_gateway.razorpay_gateway import RazorpayGateway
            gateway = RazorpayGateway()
            cls._instances[provider] = gateway
            logger.info(f"Created Razorpay gateway instance")
            return gateway

        # Add more providers here as needed
        # elif provider == 'stripe':
        #     from app.services.payment_gateway.stripe_gateway import StripeGateway
        #     gateway = StripeGateway()
        #     cls._instances[provider] = gateway
        #     return gateway
        #
        # elif provider == 'paypal':
        #     from app.services.payment_gateway.paypal_gateway import PayPalGateway
        #     gateway = PayPalGateway()
        #     cls._instances[provider] = gateway
        #     return gateway

        else:
            raise ValidationException(f"Unsupported payment provider: {provider}")

    @classmethod
    def get_available_providers(cls) -> list:
        """
        Get list of available payment providers.

        Returns:
            List of provider names
        """
        providers = ['razorpay']  # Add more as you implement them
        # providers.extend(['stripe', 'paypal'])
        return providers

    @classmethod
    def clear_cache(cls):
        """Clear cached gateway instances (useful for testing)"""
        cls._instances.clear()
        logger.info("Payment gateway cache cleared")


def get_payment_gateway(provider: Optional[str] = None) -> PaymentGatewayInterface:
    """
    Convenience function to get a payment gateway instance.

    Args:
        provider: Payment provider name (optional, uses default if not specified)

    Returns:
        PaymentGatewayInterface: Configured gateway instance

    Example:
        # Use default provider (from settings)
        gateway = get_payment_gateway()

        # Use specific provider
        gateway = get_payment_gateway('razorpay')
        gateway = get_payment_gateway('stripe')
    """
    return PaymentGatewayFactory.create_gateway(provider)
