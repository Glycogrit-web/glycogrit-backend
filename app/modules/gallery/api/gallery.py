"""
Gallery API Endpoints
"""

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.modules.gallery.services.gallery_service import GalleryService
from app.modules.gallery.schemas.photo import (
    PhotoSubmitRequest,
    PhotoResponse,
    PhotoApproveRequest,
    PhotoListResponse,
)

router = APIRouter(prefix="/api/v1/gallery", tags=["gallery"])


@router.post("/photos", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
def submit_photo(
    photo_data: PhotoSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit photo to gallery

    Photo will be pending admin approval
    """
    service = GalleryService(db)
    photo = service.submit_photo(
        user_id=current_user.id,
        photo_url=photo_data.photo_url,
        caption=photo_data.caption,
        event_id=photo_data.event_id
    )
    return PhotoResponse.model_validate(photo)


@router.post("/photos/{photo_id}/approve", response_model=PhotoResponse)
def approve_photo(
    photo_id: int,
    approve_data: PhotoApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve photo (admin only)

    Optionally mark as featured
    """
    # TODO: Add admin check
    service = GalleryService(db)
    photo = service.approve_photo(photo_id)

    if approve_data.is_featured:
        photo.is_featured = True
        db.commit()
        db.refresh(photo)

    return PhotoResponse.model_validate(photo)


@router.get("/photos", response_model=List[PhotoResponse])
def get_photos(
    event_id: Optional[int] = Query(None, description="Filter by event"),
    featured_only: bool = Query(False, description="Show only featured photos"),
    limit: int = Query(50, le=100, description="Maximum photos to return"),
    db: Session = Depends(get_db)
):
    """
    Get approved gallery photos

    Public endpoint - returns approved photos only
    """
    service = GalleryService(db)
    photos = service.get_approved_photos(
        event_id=event_id,
        featured_only=featured_only,
        limit=limit
    )
    return [PhotoResponse.model_validate(photo) for photo in photos]


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete photo

    Owner can delete their own photos
    Admin can delete any photo
    """
    service = GalleryService(db)
    service.delete_photo(photo_id, current_user.id)
    return None


@router.get("/photos/my", response_model=List[PhotoResponse])
def get_my_photos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's submitted photos

    Includes pending approval photos
    """
    from app.modules.gallery.domain.photo import GalleryPhoto

    photos = db.query(GalleryPhoto).filter(
        GalleryPhoto.user_id == current_user.id
    ).order_by(GalleryPhoto.created_at.desc()).all()

    return [PhotoResponse.model_validate(photo) for photo in photos]
