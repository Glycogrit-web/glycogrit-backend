"""
Activities Module - Domain-Driven Design

This module handles all activity-related functionality including:
- Activity submissions and tracking
- Progress tracking for events
- File parsing (GPX, TCX, FIT)
- Activity synchronization from fitness trackers
- Validation and highest-wins logic
"""

from app.modules.activities.domain.activity_log import UserActivityLog
from app.modules.activities.domain.activity_progress import ActivityProgress
from app.modules.activities.services.activity_service import ActivityService
from app.modules.activities.services.progress_service import ProgressService
from app.modules.activities.repositories.activity_repository import ActivityRepository
from app.modules.activities.repositories.progress_repository import ProgressRepository
from app.modules.activities.api import activities_router, progress_router

__all__ = [
    "UserActivityLog",
    "ActivityProgress",
    "ActivityService",
    "ProgressService",
    "ActivityRepository",
    "ProgressRepository",
    "activities_router",
    "progress_router",
]
