"""
Progress Pydantic Schemas

Schemas for API request/response validation and serialization.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, validator


class SyncSourceEnum(str, Enum):
    """Sync source enumeration"""
    manual = "manual"
    strava = "strava"
    garmin = "garmin"
    fitbit = "fitbit"
    wahoo = "wahoo"
    polar = "polar"


class ProgressBase(BaseModel):
    """Base schema for progress data"""
    target_distance: Decimal = Field(..., gt=0, description="Target distance in kilometers")

    class Config:
        json_schema_extra = {
            "example": {
                "target_distance": 42.195
            }
        }


class ProgressCreate(ProgressBase):
    """Schema for creating progress"""
    registration_id: int = Field(..., description="Registration ID")
    event_id: int = Field(..., description="Event ID")
    activity_id: int = Field(..., description="Event Activity ID")


class ProgressUpdate(BaseModel):
    """Schema for manual progress update"""
    distance_to_add: Decimal = Field(..., gt=0, description="Distance to add in kilometers")

    class Config:
        json_schema_extra = {
            "example": {
                "distance_to_add": 5.5
            }
        }


class ProgressSyncRequest(BaseModel):
    """Schema for syncing progress from external source"""
    source: SyncSourceEnum = Field(..., description="Sync source")
    distance: Decimal = Field(..., ge=0, description="Total distance from source in kilometers")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata fields"""
        if v:
            # Ensure common fields are proper types
            if 'activity_count' in v and not isinstance(v['activity_count'], int):
                raise ValueError("activity_count must be an integer")
            if 'total_duration_minutes' in v and not isinstance(v['total_duration_minutes'], (int, float)):
                raise ValueError("total_duration_minutes must be numeric")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "source": "strava",
                "distance": 125.5,
                "metadata": {
                    "activity_count": 20,
                    "total_duration_minutes": 720,
                    "last_activity_date": "2024-01-15"
                }
            }
        }


class ProgressSyncResponse(BaseModel):
    """Schema for sync operation response"""
    was_updated: bool = Field(..., description="Whether active distance was updated")
    source: str = Field(..., description="Source that was synced")
    source_distance: float = Field(..., description="Distance from this source")
    old_active_distance: float = Field(..., description="Previous active distance")
    new_active_distance: float = Field(..., description="New active distance")
    highest_source: str | None = Field(None, description="Source with highest distance")
    is_completed: bool = Field(..., description="Whether goal is completed")
    progress_percentage: float = Field(..., description="Progress percentage")

    class Config:
        json_schema_extra = {
            "example": {
                "was_updated": True,
                "source": "strava",
                "source_distance": 125.5,
                "old_active_distance": 100.0,
                "new_active_distance": 125.5,
                "highest_source": "strava",
                "is_completed": False,
                "progress_percentage": 75.5
            }
        }


class ProgressResponse(BaseModel):
    """Schema for progress response"""
    id: int
    user_id: int
    registration_id: int
    event_id: int
    activity_id: int
    distance_completed: Decimal
    target_distance: Decimal
    progress_percentage: float
    is_completed: bool
    completed_at: datetime | None

    # Source tracking
    sync_source: str | None
    last_sync_at: datetime | None
    highest_distance_source: str | None
    highest_distance_set_at: datetime | None
    distance_by_source: dict[str, Any]

    # Manual entry
    last_manual_entry: Decimal | None
    last_manual_entry_at: datetime | None

    # Proof
    proof_image_url: str | None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Computed fields
    remaining_distance: float = Field(..., description="Remaining distance to goal")
    activity_count: int = Field(0, description="Total activities from winning source")
    total_duration_minutes: int = Field(0, description="Total duration from winning source")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 123,
                "registration_id": 789,
                "event_id": 456,
                "activity_id": 12,
                "distance_completed": 125.5,
                "target_distance": 200.0,
                "progress_percentage": 62.75,
                "is_completed": False,
                "completed_at": None,
                "sync_source": "strava",
                "last_sync_at": "2024-01-15T10:30:00",
                "highest_distance_source": "strava",
                "highest_distance_set_at": "2024-01-15T10:30:00",
                "distance_by_source": {
                    "strava": {
                        "distance_km": 125.5,
                        "activity_count": 20,
                        "total_duration_minutes": 720
                    },
                    "manual": {
                        "distance_km": 100.0
                    }
                },
                "remaining_distance": 74.5,
                "activity_count": 20,
                "total_duration_minutes": 720,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-15T10:30:00"
            }
        }


class LeaderboardEntry(BaseModel):
    """Schema for leaderboard entry"""
    rank: int = Field(..., description="Leaderboard rank")
    user_id: int = Field(..., description="User ID")
    distance_completed: float = Field(..., description="Distance completed")
    target_distance: float = Field(..., description="Target distance")
    progress_percentage: float = Field(..., description="Progress percentage")
    is_completed: bool = Field(..., description="Whether goal is completed")
    completed_at: str | None = Field(None, description="Completion timestamp")
    activity_count: int = Field(..., description="Number of activities")
    total_duration_minutes: int = Field(..., description="Total duration in minutes")

    class Config:
        json_schema_extra = {
            "example": {
                "rank": 1,
                "user_id": 123,
                "distance_completed": 200.0,
                "target_distance": 200.0,
                "progress_percentage": 100.0,
                "is_completed": True,
                "completed_at": "2024-01-15T10:30:00",
                "activity_count": 25,
                "total_duration_minutes": 900
            }
        }


class LeaderboardResponse(BaseModel):
    """Schema for leaderboard response"""
    event_id: int
    leaderboard: list[LeaderboardEntry]
    total_participants: int

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": 456,
                "leaderboard": [],
                "total_participants": 150
            }
        }


class ProofUploadResponse(BaseModel):
    """Schema for proof upload response"""
    progress_id: int
    proof_image_url: str
    uploaded_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "progress_id": 1,
                "proof_image_url": "https://r2.example.com/proof/123.jpg",
                "uploaded_at": "2024-01-15T10:30:00"
            }
        }
