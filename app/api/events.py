"""
Event API Endpoints
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, status, Query, Request, Response, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.rate_limit import limiter, RateLimits
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
@limiter.limit(RateLimits.READ_LIST)
async def list_events(
    request: Request,
    response: Response,
    category: Optional[str] = Query(None, description="Filter by event type (running, cycling, walking, mixed, strength)"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (beginner, intermediate, advanced)"),
    status: Optional[str] = Query(None, description="Filter by status (upcoming, ongoing, completed)"),
    is_virtual: Optional[bool] = Query(None, description="Filter virtual events"),
    is_featured: Optional[bool] = Query(None, description="Filter featured events"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
) -> EventListResponse:
    """
    Get list of events with optional filters and pagination.

    Returns a paginated list of published events with optional filtering capabilities.

    Args:
        request: FastAPI Request object (required for rate limiting)
        category: Filter by event type (running, cycling, walking, mixed, strength)
        difficulty: Filter by difficulty level (beginner, intermediate, advanced)
        status: Filter by event status (upcoming, ongoing, completed)
        is_virtual: Filter virtual events only
        is_featured: Filter featured events only
        page: Page number (default: 1)
        limit: Items per page (default: 20, max: 100)
        db: Database session dependency

    Returns:
        EventListResponse: Paginated list of events with total count

    Rate Limit:
        60 requests per minute
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
@limiter.limit(RateLimits.READ_DETAIL)
async def get_event(
    request: Request,
    response: Response,
    event_id: int,
    db: Session = Depends(get_db)
) -> EventResponse:
    """
    Get event details by ID.

    Returns detailed information about a specific event including categories.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to retrieve
        db: Database session dependency

    Returns:
        EventResponse: Event details

    Raises:
        NotFoundException: If event not found

    Rate Limit:
        100 requests per minute
    """
    service: EventService = EventService(db)
    event: EventResponse = service.get_event_by_id(event_id)
    return event


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def create_event(
    request: Request,
    event_data: EventCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> EventResponse:
    """
    Create a new event.

    Creates a new event with the authenticated user as the organizer.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_data: Event creation data
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        EventResponse: Created event details

    Raises:
        ValidationException: If event data is invalid

    Rate Limit:
        20 requests per minute

    Authorization:
        Only authenticated users can create events

    Requires:
        Bearer token in Authorization header
    """
    service: EventService = EventService(db)
    event_dict: Dict[str, Any] = event_data.model_dump()
    event: EventResponse = service.create_event(event_dict, current_user.id)
    return event


@router.put("/{event_id}", response_model=EventResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def update_event(
    request: Request,
    event_id: int,
    event_data: EventUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> EventResponse:
    """
    Update an event.

    Updates an existing event. Only the event organizer can update.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to update
        event_data: Updated event data
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        EventResponse: Updated event details

    Raises:
        NotFoundException: If event not found
        PermissionDeniedException: If user is not the event organizer

    Rate Limit:
        30 requests per minute

    Authorization:
        Only the event organizer can update the event

    Requires:
        Bearer token in Authorization header
    """
    service: EventService = EventService(db)
    update_dict: Dict[str, Any] = event_data.model_dump(exclude_unset=True)
    event: EventResponse = service.update_event(event_id, update_dict, current_user.id)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.WRITE_DELETE)
async def delete_event(
    request: Request,
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete an event.

    Deletes an existing event. Only the event organizer can delete.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to delete
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        Dict with success message

    Raises:
        NotFoundException: If event not found
        PermissionDeniedException: If user is not the event organizer

    Rate Limit:
        10 requests per minute

    Authorization:
        Only the event organizer can delete the event

    Requires:
        Bearer token in Authorization header
    """
    service: EventService = EventService(db)
    service.delete_event(event_id, current_user.id)
    return {"message": "Event deleted successfully"}


@router.get("/{event_id}/categories", response_model=List[CategoryResponse])
@limiter.limit(RateLimits.READ_DETAIL)
async def get_event_categories(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db)
) -> List[CategoryResponse]:
    """
    Get all categories for an event.

    Returns all registration categories available for a specific event.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID
        db: Database session dependency

    Returns:
        List of CategoryResponse objects

    Raises:
        NotFoundException: If event not found

    Rate Limit:
        100 requests per minute
    """
    service: CategoryService = CategoryService(db)
    categories: List[CategoryResponse] = service.get_categories_by_event(event_id)
    return categories


@router.post("/{event_id}/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def create_event_category(
    request: Request,
    event_id: int,
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> CategoryResponse:
    """
    Create a new category for an event.

    Creates a registration category for an event (e.g., 5K, 10K, Marathon).

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to add category to
        category_data: Category creation data
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        CategoryResponse: Created category details

    Raises:
        NotFoundException: If event not found
        PermissionDeniedException: If user is not the event organizer

    Rate Limit:
        20 requests per minute

    Authorization:
        Only the event organizer can create categories

    Requires:
        Bearer token in Authorization header
    """
    service: CategoryService = CategoryService(db)
    category_dict: Dict[str, Any] = category_data.model_dump()
    category: CategoryResponse = service.create_category(event_id, category_dict, current_user.id)
    return category


@router.put("/categories/{category_id}", response_model=CategoryResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def update_event_category(
    request: Request,
    category_id: int,
    category_data: CategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> CategoryResponse:
    """
    Update an event category.

    Updates an existing event category. Only the event organizer can update.

    Args:
        request: FastAPI Request object (required for rate limiting)
        category_id: Category ID to update
        category_data: Updated category data
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        CategoryResponse: Updated category details

    Raises:
        NotFoundException: If category not found
        PermissionDeniedException: If user is not the event organizer

    Rate Limit:
        30 requests per minute

    Authorization:
        Only the event organizer can update categories

    Requires:
        Bearer token in Authorization header
    """
    service: CategoryService = CategoryService(db)
    update_dict: Dict[str, Any] = category_data.model_dump(exclude_unset=True)
    category: CategoryResponse = service.update_category(category_id, update_dict, current_user.id)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.WRITE_DELETE)
async def delete_event_category(
    request: Request,
    category_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete an event category.

    Deletes an existing event category. Only the event organizer can delete.

    Args:
        request: FastAPI Request object (required for rate limiting)
        category_id: Category ID to delete
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        Dict with success message

    Raises:
        NotFoundException: If category not found
        PermissionDeniedException: If user is not the event organizer

    Rate Limit:
        10 requests per minute

    Authorization:
        Only the event organizer can delete categories

    Requires:
        Bearer token in Authorization header
    """
    service: CategoryService = CategoryService(db)
    service.delete_category(category_id, current_user.id)
    return {"message": "Category deleted successfully"}


@router.post("/{event_id}/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def register_for_event(
    request: Request,
    event_id: int,
    registration_data: RegistrationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> RegistrationResponse:
    """
    Register current user for an event.

    Creates a new registration for the authenticated user for a specific event.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to register for
        registration_data: Registration data (category, participant name, etc.)
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        RegistrationResponse: Created registration details

    Raises:
        NotFoundException: If event or category not found
        AlreadyExistsException: If user already registered for this event
        ValidationException: If registration data is invalid

    Rate Limit:
        20 requests per minute

    Requires:
        Bearer token in Authorization header
    """
    service: RegistrationService = RegistrationService(db)
    registration: RegistrationResponse = service.register_for_event(
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
@limiter.limit(RateLimits.WRITE_DELETE)
async def cancel_registration(
    request: Request,
    registration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Cancel event registration.

    Cancels an existing registration. Users can only cancel their own registrations.

    Args:
        request: FastAPI Request object (required for rate limiting)
        registration_id: Registration ID to cancel
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        Dict with success message

    Raises:
        NotFoundException: If registration not found
        PermissionDeniedException: If user is not the registration owner

    Rate Limit:
        10 requests per minute

    Authorization:
        Users can only cancel their own registrations

    Requires:
        Bearer token in Authorization header
    """
    service: RegistrationService = RegistrationService(db)
    service.cancel_registration(registration_id, current_user.id)
    return {"message": "Registration cancelled successfully"}


@router.get("/users/{user_id}/events", response_model=EventListResponse)
@limiter.limit(RateLimits.READ_LIST)
async def get_user_events(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
) -> EventListResponse:
    """
    Get events that a user is registered for.

    Returns paginated list of events the user has registered for.

    Args:
        request: FastAPI Request object (required for rate limiting)
        user_id: User ID
        current_user: Current authenticated user from JWT token
        page: Page number (default: 1)
        limit: Items per page (default: 20, max: 100)
        db: Database session dependency

    Returns:
        EventListResponse: Paginated list of registered events

    Raises:
        PermissionDeniedException: If user tries to view another user's registrations

    Rate Limit:
        60 requests per minute

    Authorization:
        Users can only view their own registrations

    Requires:
        Bearer token in Authorization header
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

    total: int = registrations_query.count()

    # Get events through registrations
    offset: int = (page - 1) * limit
    registrations: List[Registration] = registrations_query.offset(offset).limit(limit).all()

    # Get event IDs
    event_ids: List[int] = [reg.event_id for reg in registrations]

    # Get events
    events: List[Event] = db.query(Event).filter(Event.id.in_(event_ids)).all() if event_ids else []

    return {
        "events": events,
        "total": total,
        "page": page,
        "page_size": limit
    }
