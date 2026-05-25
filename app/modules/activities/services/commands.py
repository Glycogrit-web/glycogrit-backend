"""
CQRS Commands for Activities Module

Commands represent write operations that change state.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass
class SubmitActivityCommand:
    """Command to submit a new activity"""
    user_id: int
    event_id: int
    activity_date: date
    distance: Decimal | None = None
    duration: int | None = None
    notes: str | None = None
    registration_id: int | None = None


@dataclass
class UpdateActivityCommand:
    """Command to update an existing activity"""
    activity_id: int
    current_user_id: int
    distance: Decimal | None = None
    duration: int | None = None
    activity_date: date | None = None
    notes: str | None = None


@dataclass
class DeleteActivityCommand:
    """Command to delete an activity"""
    activity_id: int
    current_user_id: int


@dataclass
class UpdateProgressCommand:
    """Command to update progress (manual entry)"""
    progress_id: int
    current_user_id: int
    distance_to_add: Decimal


@dataclass
class SyncProgressCommand:
    """Command to sync progress from external source"""
    progress_id: int
    source: str  # 'strava', 'garmin', etc.
    distance: Decimal
    metadata: dict[str, Any] | None = None


@dataclass
class CreateProgressCommand:
    """Command to create initial progress record"""
    user_id: int
    registration_id: int
    event_id: int
    activity_id: int
    target_distance: Decimal


@dataclass
class UploadProofCommand:
    """Command to upload proof image"""
    progress_id: int
    current_user_id: int
    image_url: str


@dataclass
class ResetProgressCommand:
    """Command to reset progress to zero"""
    progress_id: int
    admin_user_id: int
