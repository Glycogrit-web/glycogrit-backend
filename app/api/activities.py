"""
Activity API Endpoints
"""
from typing import Optional, Dict, List
from datetime import date
from fastapi import APIRouter, Depends, status, Query, Request, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.rate_limit import limiter, RateLimits
from app.schemas.activity import ActivitySubmit, ActivityUpdate, ActivityResponse, ActivityListResponse
from app.models.user import User
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/api/v1", tags=["Activities"])


@router.post("/events/{event_id}/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def submit_activity(
    request: Request,
    response: Response,
    event_id: int,
    activity_data: ActivitySubmit,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ActivityResponse:
    """
    Submit activity for an event.

    Creates a new activity submission for a specific event.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to submit activity for
        activity_data: Activity submission data (distance, duration, date, notes)
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        ActivityResponse: Created activity details

    Raises:
        NotFoundException: If event not found
        ValidationException: If activity data is invalid

    Rate Limit:
        20 requests per minute

    Requires:
        Bearer token in Authorization header
    """
    service: ActivityService = ActivityService(db)
    activity_dict: Dict = activity_data.model_dump()
    activity: ActivityResponse = service.create_activity(current_user.id, event_id, activity_dict)
    return activity


@router.get("/users/{user_id}/activities", response_model=ActivityListResponse)
@limiter.limit(RateLimits.READ_LIST)
async def get_user_activities(
    request: Request,
    response: Response,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
) -> ActivityListResponse:
    """
    Get user's activity history.

    Returns paginated list of user's activities with optional event filtering.

    Args:
        request: FastAPI Request object (required for rate limiting)
        user_id: User ID
        current_user: Current authenticated user from JWT token
        event_id: Optional filter by event ID
        page: Page number (default: 1)
        limit: Items per page (default: 20, max: 100)
        db: Database session dependency

    Returns:
        ActivityListResponse: Paginated list of activities

    Raises:
        PermissionDeniedException: If user tries to view another user's activities

    Rate Limit:
        60 requests per minute

    Authorization:
        Users can only view their own activities

    Requires:
        Bearer token in Authorization header
    """
    from app.core.permissions import PermissionChecker
    PermissionChecker.require_owner(user_id, current_user.id, "activities")

    service: ActivityService = ActivityService(db)
    offset: int = (page - 1) * limit

    if event_id:
        activities: List = service.get_activities_by_user_and_event(user_id, event_id, offset, limit)
        total: int = len(activities)
    else:
        activities: List = service.get_activities_by_user(user_id, offset, limit)
        total: int = len(activities)

    return {
        "activities": activities,
        "total": total,
        "page": page,
        "page_size": limit
    }


@router.get("/events/{event_id}/activities", response_model=ActivityListResponse)
@limiter.limit(RateLimits.READ_LIST)
async def get_event_activities(
    request: Request,
    response: Response,
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
) -> ActivityListResponse:
    """
    Get all activities for an event.

    Returns paginated list of current user's activities for a specific event.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID
        current_user: Current authenticated user from JWT token
        page: Page number (default: 1)
        limit: Items per page (default: 20, max: 100)
        db: Database session dependency

    Returns:
        ActivityListResponse: Paginated list of user's activities for the event

    Raises:
        NotFoundException: If event not found

    Rate Limit:
        60 requests per minute

    Requires:
        Bearer token in Authorization header
    """
    service: ActivityService = ActivityService(db)
    offset: int = (page - 1) * limit

    # Get current user's activities for this event
    activities: List = service.get_activities_by_user_and_event(current_user.id, event_id, offset, limit)
    total: int = len(activities)

    return {
        "activities": activities,
        "total": total,
        "page": page,
        "page_size": limit
    }


@router.put("/activities/{activity_id}", response_model=ActivityResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def update_activity(
    request: Request,
    response: Response,
    activity_id: int,
    activity_data: ActivityUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ActivityResponse:
    """
    Update an activity.

    Updates an existing activity. Only the activity owner can update.

    Args:
        request: FastAPI Request object (required for rate limiting)
        activity_id: Activity ID to update
        activity_data: Updated activity data
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        ActivityResponse: Updated activity details

    Raises:
        NotFoundException: If activity not found
        PermissionDeniedException: If user is not the activity owner

    Rate Limit:
        30 requests per minute

    Authorization:
        Only the activity owner can update it

    Requires:
        Bearer token in Authorization header
    """
    service: ActivityService = ActivityService(db)
    update_dict: Dict = activity_data.model_dump(exclude_unset=True)
    activity: ActivityResponse = service.update_activity(activity_id, update_dict, current_user.id)
    return activity


@router.delete("/activities/{activity_id}", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.WRITE_DELETE)
async def delete_activity(
    request: Request,
    response: Response,
    activity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete an activity.

    Deletes an existing activity. Only the activity owner can delete.

    Args:
        request: FastAPI Request object (required for rate limiting)
        activity_id: Activity ID to delete
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        Dict with success message

    Raises:
        NotFoundException: If activity not found
        PermissionDeniedException: If user is not the activity owner

    Rate Limit:
        10 requests per minute

    Authorization:
        Only the activity owner can delete it

    Requires:
        Bearer token in Authorization header
    """
    service: ActivityService = ActivityService(db)
    service.delete_activity(activity_id, current_user.id)
    return {"message": "Activity deleted successfully"}
