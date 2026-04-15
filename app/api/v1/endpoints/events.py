from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.event import Event, EventType
from app.schemas.event import EventCreate, EventUpdate, EventResponse

router = APIRouter()


@router.get("/", response_model=List[EventResponse])
def get_events(
    skip: int = 0,
    limit: int = 100,
    event_type: Optional[EventType] = None,
    city: Optional[str] = None,
    is_featured: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Get all events with optional filters.
    """
    query = db.query(Event).filter(Event.is_published == True)

    if event_type:
        query = query.filter(Event.event_type == event_type)

    if city:
        query = query.filter(Event.city.ilike(f"%{city}%"))

    if is_featured is not None:
        query = query.filter(Event.is_featured == is_featured)

    events = query.offset(skip).limit(limit).all()
    return events


@router.get("/featured", response_model=List[EventResponse])
def get_featured_events(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get featured events.
    """
    events = db.query(Event).filter(
        Event.is_featured == True,
        Event.is_published == True
    ).offset(skip).limit(limit).all()
    return events


@router.get("/upcoming", response_model=List[EventResponse])
def get_upcoming_events(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get upcoming events.
    """
    events = db.query(Event).filter(
        Event.start_date > datetime.now(),
        Event.is_published == True
    ).order_by(Event.start_date).offset(skip).limit(limit).all()
    return events


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Get event by ID.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return event


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    event: EventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new event (authenticated users only).
    """
    db_event = Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


@router.put("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: int,
    event_update: EventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an event (authenticated users only).
    """
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Update event fields
    update_data = event_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_event, field, value)

    db.commit()
    db.refresh(db_event)
    return db_event


@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an event (authenticated users only).
    """
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    db.delete(db_event)
    db.commit()
    return {"message": "Event deleted successfully"}
