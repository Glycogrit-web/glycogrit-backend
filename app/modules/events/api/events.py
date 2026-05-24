"""
Events API Endpoints
"""

from fastapi import APIRouter, Depends, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.auth import get_optional_current_user as get_optional_user
from app.models.user import User
from app.modules.events.services.event_service import EventService, ActivityService
from app.modules.events.domain.event import Event
# EventActivityService was removed in refactoring - use EventService directly
from app.modules.events.schemas.event import (
    EventResponse,
    EventCreate,
    EventUpdate,
    ActivityResponse,
    ActivityCreate,
    ActivityUpdate,
)


class RegisterTierRequest(BaseModel):
    tier_id: int
    activity_id: Optional[int] = None
    participant_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    t_shirt_size: Optional[str] = None

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new event (Admin/Organizer only)

    Creates event with:
    - Basic details (name, description, dates)
    - Registration configuration
    - Pricing tiers
    - Activities
    """
    service = EventService(db)
    event = service.create_event(
        event_data=event_data.model_dump(),
        organizer_id=current_user.id
    )
    return EventResponse.model_validate(event)


@router.get("")
def get_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    search: Optional[str] = None,
    is_featured: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Get all events with pagination metadata

    Returns paginated response with:
    - events: List of events
    - total: Total count of events
    - page: Current page number
    - page_size: Number of items per page

    Optional parameters:
    - search: Filter by name/description
    - is_featured: Filter featured events only
    """
    service = EventService(db)

    # Get events based on filters
    if search:
        events = service.search_events(search_term=search, skip=skip, limit=limit)
        # For search, count all matching results
        all_results = service.search_events(search_term=search, skip=0, limit=99999)
        total = len(all_results)
    elif is_featured is not None:
        # Filter by is_featured flag
        query = service.db.query(Event).filter(Event.is_featured == is_featured)
        total = query.count()
        events = query.offset(skip).limit(limit).all()
    else:
        events = service.get_all_events(skip=skip, limit=limit)
        total = service.db.query(Event).count()

    return {
        "events": [EventResponse.model_validate(event) for event in events],
        "total": total,
        "page": (skip // limit) + 1 if limit > 0 else 1,
        "page_size": limit
    }


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Get event details by ID

    Returns complete event information including:
    - Basic details
    - Activities
    - Tiers
    - Registration status
    """
    service = EventService(db)
    event = service.get_event_by_id(event_id)
    return EventResponse.model_validate(event)


@router.get("/slug/{slug}", response_model=EventResponse)
def get_event_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """
    Get event details by slug (URL-friendly identifier)
    """
    service = EventService(db)
    event = service.get_event_by_slug(slug)
    return EventResponse.model_validate(event)


@router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: int,
    event_data: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update event details (Admin/Organizer only)
    """
    service = EventService(db)
    event = service.update_event(
        event_id=event_id,
        update_data=event_data.model_dump(exclude_unset=True),
        current_user=current_user
    )
    return EventResponse.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete event (Admin/Organizer only)

    Soft deletes the event
    """
    service = EventService(db)
    service.delete_event(event_id=event_id, current_user=current_user)
    return None


@router.get("/organizer/my", response_model=List[EventResponse])
def get_my_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get events created by current user (Organizer view)
    """
    service = EventService(db)
    events = service.get_events_by_organizer(
        organizer_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return [EventResponse.model_validate(event) for event in events]


@router.get("/users/{user_id}/events")
def get_user_events(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """
    Get all events a user has registered for

    Returns paginated response with:
    - events: List of events the user has registered for
    - total: Total count of user's events
    - page: Current page number
    - page_size: Number of items per page
    """
    service = EventService(db)
    events = service.get_events_by_user(
        user_id=user_id,
        skip=skip,
        limit=limit
    )

    # Get total count
    from app.modules.registrations.domain.registration import Registration
    total = db.query(Event).join(
        Registration, Event.id == Registration.event_id
    ).filter(
        Registration.user_id == user_id
    ).count()

    return {
        "events": [EventResponse.model_validate(event) for event in events],
        "total": total,
        "page": (skip // limit) + 1 if limit > 0 else 1,
        "page_size": limit
    }


# Event Activities Endpoints

@router.post("/{event_id}/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(
    event_id: int,
    activity_data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create activity for event (Admin/Organizer only)

    Activities are selectable options like "5K Run", "10K Cycle"
    """
    service = ActivityService(db)
    activity = service.create_activity(
        event_id=event_id,
        activity_data=activity_data.model_dump(),
        current_user_id=current_user.id
    )
    return ActivityResponse.model_validate(activity)


@router.get("/{event_id}/activities", response_model=List[ActivityResponse])
def get_event_activities(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all activities for an event

    Returns list of selectable activities with participant counts
    """
    service = ActivityService(db)
    activities = service.get_activities_by_event(event_id)
    return [ActivityResponse.model_validate(activity) for activity in activities]


@router.patch("/activities/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: int,
    activity_data: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update activity details (Admin/Organizer only)
    """
    service = ActivityService(db)
    activity = service.update_activity(
        activity_id=activity_id,
        update_data=activity_data.model_dump(exclude_unset=True),
        current_user_id=current_user.id
    )
    return ActivityResponse.model_validate(activity)


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete activity (Admin/Organizer only)
    """
    service = ActivityService(db)
    service.delete_activity(activity_id=activity_id, current_user_id=current_user.id)
    return None


@router.post("/{event_id}/register-tier", status_code=status.HTTP_201_CREATED)
def register_for_event_tier(
    event_id: int,
    request: RegisterTierRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Register for an event with a specific tier.

    Returns registration details and payment order if payment is required.
    """
    from app.modules.registrations.services.registration_service import RegistrationService

    service = RegistrationService(db)
    return service.register_for_event_tier(
        event_id=event_id,
        tier_id=request.tier_id,
        user_id=current_user.id,
        participant_name=request.participant_name,
        age=request.age,
        gender=request.gender,
        t_shirt_size=request.t_shirt_size,
        activity_id=request.activity_id,
    )
