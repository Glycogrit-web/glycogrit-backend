"""
Pydantic schemas for Physical Rewards API
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MarkEligibleRequest(BaseModel):
    """Request to mark rewards as eligible"""
    reward_ids: List[UUID] = Field(..., description="List of reward IDs to mark as eligible")


class MarkEligibleResponse(BaseModel):
    """Response from marking rewards eligible"""
    marked_count: int = Field(..., description="Number of rewards marked as eligible")
    skipped_count: int = Field(..., description="Number of rewards skipped")
    errors: List[str] = Field(default_factory=list, description="List of error messages")


class ImportTrackingResponse(BaseModel):
    """Response from importing tracking data"""
    message: str = Field(..., description="Success message")
    total_rows: int = Field(..., description="Total rows processed")
    successful: int = Field(..., description="Successfully imported")
    failed: int = Field(..., description="Failed to import")
    not_found: int = Field(..., description="Rewards not found")
    errors: List[str] = Field(default_factory=list, description="List of error messages")


class ToggleVisibilityRequest(BaseModel):
    """Request to toggle tracking visibility"""
    reward_ids: List[UUID] = Field(..., description="List of reward IDs")
    visible: bool = Field(..., description="Whether tracking should be visible to users")


class ToggleVisibilityResponse(BaseModel):
    """Response from toggling visibility"""
    toggled_count: int = Field(..., description="Number of rewards toggled")
    skipped_count: int = Field(..., description="Number skipped (no tracking data)")
    errors: List[str] = Field(default_factory=list, description="List of error messages")


class UpdateTrackingRequest(BaseModel):
    """Request to update tracking info manually"""
    tracking_id: str = Field(..., description="Tracking/AWB number")
    tracking_url: Optional[str] = Field(None, description="Direct tracking URL")
    courier_name: Optional[str] = Field(None, description="Courier partner name")


class PhysicalRewardResponse(BaseModel):
    """Physical reward details"""
    id: UUID
    user_id: int
    event_id: int
    reward_name: str
    reward_type: str
    reward_description: Optional[str]
    reward_image_url: Optional[str]
    status: str

    # Tracking details
    is_unlocked: bool
    tracking_visible_to_user: bool
    manual_tracking_id: Optional[str]
    manual_tracking_url: Optional[str]
    manual_courier_name: Optional[str]
    manual_order_reference: Optional[str]

    # Admin metadata
    unlocked_at: Optional[datetime]
    tracking_imported_at: Optional[datetime]

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RewardWithTrackingStatus(BaseModel):
    """Reward with tracking status for admin dashboard"""
    id: UUID
    user_id: int
    user_email: Optional[str]
    user_name: Optional[str]
    reward_name: str
    reward_type: str
    status: str

    # Shipping details
    shipping_city: Optional[str]
    shipping_state: Optional[str]
    shipping_pincode: Optional[str]

    # Tracking info
    manual_tracking_id: Optional[str]
    manual_tracking_url: Optional[str]
    manual_courier_name: Optional[str]
    manual_order_reference: Optional[str]
    tracking_visible_to_user: bool

    # Timestamps
    created_at: datetime
    tracking_imported_at: Optional[datetime]

    class Config:
        from_attributes = True


class TrackingPreviewResponse(BaseModel):
    """Tracking preview for admin"""
    reward_id: UUID
    reward_name: str
    tracking_id: Optional[str]
    tracking_url: Optional[str]
    courier_name: Optional[str]
    order_reference: Optional[str]
    status: str
    tracking_visible_to_user: bool


class UserTrackingResponse(BaseModel):
    """Tracking information for user"""
    reward_id: UUID
    reward_name: str
    reward_type: str
    status: str
    tracking_id: str
    tracking_url: Optional[str]
    courier_name: Optional[str]
    estimated_delivery_date: Optional[datetime]
    current_location: Optional[str]
    last_updated: Optional[datetime]
