"""
DEPRECATED: Registration model has been moved to app.modules.registrations.domain

This module provides backward compatibility and will be removed in v2.0.

Migration Guide:
    Old: from app.models.registration import Registration
    New: from app.modules.registrations.domain.registration import Registration
    OR:  from app.modules.registrations import Registration
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.models.registration is deprecated. "
    "Use app.modules.registrations.domain.registration or app.modules.registrations instead. "
    "This compatibility layer will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from app.modules.registrations.domain.registration import Registration

__all__ = ['Registration']
