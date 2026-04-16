"""
Event API Endpoints
"""
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.schemas.event import (
    EventResponse, EventListResponse, EventRegisterRequest, EventRegisterResponse,
    EventCreate, EventUpdate, CategoryResponse, CategoryCreate, CategoryUpdate
)
from app.schemas.registration import RegistrationCreate, RegistrationResponse
from app.models.user import User
from app.models.event import Event
from app.models.registration import Registration
from app.services.event_service import EventService, CategoryService
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/api/v1/events", tags=["Events"])


@router.get("", response_model=EventListResponse)
async def list_events(
    category: Optional[str] = Query(None, description="Filter by event type (running, cycling, walking, mixed, strength)"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (beginner, intermediate, advanced)"),
    status: Optional[str] = Query(None, description="Filter by status (upcoming, ongoing, completed)"),
    is_virtual: Optional[bool] = Query(None, description="Filter virtual events"),
    is_featured: Optional[bool] = Query(None, description="Filter featured events"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get list of events with optional filters

    - **category**: Filter by event type (running, cycling, walking, mixed, strength)
    - **difficulty**: Filter by difficulty level (beginner, intermediate, advanced)
    - **status**: Filter by event status (upcoming, ongoing, completed)
    - **is_virtual**: Filter virtual events only
    - **is_featured**: Filter featured events only
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)
    """
    query = db.query(Event)

    # Apply filters
    if category and category != 'all':
        query = query.filter(Event.event_type == category)

    if difficulty and difficulty != 'all':
        query = query.filter(Event.difficulty_level == difficulty)

    if status and status != 'all':
        query = query.filter(Event.status == status)

    if is_virtual is not None:
        query = query.filter(Event.is_virtual == is_virtual)

    if is_featured is not None:
        query = query.filter(Event.is_featured == is_featured)

    # Only show published events (not draft)
    query = query.filter(Event.status != 'draft')

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * limit
    events = query.order_by(Event.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "events": events,
        "total": total,
        "page": page,
        "page_size": limit
    }


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: Session = Depends(get_db)):
    """
    Get event details by ID

    - **event_id**: Event ID
    """
    service = EventService(db)
    event = service.get_event_by_id(event_id)
    return event


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new event

    Only authenticated users can create events. The creator becomes the organizer.

    Requires: Bearer token in Authorization header
    """
    service = EventService(db)
    event_dict = event_data.model_dump()
    event = service.create_event(event_dict, current_user.id)
    return event


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an event

    Only the event organizer can update the event.

    - **event_id**: Event ID to update

    Requires: Bearer token in Authorization header
    """
    service = EventService(db)
    update_dict = event_data.model_dump(exclude_unset=True)
    event = service.update_event(event_id, update_dict, current_user.id)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an event

    Only the event organizer can delete the event.

    - **event_id**: Event ID to delete

    Requires: Bearer token in Authorization header
    """
    service = EventService(db)
    service.delete_event(event_id, current_user.id)
    return {"message": "Event deleted successfully"}


@router.get("/{event_id}/categories", response_model=list[CategoryResponse])
async def get_event_categories(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all categories for an event

    - **event_id**: Event ID
    """
    service = CategoryService(db)
    categories = service.get_categories_by_event(event_id)
    return categories


@router.post("/{event_id}/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_event_category(
    event_id: int,
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new category for an event

    Only the event organizer can create categories.

    - **event_id**: Event ID

    Requires: Bearer token in Authorization header
    """
    service = CategoryService(db)
    category_dict = category_data.model_dump()
    category = service.create_category(event_id, category_dict, current_user.id)
    return category


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_event_category(
    category_id: int,
    category_data: CategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an event category

    Only the event organizer can update categories.

    - **category_id**: Category ID to update

    Requires: Bearer token in Authorization header
    """
    service = CategoryService(db)
    update_dict = category_data.model_dump(exclude_unset=True)
    category = service.update_category(category_id, update_dict, current_user.id)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_200_OK)
async def delete_event_category(
    category_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an event category

    Only the event organizer can delete categories.

    - **category_id**: Category ID to delete

    Requires: Bearer token in Authorization header
    """
    service = CategoryService(db)
    service.delete_category(category_id, current_user.id)
    return {"message": "Category deleted successfully"}


@router.post("/{event_id}/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_for_event(
    event_id: int,
    registration_data: RegistrationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Register current user for an event

    Requires authentication.

    - **event_id**: Event ID to register for
    - **category_id**: Optional category ID within the event
    - **participant_name**: Name of the participant
    - **age**: Optional age
    - **gender**: Optional gender
    - **t_shirt_size**: Optional t-shirt size
    """
    service = RegistrationService(db)
    registration = service.register_for_event(
        event_id=event_id,
        user_id=current_user.id,
        category_id=registration_data.category_id,
        participant_name=registration_data.participant_name,
        age=registration_data.age,
        gender=registration_data.gender,
        t_shirt_size=registration_data.t_shirt_size
    )
    return registration


@router.delete("/registrations/{registration_id}", status_code=status.HTTP_200_OK)
async def cancel_registration(
    registration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cancel event registration

    Requires authentication. Users can only cancel their own registrations.

    - **registration_id**: Registration ID to cancel
    """
    service = RegistrationService(db)
    service.cancel_registration(registration_id, current_user.id)
    return {"message": "Registration cancelled successfully"}


@router.get("/users/{user_id}/events", response_model=EventListResponse)
async def get_user_events(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get events that a user is registered for

    Requires authentication. Users can only view their own registrations.

    - **user_id**: User ID
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)
    """
    # Check if user is accessing their own data
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own registrations"
        )

    # Get user's registrations
    registrations_query = db.query(Registration).filter(
        Registration.user_id == user_id,
        Registration.status == 'confirmed'
    )

    total = registrations_query.count()

    # Get events through registrations
    offset = (page - 1) * limit
    registrations = registrations_query.offset(offset).limit(limit).all()

    # Get event IDs
    event_ids = [reg.event_id for reg in registrations]

    # Get events
    events = db.query(Event).filter(Event.id.in_(event_ids)).all() if event_ids else []

    return {
        "events": events,
        "total": total,
        "page": page,
        "page_size": limit
    }
