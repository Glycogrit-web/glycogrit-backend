"""
DEPRECATED: Shiprocket models have been moved to app.modules.shipping.domain

This module provides backward compatibility and will be removed in v2.0.

Migration Guide:
    Old: from app.models.shiprocket_order import ShiprocketOrder, ShiprocketOrderStatus
    New: from app.modules.shipping.domain.shipment import ShiprocketOrder, ShiprocketOrderStatus
    OR:  from app.modules.shipping import ShiprocketOrder, ShiprocketOrderStatus
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.models.shiprocket_order is deprecated. "
    "Use app.modules.shipping.domain.shipment or app.modules.shipping instead. "
    "This compatibility layer will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from app.modules.shipping.domain.shipment import ShiprocketOrder, ShiprocketOrderStatus

__all__ = ['ShiprocketOrder', 'ShiprocketOrderStatus']
