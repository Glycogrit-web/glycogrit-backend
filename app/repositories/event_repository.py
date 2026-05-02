"""
DEPRECATED: EventRepository has been moved to app.modules.events.repositories

This module provides backward compatibility and will be removed in v2.0.

Migration Guide:
    Old: from app.repositories.event_repository import EventRepository, EventActivityRepository
    New: from app.modules.events.repositories.event_repository import EventRepository, EventActivityRepository
    OR:  from app.modules.events import EventRepository, EventActivityRepository
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.repositories.event_repository is deprecated. "
    "Use app.modules.events.repositories.event_repository or app.modules.events instead. "
    "This compatibility layer will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from app.modules.events.repositories.event_repository import EventRepository, EventActivityRepository

__all__ = ['EventRepository', 'EventActivityRepository']
