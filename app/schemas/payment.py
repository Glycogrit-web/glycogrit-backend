"""
DEPRECATED: Payment schemas have been moved to app.modules.payments.schemas

This module provides backward compatibility and will be removed in v2.0.

Migration Guide:
    Old: from app.schemas.payment import PaymentResponse, PaymentCreate, ...
    New: from app.modules.payments.schemas.payment import PaymentResponse, PaymentCreate, ...
    OR:  from app.modules.payments import PaymentResponse, PaymentCreate, ...
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.schemas.payment is deprecated. "
    "Use app.modules.payments.schemas.payment or app.modules.payments instead. "
    "This compatibility layer will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from app.modules.payments.schemas.payment import (
    PaymentCreate,
    PaymentOrderCreate,
    PaymentVerify,
    RazorpayOrderCreate,
    RazorpayPaymentVerify,
    RefundCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentOrderResponse,
    RazorpayOrderResponse
)

__all__ = [
    'PaymentCreate',
    'PaymentOrderCreate',
    'PaymentVerify',
    'RazorpayOrderCreate',
    'RazorpayPaymentVerify',
    'RefundCreate',
    'PaymentUpdate',
    'PaymentResponse',
    'PaymentOrderResponse',
    'RazorpayOrderResponse'
]
