"""
Activity API Endpoints
"""
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.schemas.activity import ActivitySubmit, ActivityUpdate, ActivityResponse, ActivityListResponse
from app.models.user import User
from app.services.activity_service import ActivityService

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

    Requires authentication.

    - **event_id**: Event ID
    - **distance**: Distance in kilometers (optional)
    - **duration**: Duration in minutes (optional)
    - **activity_date**: Date of activity
    - **notes**: Optional notes about the activity
    """
    service = ActivityService(db)
    activity_dict = activity_data.model_dump()
    activity = service.create_activity(current_user.id, event_id, activity_dict)
    return activity


@router.get("/users/{user_id}/activities", response_model=ActivityListResponse)
async def get_user_activities(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get user's activity history

    Requires authentication. Users can only view their own activities.

    - **user_id**: User ID
    - **event_id**: Optional filter by event ID
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)
    """
    from app.core.permissions import PermissionChecker
    PermissionChecker.require_owner(user_id, current_user.id, "activities")

    service = ActivityService(db)
    offset = (page - 1) * limit

    if event_id:
        activities = service.get_activities_by_user_and_event(user_id, event_id, offset, limit)
        total = len(activities)
    else:
        activities = service.get_activities_by_user(user_id, offset, limit)
        total = len(activities)

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
    service = ActivityService(db)
    offset = (page - 1) * limit

    # Get current user's activities for this event
    activities = service.get_activities_by_user_and_event(current_user.id, event_id, offset, limit)
    total = len(activities)

    return {
        "activities": activities,
        "total": total,
        "page": page,
        "page_size": limit
    }


@router.put("/activities/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: int,
    activity_data: ActivityUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an activity

    Only the activity owner can update it.

    - **activity_id**: Activity ID to update

    Requires: Bearer token in Authorization header
    """
    service = ActivityService(db)
    update_dict = activity_data.model_dump(exclude_unset=True)
    activity = service.update_activity(activity_id, update_dict, current_user.id)
    return activity


@router.delete("/activities/{activity_id}", status_code=status.HTTP_200_OK)
async def delete_activity(
    activity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an activity

    Only the activity owner can delete it.

    - **activity_id**: Activity ID to delete

    Requires: Bearer token in Authorization header
    """
    service = ActivityService(db)
    service.delete_activity(activity_id, current_user.id)
    return {"message": "Activity deleted successfully"}
