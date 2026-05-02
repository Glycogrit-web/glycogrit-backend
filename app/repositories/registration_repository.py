"""
DEPRECATED: RegistrationRepository has been moved to app.modules.registrations.repositories

This module provides backward compatibility and will be removed in v2.0.

Migration Guide:
    Old: from app.repositories.registration_repository import RegistrationRepository
    New: from app.modules.registrations.repositories.registration_repository import RegistrationRepository
    OR:  from app.modules.registrations import RegistrationRepository
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.repositories.registration_repository is deprecated. "
    "Use app.modules.registrations.repositories.registration_repository or app.modules.registrations instead. "
    "This compatibility layer will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from app.modules.registrations.repositories.registration_repository import RegistrationRepository

__all__ = ['RegistrationRepository']
