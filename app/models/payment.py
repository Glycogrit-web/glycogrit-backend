"""
DEPRECATED: Payment model has been moved to app.modules.payments.domain

This module provides backward compatibility and will be removed in v2.0.

Migration Guide:
    Old: from app.models.payment import Payment
    New: from app.modules.payments.domain.payment import Payment
    OR:  from app.modules.payments import Payment
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.models.payment is deprecated. "
    "Use app.modules.payments.domain.payment or app.modules.payments instead. "
    "This compatibility layer will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from app.modules.payments.domain.payment import Payment

__all__ = ['Payment']
