"""
DEPRECATED: Event models have been moved to app.modules.events.domain

This module provides backward compatibility and will be removed in v2.0.

Migration Guide:
    Old: from app.models.event import Event, EventActivity
    New: from app.modules.events.domain.event import Event, EventActivity
    OR:  from app.modules.events import Event, EventActivity
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.models.event is deprecated. "
    "Use app.modules.events.domain.event or app.modules.events instead. "
    "This compatibility layer will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from app.modules.events.domain.event import Event, EventActivity

__all__ = ['Event', 'EventActivity']
