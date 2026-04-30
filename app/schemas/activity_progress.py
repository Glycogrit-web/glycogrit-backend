"""
Activity Progress Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ActivityProgressBase(BaseModel):
    """Base activity progress schema"""
    distance_completed: Decimal = Field(ge=0, description="Distance completed in kilometers")
    target_distance: Decimal = Field(gt=0, description="Target distance for this activity")


class ActivityProgressCreate(BaseModel):
    """Schema for creating activity progress"""
    registration_id: int
    activity_id: int
    target_distance: Decimal = Field(gt=0, description="Target distance for this activity")


class ManualDistanceEntry(BaseModel):
    """Schema for manual distance entry"""
    distance: Decimal = Field(gt=0, description="Distance to add in kilometers")


class ActivityProgressUpdate(BaseModel):
    """Schema for updating activity progress"""
    distance_to_add: Optional[Decimal] = Field(None, gt=0, description="Distance to add in kilometers")
    sync_source: Optional[str] = Field(None, max_length=50, description="Source of sync (manual, strava, garmin)")


class ActivityProgressResponse(BaseModel):
    """Activity progress response schema"""
    id: int
    user_id: int
    registration_id: int
    event_id: int
    activity_id: int

    # Progress
    distance_completed: Decimal
    target_distance: Decimal
    progress_percentage: Decimal
    is_completed: bool
    completed_at: Optional[datetime] = None

    # Manual entry
    last_manual_entry: Optional[Decimal] = None
    last_manual_entry_at: Optional[datetime] = None

    # Sync
    last_sync_at: Optional[datetime] = None
    sync_source: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Computed properties
    progress_display: str
    remaining_distance: float

    # Activity details (populated from relationship)
    activity_name: Optional[str] = None
    activity_type: Optional[str] = None
    activity_distance: Optional[Decimal] = None

    class Config:
        from_attributes = True


class ActivityProgressList(BaseModel):
    """List of activity progress records"""
    progress_records: list[ActivityProgressResponse]
    total: int
