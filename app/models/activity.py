"""
Activity Model - For tracking user activities in events/challenges
"""
from sqlalchemy import Column, Integer, Numeric, Date, Text, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class EventActivity(Base):
    """EventActivity model - tracks user activity submissions for virtual challenges"""
    __tablename__ = "event_activities"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False, index=True)
    registration_id = Column(Integer, ForeignKey('registrations.id'), nullable=True, index=True)

    # Activity Details
    distance = Column(Numeric(10, 2), nullable=True)  # Distance in km
    duration = Column(Integer, nullable=True)  # Duration in minutes
    activity_date = Column(Date, nullable=False, index=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    event = relationship("Event")
    registration = relationship("Registration")

    def __repr__(self):
        return f"<EventActivity(id={self.id}, user_id={self.user_id}, event_id={self.event_id}, date={self.activity_date})>"
