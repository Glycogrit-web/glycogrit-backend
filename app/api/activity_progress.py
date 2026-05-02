"""
Activity Progress API Endpoints
Handles activity progress tracking for event participants
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.activity_progress import ActivityProgress
from app.models.registration import Registration
from app.schemas.activity_progress import (
    ActivityProgressCreate,
    ActivityProgressResponse,
    ManualDistanceEntry,
    ActivityProgressUpdate,
    ActivityProgressList
)
from app.core.rate_limit import limiter, RateLimits
from decimal import Decimal
from sqlalchemy.sql import func

router = APIRouter(prefix="/api/v1/activity-progress", tags=["Activity Progress"])


@router.post("", response_model=ActivityProgressResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def create_activity_progress(
    request: Request,
    response: Response,
    progress_data: ActivityProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create activity progress record for a registration.
    Automatically created when user registers for an event with activities.
    """
    # Verify registration belongs to current user
    registration = db.query(Registration).filter(
        Registration.id == progress_data.registration_id,
        Registration.user_id == current_user.id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found or access denied"
        )

    # Check if progress already exists for this registration
    existing_progress = db.query(ActivityProgress).filter(
        ActivityProgress.registration_id == progress_data.registration_id
    ).first()

    if existing_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Activity progress already exists for this registration"
        )

    # Create new progress record
    # Note: progress_percentage and is_completed are computed properties
    new_progress = ActivityProgress(
        user_id=current_user.id,
        registration_id=progress_data.registration_id,
        event_id=registration.event_id,
        activity_id=progress_data.activity_id,
        target_distance=progress_data.target_distance,
        distance_completed=Decimal("0.00")
    )

    db.add(new_progress)
    db.commit()
    db.refresh(new_progress)

    return new_progress


@router.get("/my-progress", response_model=ActivityProgressList)
@limiter.limit(RateLimits.READ_LIST)
async def get_my_progress(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all activity progress records for the current user.
    """
    progress_records = db.query(ActivityProgress).filter(
        ActivityProgress.user_id == current_user.id
    ).order_by(ActivityProgress.created_at.desc()).all()

    return {
        "progress_records": progress_records,
        "total": len(progress_records)
    }


@router.get("/registration/{registration_id}", response_model=ActivityProgressResponse)
@limiter.limit(RateLimits.READ_LIST)
async def get_progress_by_registration(
    request: Request,
    response: Response,
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get activity progress for a specific registration.
    Includes activity details (name, type, distance).
    """
    progress = db.query(ActivityProgress).options(
        joinedload(ActivityProgress.activity)
    ).filter(
        ActivityProgress.registration_id == registration_id,
        ActivityProgress.user_id == current_user.id
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity progress not found"
        )

    # Populate activity details from relationship
    progress_dict = {
        **{k: v for k, v in progress.__dict__.items() if not k.startswith('_')},
        "progress_percentage": progress.progress_percentage,  # Computed property
        "is_completed": progress.is_completed,  # Computed property
        "progress_display": progress.progress_display,
        "remaining_distance": progress.remaining_distance,
        "activity_name": progress.activity.name if progress.activity else None,
        "activity_type": progress.activity.activity_type if progress.activity else None,
        "activity_distance": progress.activity.distance if progress.activity else None,
    }

    return ActivityProgressResponse(**progress_dict)


@router.get("/event/{event_id}/my-progress", response_model=ActivityProgressResponse)
@limiter.limit(RateLimits.READ_LIST)
async def get_my_event_progress(
    request: Request,
    response: Response,
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get activity progress for the current user in a specific event.
    Includes activity details (name, type, distance).
    """
    progress = db.query(ActivityProgress).options(
        joinedload(ActivityProgress.activity)
    ).filter(
        ActivityProgress.event_id == event_id,
        ActivityProgress.user_id == current_user.id
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity progress not found for this event"
        )

    # Populate activity details from relationship
    progress_dict = {
        **{k: v for k, v in progress.__dict__.items() if not k.startswith('_')},
        "progress_percentage": progress.progress_percentage,  # Computed property
        "is_completed": progress.is_completed,  # Computed property
        "progress_display": progress.progress_display,
        "remaining_distance": progress.remaining_distance,
        "activity_name": progress.activity.name if progress.activity else None,
        "activity_type": progress.activity.activity_type if progress.activity else None,
        "activity_distance": progress.activity.distance if progress.activity else None,
    }

    return ActivityProgressResponse(**progress_dict)


@router.post("/{progress_id}/add-distance", response_model=ActivityProgressResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def add_manual_distance(
    request: Request,
    response: Response,
    progress_id: int,
    distance_entry: ManualDistanceEntry,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually add distance to activity progress.
    Used before Strava integration is implemented.
    """
    progress = db.query(ActivityProgress).filter(
        ActivityProgress.id == progress_id,
        ActivityProgress.user_id == current_user.id
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity progress not found"
        )

    if progress.is_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Activity already completed. No more distance can be added."
        )

    # Add distance
    progress.distance_completed += distance_entry.distance
    progress.last_manual_entry = distance_entry.distance
    progress.last_manual_entry_at = func.now()
    progress.sync_source = "manual"
    progress.last_sync_at = func.now()

    # Note: progress_percentage is now a computed property

    # Check if completed (is_completed is now a computed property)
    if progress.is_completed and not progress.completed_at:
        progress.completed_at = func.now()

    db.commit()
    db.refresh(progress)

    return progress


@router.delete("/{progress_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RateLimits.WRITE_DELETE)
async def delete_activity_progress(
    request: Request,
    response: Response,
    progress_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete activity progress record.
    Only the user who owns the progress can delete it.
    """
    progress = db.query(ActivityProgress).filter(
        ActivityProgress.id == progress_id,
        ActivityProgress.user_id == current_user.id
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity progress not found"
        )

    db.delete(progress)
    db.commit()

    return None


@router.get("/event/{event_id}/leaderboard", response_model=List[ActivityProgressResponse])
@limiter.limit(RateLimits.READ_LIST)
async def get_event_leaderboard(
    request: Request,
    response: Response,
    event_id: int,
    db: Session = Depends(get_db),
    limit: int = 10
):
    """
    Get leaderboard for an event (top participants by distance completed).
    Public endpoint - no authentication required.
    """
    leaderboard = db.query(ActivityProgress).filter(
        ActivityProgress.event_id == event_id
    ).order_by(
        ActivityProgress.distance_completed.desc(),
        ActivityProgress.completed_at.asc()
    ).limit(limit).all()

    return leaderboard
