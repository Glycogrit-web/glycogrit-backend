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
from app.models.activity_progress import ActivityProgress
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

    # Get ActivityProgress record
    progress = db.query(ActivityProgress).filter(
        and_(
            ActivityProgress.user_id == current_user.id,
            ActivityProgress.event_id == event_id
        )
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registration found for this event. Please register first."
        )

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )

    # Delete old proof image if exists
    if progress.proof_image_url:
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

        # Update progress record with proof URL
        progress.proof_image_url = image_url
        progress.updated_at = datetime.now(timezone.utc)

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
    # Get ActivityProgress record
    progress = db.query(ActivityProgress).filter(
        and_(
            ActivityProgress.user_id == current_user.id,
            ActivityProgress.event_id == event_id
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
    Uses "highest value wins" logic - will only update if new value is higher than current.
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

    # Get ActivityProgress record
    progress = db.query(ActivityProgress).filter(
        and_(
            ActivityProgress.user_id == update_data.user_id,
            ActivityProgress.event_id == event_id
        )
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registration found for this user in this event"
        )

    # Apply highest-wins logic
    from app.services.progress_validation_service import ProgressValidationService

    result = ProgressValidationService.validate_and_update_progress(
        progress=progress,
        new_distance_km=update_data.total_distance_km,
        source='admin_manual',
        metadata={
            'notes': update_data.notes,
            'admin_user_id': current_user.id,
            'admin_email': current_user.email
        }
    )

    if not result['updated'] and result['reason'] == 'lower_value':
        # Return error when trying to set lower value
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Cannot update progress - value too low",
                "current_distance_km": result['current_distance'],
                "attempted_distance_km": result['attempted_distance'],
                "current_source": result['source'],
                "current_source_display": result['source_display'],
                "message": result['message']
            }
        )

    db.commit()
    db.refresh(progress)

    return AdminProgressUpdateResponse(
        message=result['message'],
        total_distance_km=float(progress.distance_completed),
        progress_percentage=float(progress.progress_percentage)
    )
