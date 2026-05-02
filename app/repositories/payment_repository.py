"""
DEPRECATED: Payment repository has been moved to app.modules.payments.repositories

This module provides backward compatibility and will be removed in v2.0.

Migration Guide:
    Old: from app.repositories.payment_repository import PaymentRepository
    New: from app.modules.payments.repositories.payment_repository import PaymentRepository
    OR:  from app.modules.payments import PaymentRepository
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.repositories.payment_repository is deprecated. "
    "Use app.modules.payments.repositories.payment_repository or app.modules.payments instead. "
    "This compatibility layer will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from app.modules.payments.repositories.payment_repository import PaymentRepository

__all__ = ['PaymentRepository']
