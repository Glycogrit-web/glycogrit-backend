"""
Event Models
"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Date, Numeric, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Event(Base):
    """Event model - running/cycling events"""
    __tablename__ = "events"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Basic Info
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    event_type = Column(String(50), nullable=False, index=True)  # running, cycling, marathon, etc
    status = Column(String(50), default='draft', nullable=False, index=True)

    # Dates
    start_date = Column(Date, nullable=True, index=True)  # Event start date
    end_date = Column(Date, nullable=True, index=True)  # Event end date
    event_date = Column(TIMESTAMP, nullable=False, index=True)  # Kept for backward compatibility
    registration_start_date = Column(TIMESTAMP, nullable=False)
    registration_end_date = Column(TIMESTAMP, nullable=False)

    # Location
    location = Column(String(500), nullable=True)  # Full location string
    location_name = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    country = Column(String(100), nullable=False, index=True)

    # Event Details
    total_distance = Column(Numeric(10, 2), nullable=True)
    max_participants = Column(Integer, nullable=True)
    current_participants = Column(Integer, default=0)
    registration_fee = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(10), default='INR')

    # Challenge-specific fields (for frontend compatibility)
    difficulty_level = Column(String(50), nullable=True)  # beginner, intermediate, advanced
    goals = Column(JSONB, nullable=True)  # ["Run 100km", "Complete 30 days"]
    rewards = Column(JSONB, nullable=True)  # ["Medal", "Certificate", "T-shirt"]
    banner_image_url = Column(String(500), nullable=True)  # For challenge/event images
    rules = Column(Text, nullable=True)  # Event rules (stored as text, can be split into array for frontend)

    # Organizer
    organizer_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)

    # Flags
    is_virtual = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organizer = relationship("User", back_populates="organized_events")
    categories = relationship("EventCategory", back_populates="event", cascade="all, delete-orphan")
    registrations = relationship("Registration", back_populates="event")

    def __repr__(self):
        return f"<Event(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class EventCategory(Base):
    """Event Category model - distance categories within events"""
    __tablename__ = "event_categories"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False, index=True)

    # Category Details
    name = Column(String(100), nullable=False)  # 5K, 10K, Half Marathon, etc
    distance = Column(Numeric(10, 2), nullable=True)
    description = Column(String(255), nullable=True)

    # Capacity
    max_participants = Column(Integer, nullable=True)
    current_participants = Column(Integer, default=0)

    # Pricing
    registration_fee = Column(Numeric(10, 2), nullable=True)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    event = relationship("Event", back_populates="categories")
    registrations = relationship("Registration", back_populates="category")

    def __repr__(self):
        return f"<EventCategory(id={self.id}, name='{self.name}', event_id={self.event_id})>"
