"""
Schemas package for Activities module

Exports Pydantic schemas for API validation and serialization.
"""

from app.modules.activities.schemas.activity import (
    ActivityBase,
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    ActivityStatsResponse,
)
from app.modules.activities.schemas.progress import (
    ProgressBase,
    ProgressCreate,
    ProgressUpdate,
    ProgressSyncRequest,
    ProgressResponse,
    LeaderboardEntry,
    LeaderboardResponse,
)

__all__ = [
    # Activity schemas
    "ActivityBase",
    "ActivityCreate",
    "ActivityUpdate",
    "ActivityResponse",
    "ActivityStatsResponse",
    # Progress schemas
    "ProgressBase",
    "ProgressCreate",
    "ProgressUpdate",
    "ProgressSyncRequest",
    "ProgressResponse",
    "LeaderboardEntry",
    "LeaderboardResponse",
]
