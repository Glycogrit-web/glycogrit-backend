"""
Gallery Photo Model
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class GalleryPhoto(Base):
    """Gallery photo submissions"""
    __tablename__ = "gallery_photos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)

    # Photo details
    photo_url = Column(Text, nullable=False)  # Cloudflare R2 URL
    thumbnail_url = Column(Text)  # Thumbnail version
    caption = Column(Text)
    description = Column(Text)

    # Metadata
    is_approved = Column(Boolean, default=False, index=True)
    is_featured = Column(Boolean, default=False, index=True)
    view_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")
    event = relationship("Event")

    def __repr__(self):
        return f"<GalleryPhoto(id={self.id}, user_id={self.user_id})>"
