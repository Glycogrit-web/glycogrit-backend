from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Enum
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class EventType(str, enum.Enum):
    RACE = "race"
    GROUP_RIDE = "group_ride"
    WORKSHOP = "workshop"
    SOCIAL = "social"
    CHARITY = "charity"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    # Basic information
    title = Column(String(255), nullable=False)
    description = Column(Text)
    event_type = Column(Enum(EventType), default=EventType.GROUP_RIDE)
    image_url = Column(Text)

    # Location
    location = Column(String(500), nullable=False)
    venue_name = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))

    # Schedule
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True))
    registration_deadline = Column(DateTime(timezone=True))

    # Event details
    distance = Column(Float)  # for races/rides
    entry_fee = Column(Float, default=0)
    max_participants = Column(Integer)
    current_participants = Column(Integer, default=0)

    # Registration
    registration_url = Column(Text)
    is_registration_open = Column(Boolean, default=True)

    # Organizer
    organizer_name = Column(String(255))
    organizer_contact = Column(String(255))
    organizer_email = Column(String(255))

    # Status
    is_featured = Column(Boolean, default=False)
    is_published = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Event {self.title}>"
