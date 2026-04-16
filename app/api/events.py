"""
Event API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.schemas.event import EventResponse, EventListResponse, EventRegisterRequest, EventRegisterResponse
from app.models.user import User
from app.models.event import Event
from app.models.registration import Registration

router = APIRouter(prefix="/api/v1/events", tags=["Events"])


@router.get("", response_model=EventListResponse)
async def list_events(
    category: Optional[str] = Query(None, description="Filter by event type (running, cycling, walking, mixed, strength)"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (beginner, intermediate, advanced)"),
    status: Optional[str] = Query(None, description="Filter by status (upcoming, ongoing, completed)"),
    is_virtual: Optional[bool] = Query(None, description="Filter virtual events"),
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
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    return event


@router.post("/{event_id}/register", response_model=EventRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_for_event(
    event_id: int,
    registration_data: EventRegisterRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Register current user for an event

    Requires authentication.

    - **event_id**: Event ID to register for
    - **category_id**: Optional category ID within the event
    """
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Check if event is open for registration
    if event.status not in ['upcoming', 'ongoing']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event is not open for registration"
        )

    # Check if user is already registered
    existing_registration = db.query(Registration).filter(
        Registration.user_id == current_user.id,
        Registration.event_id == event_id
    ).first()

    if existing_registration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already registered for this event"
        )

    # Check max participants
    if event.max_participants and event.current_participants >= event.max_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event is full"
        )

    # Create registration
    new_registration = Registration(
        user_id=current_user.id,
        event_id=event_id,
        category_id=registration_data.category_id,
        status='confirmed',
        payment_status='pending' if event.registration_fee and event.registration_fee > 0 else 'not_required'
    )

    db.add(new_registration)

    # Increment participant count
    event.current_participants += 1

    db.commit()
    db.refresh(new_registration)

    return new_registration


@router.delete("/registrations/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
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
    # Find registration
    registration = db.query(Registration).filter(Registration.id == registration_id).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )

    # Check ownership
    if registration.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own registrations"
        )

    # Check if already cancelled
    if registration.status == 'cancelled':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is already cancelled"
        )

    # Update status
    registration.status = 'cancelled'

    # Decrement participant count
    event = db.query(Event).filter(Event.id == registration.event_id).first()
    if event and event.current_participants > 0:
        event.current_participants -= 1

    db.commit()


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
