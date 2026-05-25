"""
Payments Module

This module handles all payment-related operations including:
- Payment order creation (Razorpay, Stripe, etc.)
- Payment verification and signature validation
- Refund processing
- Payment history and tracking

Architecture:
    - domain/: Domain models, entities, and value objects
    - services/: Application services and business logic
    - repositories/: Data access layer
    - schemas/: Request/response validation schemas
    - api/: HTTP route handlers

Usage:
    from app.modules.payments import PaymentService, Payment, PaymentEntity
    from app.modules.payments import PaymentResponse, PaymentCreate
"""

# Domain layer exports
from app.modules.payments.domain.entities import PaymentEntity
from app.modules.payments.domain.payment import Payment
from app.modules.payments.domain.payment_link import PaymentLink
from app.modules.payments.domain.settlement import PaymentSettlement, Settlement
from app.modules.payments.domain.value_objects import (
    GatewayOrderId,
    GatewayPaymentId,
    Money,
    RefundAmount,
)

# Repository exports
from app.modules.payments.repositories.payment_repository import PaymentRepository

# Schema exports
from app.modules.payments.schemas.payment import (
    PaymentCreate,
    PaymentOrderCreate,
    PaymentOrderResponse,
    PaymentResponse,
    PaymentUpdate,
    PaymentVerify,
    # Deprecated but still exported for compatibility
    RazorpayOrderCreate,
    RazorpayOrderResponse,
    RazorpayPaymentVerify,
    RefundCreate,
)
from app.modules.payments.services.commands import (
    CreatePaymentOrderCommand,
    CreateRefundCommand,
    InitiatePaymentCommand,
    UpdatePaymentStatusCommand,
    VerifyPaymentCommand,
)

# Service layer exports
from app.modules.payments.services.payment_service import PaymentService
from app.modules.payments.services.queries import (
    GetPaymentByIdQuery,
    GetPaymentByOrderIdQuery,
    GetPaymentByTransactionIdQuery,
    GetPaymentStatsQuery,
    GetRegistrationPaymentsQuery,
    GetUserPaymentsQuery,
)
from app.modules.webhooks.domain.webhook_event import WebhookEvent

__all__ = [
    # Domain
    'Payment',
    'PaymentLink',
    'Settlement',
    'PaymentSettlement',
    'WebhookEvent',
    'PaymentEntity',
    'Money',
    'GatewayOrderId',
    'GatewayPaymentId',
    'RefundAmount',

    # Services
    'PaymentService',

    # Commands
    'CreatePaymentOrderCommand',
    'VerifyPaymentCommand',
    'CreateRefundCommand',
    'UpdatePaymentStatusCommand',
    'InitiatePaymentCommand',

    # Queries
    'GetPaymentByIdQuery',
    'GetUserPaymentsQuery',
    'GetRegistrationPaymentsQuery',
    'GetPaymentByOrderIdQuery',
    'GetPaymentByTransactionIdQuery',
    'GetPaymentStatsQuery',

    # Repository
    'PaymentRepository',

    # Schemas
    'PaymentCreate',
    'PaymentOrderCreate',
    'PaymentVerify',
    'RefundCreate',
    'PaymentUpdate',
    'PaymentResponse',
    'PaymentOrderResponse',
    'RazorpayOrderCreate',
    'RazorpayOrderResponse',
    'RazorpayPaymentVerify'
]
