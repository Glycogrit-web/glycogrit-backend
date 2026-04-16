"""
Database Models Package
All SQLAlchemy ORM models for the application
"""
from app.models.user import User
from app.models.event import Event, EventCategory, EventCheckpoint, EventSponsor, EventPhoto
from app.models.registration import Registration
from app.models.payment import Payment
from app.models.result import EventResult, LeaderBoard, CheckpointTiming
from app.models.certificate import Certificate
from app.models.challenge import VirtualChallenge, ChallengeParticipation
from app.models.achievement import UserAchievement

__all__ = [
    "User",
    "Event",
    "EventCategory",
    "EventCheckpoint",
    "EventSponsor",
    "EventPhoto",
    "Registration",
    "Payment",
    "EventResult",
    "LeaderBoard",
    "CheckpointTiming",
    "Certificate",
    "VirtualChallenge",
    "ChallengeParticipation",
    "UserAchievement",
]
