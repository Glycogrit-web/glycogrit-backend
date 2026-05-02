"""
DEPRECATED: Shiprocket config has been moved to app.modules.shipping.domain

This module provides backward compatibility and will be removed in v2.0.

Migration Guide:
    Old: from app.models.shiprocket_config import ShiprocketConfig
    New: from app.modules.shipping.domain.config import ShiprocketConfig
    OR:  from app.modules.shipping import ShiprocketConfig
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.models.shiprocket_config is deprecated. "
    "Use app.modules.shipping.domain.config or app.modules.shipping instead. "
    "This compatibility layer will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from app.modules.shipping.domain.config import ShiprocketConfig

__all__ = ['ShiprocketConfig']
