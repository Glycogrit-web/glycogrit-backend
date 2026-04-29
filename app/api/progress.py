"""
Progress Management API
Handles proof upload and admin manual progress updates
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.strava_connection import UserChallengeProgress
from app.models.event import Event
from app.services.storage_service import storage_service
from pydantic import BaseModel


router = APIRouter(prefix="/api/progress", tags=["progress"])


# Pydantic Schemas
class ProofUploadResponse(BaseModel):
    message: str
    proof_image_url: str


class AdminProgressUpdateRequest(BaseModel):
    user_id: int
    total_distance_km: float
    notes: Optional[str] = None


class AdminProgressUpdateResponse(BaseModel):
    message: str
    total_distance_km: float
    progress_percentage: float


@router.post("/{event_id}/upload-proof", response_model=ProofUploadResponse)
async def upload_proof_image(
    event_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload progress proof image for an event

    User can upload one proof image per event. Uploading a new image replaces the old one.
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Get or create progress record
    progress = db.query(UserChallengeProgress).filter(
        and_(
            UserChallengeProgress.user_id == current_user.id,
            UserChallengeProgress.challenge_id == event_id
        )
    ).first()

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )

    # Delete old proof image if exists
    if progress and progress.proof_image_url:
        try:
            await storage_service.delete_proof_image(progress.proof_image_url)
        except Exception as e:
            # Log but don't fail if old image deletion fails
            pass

    # Upload new proof image
    try:
        image_url = await storage_service.upload_proof_image(
            file_content=file_content,
            user_id=current_user.id,
            event_id=event_id,
            filename=file.filename or "proof.jpg"
        )

        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image to storage"
            )

        # Update or create progress record with proof URL
        if progress:
            progress.proof_image_url = image_url
            progress.updated_at = datetime.now(timezone.utc)
        else:
            # Create new progress record
            progress = UserChallengeProgress(
                user_id=current_user.id,
                challenge_id=event_id,
                total_distance_km=0,
                total_activities=0,
                progress_percentage=0,
                proof_image_url=image_url
            )
            db.add(progress)

        db.commit()

        return ProofUploadResponse(
            message="Proof image uploaded successfully",
            proof_image_url=image_url
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload proof image: {str(e)}"
        )


@router.delete("/{event_id}/delete-proof")
async def delete_proof_image(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user's proof image for an event
    """
    # Get progress record
    progress = db.query(UserChallengeProgress).filter(
        and_(
            UserChallengeProgress.user_id == current_user.id,
            UserChallengeProgress.challenge_id == event_id
        )
    ).first()

    if not progress or not progress.proof_image_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No proof image found"
        )

    # Delete image from storage
    try:
        await storage_service.delete_proof_image(progress.proof_image_url)
    except Exception as e:
        # Continue even if storage deletion fails
        pass

    # Remove URL from database
    progress.proof_image_url = None
    progress.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Proof image deleted successfully"}


@router.post("/{event_id}/admin-update", response_model=AdminProgressUpdateResponse)
async def admin_update_progress(
    event_id: int,
    update_data: AdminProgressUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin manually updates user's progress

    Only admins can use this endpoint to update any user's progress.
    """
    # Check if current user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manually update user progress"
        )

    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Get or create progress record
    progress = db.query(UserChallengeProgress).filter(
        and_(
            UserChallengeProgress.user_id == update_data.user_id,
            UserChallengeProgress.challenge_id == event_id
        )
    ).first()

    # Calculate progress percentage
    goal_distance = int(event.total_distance) if event.total_distance else 0
    progress_pct = (update_data.total_distance_km / goal_distance * 100) if goal_distance > 0 else 0

    sync_time = datetime.now(timezone.utc)

    if progress:
        # Update existing progress
        progress.total_distance_km = int(update_data.total_distance_km)
        progress.goal_distance_km = goal_distance  # Always update goal from event
        progress.progress_percentage = int(progress_pct)  # Don't cap at 100 to show overachievement
        progress.last_sync_source = 'admin_manual'
        progress.last_sync_at = sync_time
        progress.last_synced_by_user_id = current_user.id
        progress.updated_at = sync_time
    else:
        # Create new progress record
        progress = UserChallengeProgress(
            user_id=update_data.user_id,
            challenge_id=event_id,
            total_distance_km=int(update_data.total_distance_km),
            total_activities=0,
            goal_distance_km=goal_distance,
            progress_percentage=int(progress_pct),  # Don't cap at 100 to show overachievement
            last_sync_source='admin_manual',
            last_sync_at=sync_time,
            last_synced_by_user_id=current_user.id
        )
        db.add(progress)

    db.commit()
    db.refresh(progress)

    return AdminProgressUpdateResponse(
        message="Progress updated successfully by admin",
        total_distance_km=float(progress.total_distance_km),
        progress_percentage=float(progress.progress_percentage)
    )
