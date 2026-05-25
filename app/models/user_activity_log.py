"""
User Activity Log Model - For tracking user daily activities in events/challenges
"""
from sqlalchemy import TIMESTAMP, Column, Date, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserActivityLog(Base):
    """UserActivityLog model - tracks user daily activity submissions for virtual challenges"""
    __tablename__ = "user_activity_logs"

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
        return f"<UserActivityLog(id={self.id}, user_id={self.user_id}, event_id={self.event_id}, date={self.activity_date})>"
