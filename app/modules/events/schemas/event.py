"""
Event Schemas
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, computed_field

if TYPE_CHECKING:
    from app.core.tier_schemas import TierResponse


class EventBase(BaseModel):
    """Base event schema"""

    name: str
    description: str
    goals: list[str] | None = None
    rewards: list[str] | None = None
    banner_image_url: str | None = None
    rules: str | None = None


class ActivityResponse(BaseModel):
    """Global activity template response - represents selectable activities like '5K Run', '10K Cycle'"""

    id: int
    # NOTE: event_id removed - activities are now global templates
    name: str  # "5K Run", "10K Cycle", etc.
    activity_type: str | None = None  # "running", "cycling", "walking", etc.
    distance: Decimal | None = None
    description: str | None = None
    # NOTE: max_participants, current_participants, and registration_fee removed
    # These are now handled at the tier level (event_registration_tiers)
    created_at: datetime

    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    """Event response schema - maps to frontend Challenge interface"""

    id: int
    name: str
    slug: str
    description: str
    status: str  # Only 'draft' or 'published'
    event_date: datetime | None = None  # Event start date/time
    event_end_date: datetime | None = None  # Event end date/time (actual event timeline)
    registration_start_date: datetime | None = None
    registration_end_date: datetime | None = None
    current_participants: int
    currency: str
    goals: list[str] | None = None
    banner_image_url: str | None = None
    rules: str | None = None
    how_it_works: dict[str, Any] | None = None
    is_virtual: bool
    is_featured: bool
    is_archived: bool = False  # Controls visibility in archived section
    uses_tier_system: bool
    created_at: datetime
    # NOTE: activities field removed - activities are now global templates
    # Frontend should fetch all activities separately and allow user to select during registration
    tiers: list["TierResponse"] = Field(
        default=[], alias="registration_tiers", serialization_alias="tiers"
    )  # Registration tiers

    # User-specific registration status (optional - populated when user is authenticated)
    user_registration: dict[str, Any] | None = None  # User's registration for this event

    # Computed fields - automatically calculated from dates
    @computed_field
    @property
    def registration_state(self) -> str:
        """Registration state: 'open' or 'closed' (auto-computed from dates)"""
        if not self.registration_start_date or not self.registration_end_date:
            return 'closed'
        now = datetime.now()
        if self.registration_start_date <= now <= self.registration_end_date:
            return 'open'
        return 'closed'

    @computed_field
    @property
    def is_registration_open(self) -> bool:
        """Whether registration is currently open"""
        return self.registration_state == 'open'

    @computed_field
    @property
    def has_started(self) -> bool:
        """Whether event has started"""
        if not self.event_date:
            return False
        return datetime.now() >= self.event_date

    @computed_field
    @property
    def has_ended(self) -> bool:
        """Whether event has ended"""
        end_date = self.event_end_date or self.event_date
        if not end_date:
            return False
        return datetime.now() > end_date

    @computed_field
    @property
    def is_active(self) -> bool:
        """Whether event is currently active (started but not ended)"""
        return self.has_started and not self.has_ended

    class Config:
        from_attributes = True
        populate_by_name = True  # Allow using both 'tiers' and 'registration_tiers' field names


# Update forward references after all models are defined
from app.core.tier_schemas import TierResponse

EventResponse.model_rebuild()


class EventListResponse(BaseModel):
    """Event list response with pagination"""

    events: list[EventResponse]
    total: int
    page: int
    page_size: int


class EventRegisterRequest(BaseModel):
    """Event registration request"""

    activity_id: int = Field(
        ..., description="ID of the selected activity (e.g., 5K Run, 10K Cycle)"
    )


class EventRegisterResponse(BaseModel):
    """Event registration response"""

    id: int
    event_id: int
    user_id: int
    status: str
    registered_at: datetime

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    """Schema for creating a new event"""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    status: str | None = Field("draft", max_length=50)
    event_date: datetime
    event_end_date: datetime | None = None
    registration_start_date: datetime
    registration_end_date: datetime
    currency: str | None = Field("INR", max_length=10)
    goals: list[str] | None = None
    banner_image_url: str | None = Field(None, max_length=500)
    rules: str | None = None
    how_it_works: dict[str, Any] | None = None
    is_virtual: bool | None = True  # All events are virtual by default
    is_featured: bool | None = False
    is_archived: bool | None = False  # Controls archived section visibility


class EventUpdate(BaseModel):
    """Schema for updating an event"""

    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    status: str | None = Field(None, max_length=50)
    event_date: datetime | None = None
    event_end_date: datetime | None = None  # Event end date/time (actual event timeline)
    registration_start_date: datetime | None = None
    registration_end_date: datetime | None = None
    currency: str | None = Field(None, max_length=10)
    goals: list[str] | None = None
    banner_image_url: str | None = Field(None, max_length=500)
    banner_crop_data: dict[str, Any] | None = None  # Banner image crop metadata
    banner_dominant_color: str | None = Field(None, max_length=50)  # Extracted dominant color
    banner_accent_color: str | None = Field(None, max_length=50)  # Extracted accent color
    rules: str | None = None
    how_it_works: dict[str, Any] | None = None
    is_virtual: bool | None = None
    is_featured: bool | None = None
    is_archived: bool | None = None  # Controls archived section visibility


class ActivityCreate(BaseModel):
    """Schema for creating a new event activity"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Activity name (e.g., '5K Run', '10K Cycle')"
    )
    activity_type: str = Field(
        ..., max_length=50, description="Activity type: running, cycling, walking, etc."
    )
    distance: Decimal | None = Field(None, description="Distance in kilometers")
    description: str | None = Field(None, max_length=255)
    # NOTE: max_participants and registration_fee removed - handled by tiers


class ActivityUpdate(BaseModel):
    """Schema for updating an event activity"""

    name: str | None = Field(None, min_length=1, max_length=100)
    activity_type: str | None = Field(None, max_length=50)
    distance: Decimal | None = None
    description: str | None = Field(None, max_length=255)
    # NOTE: max_participants and registration_fee removed - handled by tiers
