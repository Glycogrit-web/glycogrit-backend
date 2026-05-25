"""
Gallery Service
"""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, PermissionDeniedException
from app.modules.gallery.domain.photo import GalleryPhoto
from app.services.base import BaseService


class GalleryService(BaseService):
    """Service for gallery operations"""

    def __init__(self, db: Session):
        super().__init__(db)

    def submit_photo(
        self, user_id: int, photo_url: str, caption: str = None, event_id: int = None
    ) -> GalleryPhoto:
        """Submit photo to gallery"""
        photo = GalleryPhoto(
            user_id=user_id,
            photo_url=photo_url,
            caption=caption,
            event_id=event_id,
            is_approved=False,  # Requires admin approval
        )
        self.db.add(photo)
        self.db.commit()
        self.db.refresh(photo)
        return photo

    def approve_photo(self, photo_id: int) -> GalleryPhoto:
        """Approve photo (admin only)"""
        photo = self.db.query(GalleryPhoto).filter(GalleryPhoto.id == photo_id).first()
        if not photo:
            raise NotFoundException("Photo", str(photo_id))

        photo.is_approved = True
        self.db.commit()
        self.db.refresh(photo)
        return photo

    def get_approved_photos(
        self, event_id: int = None, featured_only: bool = False, limit: int = 50
    ) -> list[GalleryPhoto]:
        """Get approved photos for gallery display"""
        query = self.db.query(GalleryPhoto).filter(GalleryPhoto.is_approved)

        if event_id:
            query = query.filter(GalleryPhoto.event_id == event_id)

        if featured_only:
            query = query.filter(GalleryPhoto.is_featured)

        return query.order_by(GalleryPhoto.created_at.desc()).limit(limit).all()

    def delete_photo(self, photo_id: int, user_id: int) -> None:
        """Delete photo (owner or admin only)"""
        photo = self.db.query(GalleryPhoto).filter(GalleryPhoto.id == photo_id).first()
        if not photo:
            raise NotFoundException("Photo", str(photo_id))

        if photo.user_id != user_id:
            raise PermissionDeniedException("You can only delete your own photos")

        self.db.delete(photo)
        self.db.commit()
