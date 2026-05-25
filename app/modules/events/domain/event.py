"""
Event Models
"""
from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.enums import EventStatus


class Event(Base):
    """Event model - fitness events supporting multiple activities"""
    __tablename__ = "events"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Basic Info
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    status = Column(String(50), default=EventStatus.DRAFT, nullable=False, index=True)

    # Dates (TIMESTAMP fields provide both date and time precision)
    event_date = Column(TIMESTAMP, nullable=False, index=True)  # Event start date/time
    event_end_date = Column(TIMESTAMP, nullable=True, index=True)  # Event end date/time (actual event timeline)
    registration_start_date = Column(TIMESTAMP, nullable=False)  # Registration opens
    registration_end_date = Column(TIMESTAMP, nullable=False)  # Registration closes

    # Event Details
    current_participants = Column(Integer, default=0)
    currency = Column(String(10), default='INR')

    # Challenge-specific fields (for frontend compatibility)
    goals = Column(JSONB, nullable=True)  # ["Run 100km", "Complete 30 days"]
    banner_image_url = Column(String(500), nullable=True)  # For challenge/event images
    banner_crop_data = Column(JSONB, nullable=True)  # {"x": 0, "y": 0, "width": 100, "height": 100, "zoom": 1}
    banner_dominant_color = Column(String(50), nullable=True)  # Extracted dominant color from banner
    banner_accent_color = Column(String(50), nullable=True)  # Secondary/accent color from banner
    rules = Column(Text, nullable=True)  # Event rules (stored as text, can be split into array for frontend)
    how_it_works = Column(JSONB, nullable=True)  # "How It Works" section template (title, subtitle, steps with number, title, content, footer)
    event_features = Column(JSONB, nullable=True)  # Event features/symbols to display on cards (activity types, rewards, shipping)

    # Hero Section Customization
    hero_title = Column(String(200), nullable=True)  # Custom hero title (e.g., "This Mother's Day, dedicate every km to her")
    hero_subtitle = Column(String(200), nullable=True)  # Hero subtitle (e.g., "Virtual Run & Ride Challenge")
    hero_tagline = Column(Text, nullable=True)  # Emotional tagline (e.g., "🎁 The most meaningful Mother's Day gift...")
    medal_image_url = Column(String(500), nullable=True)  # Dedicated medal image for hero showcase
    hero_background_pattern = Column(String(50), nullable=True)  # Background pattern type: 'gradient', 'radial', 'mesh', 'geometric'

    # Organizer
    organizer_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)

    # Flags
    is_virtual = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)

    # Multi-Tier Registration System
    uses_tier_system = Column(Boolean, default=True)  # Whether event uses tier-based pricing
    default_tier_id = Column(Integer, ForeignKey('event_registration_tiers.id'), nullable=True, index=True)  # Default/free tier

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organizer = relationship("User", back_populates="organized_events")
    activities = relationship("EventActivity", back_populates="event", cascade="all, delete-orphan")
    registrations = relationship("Registration", back_populates="event", cascade="all, delete-orphan")
    user_rewards = relationship("UserReward", back_populates="event")
    registration_tiers = relationship("EventRegistrationTier", back_populates="event", cascade="all, delete-orphan", foreign_keys="EventRegistrationTier.event_id")
    default_tier = relationship("EventRegistrationTier", foreign_keys=[default_tier_id], post_update=True)

    def __repr__(self):
        return f"<Event(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class EventActivity(Base):
    """Event Activity model - selectable activities within events (e.g., 5K Run, 10K Cycle)"""
    __tablename__ = "event_activities"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False, index=True)

    # Activity Details
    name = Column(String(100), nullable=False)  # "5K Run", "10K Cycle", "Half Marathon", etc
    activity_type = Column(String(50), nullable=True, index=True)  # running, cycling, walking, etc
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
    event = relationship("Event", back_populates="activities")
    registrations = relationship("Registration", back_populates="activity")
    activity_progress = relationship("ActivityProgress", back_populates="activity")

    def __repr__(self):
        return f"<EventActivity(id={self.id}, name='{self.name}', type='{self.activity_type}', event_id={self.event_id})>"
