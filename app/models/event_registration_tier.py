"""
DEPRECATED: EventRegistrationTier model has been moved to app.modules.registrations.domain

This module provides backward compatibility and will be removed in v2.0.

Migration Guide:
    Old: from app.models.event_registration_tier import EventRegistrationTier
    New: from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier
    OR:  from app.modules.registrations import EventRegistrationTier
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.models.event_registration_tier is deprecated. "
    "Use app.modules.registrations.domain.event_registration_tier or app.modules.registrations instead. "
    "This compatibility layer will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier

__all__ = ['EventRegistrationTier']
