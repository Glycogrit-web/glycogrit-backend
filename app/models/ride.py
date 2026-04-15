from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class RideStatus(str, enum.Enum):
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RideDifficulty(str, enum.Enum):
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    EXTREME = "extreme"


class Ride(Base):
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True, index=True)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Basic information
    title = Column(String(255), nullable=False)
    description = Column(Text)
    image_url = Column(Text)

    # Location
    start_location = Column(String(500), nullable=False)
    end_location = Column(String(500))
    route_map_url = Column(Text)

    # Ride details
    distance = Column(Float)  # in kilometers
    difficulty = Column(Enum(RideDifficulty), default=RideDifficulty.MODERATE)
    estimated_duration = Column(Integer)  # in minutes
    elevation_gain = Column(Float)  # in meters

    # Schedule
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))

    # Participation
    max_participants = Column(Integer)
    current_participants = Column(Integer, default=0)

    # Status
    status = Column(Enum(RideStatus), default=RideStatus.UPCOMING)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organizer = relationship("User", backref="organized_rides")

    def __repr__(self):
        return f"<Ride {self.title}>"
