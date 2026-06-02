"""
Gallery API Endpoints
"""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.modules.gallery.schemas.photo import (
    PhotoApproveRequest,
    PhotoResponse,
    PhotoSubmitRequest,
)
from app.modules.gallery.services.gallery_service import GalleryService

router = APIRouter(prefix="/gallery", tags=["gallery"])


@router.post("/photos", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
def submit_photo(
    photo_data: PhotoSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        event_id=photo_data.event_id,
    )
    return PhotoResponse.model_validate(photo)


@router.post("/submit", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def submit_photo_with_upload(
    fullName: str = Form(...),
    email: str = Form(...),
    city: str = Form(...),
    challengeName: str = Form(...),
    story: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit photo to gallery with file upload

    User uploads photo directly - will be pending admin approval.
    Combines user information into caption field.
    """
    from app.modules.gallery.services.storage_service import StorageService

    # Read uploaded file
    file_content = await photo.read()

    # Upload to R2
    storage = StorageService()
    image_url = await storage.upload_gallery_photo(
        file_content, current_user.id, photo.filename or "photo.jpg"
    )

    if not image_url:
        from app.core.exceptions import ValidationException
        raise ValidationException("Failed to upload image")

    # Format caption with user information
    caption = f"{fullName} from {city}\nChallenge: {challengeName}\n\n{story}"

    # Save to database
    service = GalleryService(db)
    photo_record = service.submit_photo(
        user_id=current_user.id,
        photo_url=image_url,
        caption=caption,
        event_id=None,  # No event association for now
    )

    return PhotoResponse.model_validate(photo_record)


@router.post("/photos/{photo_id}/approve", response_model=PhotoResponse)
def approve_photo(
    photo_id: int,
    approve_data: PhotoApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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


@router.get("/photos")
async def get_photos(
    event_id: int | None = Query(None, description="Filter by event"),
    featured_only: bool = Query(False, description="Show only featured photos"),
    limit: int = Query(50, le=100, description="Maximum photos to return"),
):
    """
    Get gallery photos from Instagram

    Fetches photos directly from Instagram API
    """
    import httpx
    from app.core.config import settings

    # Check if Instagram is configured
    if not settings.instagram_access_token or not settings.instagram_account_id:
        return {
            "error": "Instagram not configured",
            "photos": [],
            "message": "Instagram API credentials not set"
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch media from Instagram
            url = f"https://graph.facebook.com/v18.0/{settings.instagram_account_id}/media"
            params = {
                "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp",
                "access_token": settings.instagram_access_token,
                "limit": limit
            }

            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            photos = data.get("data", [])

            return {
                "photos": photos,
                "count": len(photos)
            }

    except Exception as e:
        return {
            "error": str(e),
            "photos": [],
            "message": "Failed to fetch photos from Instagram"
        }


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Delete photo

    Owner can delete their own photos
    Admin can delete any photo
    """
    service = GalleryService(db)
    service.delete_photo(photo_id, current_user.id)
    return None


@router.get("/photos/my", response_model=list[PhotoResponse])
def get_my_photos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get current user's submitted photos

    Includes pending approval photos
    """
    from app.modules.gallery.domain.photo import GalleryPhoto

    photos = (
        db.query(GalleryPhoto)
        .filter(GalleryPhoto.user_id == current_user.id)
        .order_by(GalleryPhoto.created_at.desc())
        .all()
    )

    return [PhotoResponse.model_validate(photo) for photo in photos]
