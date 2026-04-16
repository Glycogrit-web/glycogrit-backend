"""
Activity API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.schemas.activity import ActivitySubmit, ActivityResponse, ActivityListResponse
from app.models.user import User
from app.models.event import Event
from app.models.activity import EventActivity
from app.models.registration import Registration

router = APIRouter(prefix="/api/v1", tags=["Activities"])


@router.post("/events/{event_id}/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def submit_activity(
    event_id: int,
    activity_data: ActivitySubmit,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Submit activity for an event

    Requires authentication. User must be registered for the event.

    - **event_id**: Event ID
    - **distance**: Distance in kilometers (optional)
    - **duration**: Duration in minutes (optional)
    - **activity_date**: Date of activity
    - **notes**: Optional notes about the activity
    """
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Check if user is registered for the event
    registration = db.query(Registration).filter(
        Registration.user_id == current_user.id,
        Registration.event_id == event_id,
        Registration.status == 'confirmed'
    ).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be registered for this event to submit activities"
        )

    # Validate activity date is within event dates
    if event.start_date and activity_data.activity_date < event.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Activity date cannot be before event start date"
        )

    if event.end_date and activity_data.activity_date > event.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Activity date cannot be after event end date"
        )

    # Create activity
    new_activity = EventActivity(
        user_id=current_user.id,
        event_id=event_id,
        registration_id=registration.id,
        distance=activity_data.distance,
        duration=activity_data.duration,
        activity_date=activity_data.activity_date,
        notes=activity_data.notes
    )

    db.add(new_activity)
    db.commit()
    db.refresh(new_activity)

    return new_activity


@router.get("/users/{user_id}/activities", response_model=ActivityListResponse)
async def get_user_activities(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    start_date: Optional[date] = Query(None, description="Filter activities from this date"),
    end_date: Optional[date] = Query(None, description="Filter activities until this date"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get user's activity history

    Requires authentication. Users can only view their own activities.

    - **user_id**: User ID
    - **event_id**: Optional filter by event ID
    - **start_date**: Optional filter from date
    - **end_date**: Optional filter until date
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)
    """
    # Check if user is accessing their own data
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own activities"
        )

    # Build query
    query = db.query(EventActivity).filter(EventActivity.user_id == user_id)

    # Apply filters
    if event_id:
        query = query.filter(EventActivity.event_id == event_id)

    if start_date:
        query = query.filter(EventActivity.activity_date >= start_date)

    if end_date:
        query = query.filter(EventActivity.activity_date <= end_date)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * limit
    activities = query.order_by(EventActivity.activity_date.desc()).offset(offset).limit(limit).all()

    return {
        "activities": activities,
        "total": total,
        "page": page,
        "page_size": limit
    }


@router.get("/events/{event_id}/activities", response_model=ActivityListResponse)
async def get_event_activities(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get all activities for an event

    Requires authentication. Only returns the current user's activities for the event.

    - **event_id**: Event ID
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)
    """
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Get current user's activities for this event
    query = db.query(EventActivity).filter(
        EventActivity.event_id == event_id,
        EventActivity.user_id == current_user.id
    )

    total = query.count()

    # Apply pagination
    offset = (page - 1) * limit
    activities = query.order_by(EventActivity.activity_date.desc()).offset(offset).limit(limit).all()

    return {
        "activities": activities,
        "total": total,
        "page": page,
        "page_size": limit
    }
