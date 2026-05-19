from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_optional_current_user
from app.core.rate_limit import limiter
from app.models.user import User
from app.services.instagram_service import InstagramService
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/gallery",
    tags=["gallery"]
)

@router.post("/submit")
@limiter.limit("3/hour")  # Limit to 3 submissions per hour per IP
async def submit_gallery_photo(
    request: Request,
    fullName: str = Form(...),
    email: str = Form(...),
    city: str = Form(...),
    challengeName: str = Form(...),
    story: str = Form(...),
    photo: UploadFile = File(...),
    current_user: User = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a photo to the Hall of Achievers gallery.
    The photo will be uploaded directly to Instagram as an unpublished container
    for admin review and approval.

    Rate Limited: 3 submissions per hour per IP address
    Authentication: Optional (but recommended for users)
    """
    try:
        # Log submission attempt with user info if authenticated
        if current_user:
            logger.info(f"Gallery submission from authenticated user: {current_user.id} ({current_user.email})")
        else:
            logger.info(f"Gallery submission from unauthenticated user: {email}")

        # Validate file type
        if not photo.content_type or not photo.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if photo.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Only JPG, PNG, and WEBP images are allowed"
            )

        # Validate file size (8MB)
        photo_content = await photo.read()
        if len(photo_content) > 8 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image size must be less than 8MB")

        # Create caption with submission details
        caption = f"""Hall of Achievers Submission

👤 Name: {fullName}
📧 Email: {email}
📍 City: {city}
🏆 Challenge: {challengeName}

📖 Story:
{story}

#GlycoGrit #HallOfAchievers #CyclingCommunity
"""

        # Initialize Instagram service
        instagram_service = InstagramService()

        # Upload to Instagram as unpublished container
        container_id = await instagram_service.create_media_container(
            image_data=photo_content,
            caption=caption
        )

        logger.info(
            f"Gallery submission created: {fullName} ({email}) - "
            f"Instagram Container ID: {container_id}"
        )

        return {
            "success": True,
            "message": "Your submission has been received! It will appear in the gallery after admin approval.",
            "container_id": container_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing gallery submission: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process your submission. Please try again later."
        )
