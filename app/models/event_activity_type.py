"""
Event Activity Type Model - Many-to-many relationship for event activities
"""
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class EventActivityType(Base):
    """
    EventActivityType model - Represents the many-to-many relationship between events and activity types.

    This allows a single event to support multiple activity types (e.g., a triathlon with running, cycling, swimming).
    """
    __tablename__ = "event_activity_types"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False, index=True)

    # Activity Details
    activity_type = Column(String(50), nullable=False, index=True)  # running, cycling, swimming, walking, hiking, etc.
    is_primary = Column(Boolean, default=False, nullable=False)  # Mark one activity as primary for display purposes

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    event = relationship("Event", back_populates="activity_types")

    def __repr__(self):
        return f"<EventActivityType(id={self.id}, event_id={self.event_id}, activity_type='{self.activity_type}', is_primary={self.is_primary})>"
