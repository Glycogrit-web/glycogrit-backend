"""
Registration Model
"""
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Registration(Base):
    """Registration model - event sign-ups"""
    __tablename__ = "registrations"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False, index=True)
    event_category_id = Column(Integer, ForeignKey('event_categories.id'), nullable=True, index=True)

    # Registration Details
    registration_number = Column(String(50), unique=True, nullable=False, index=True)
    bib_number = Column(String(50), unique=True, nullable=True, index=True)
    status = Column(String(50), default='pending', nullable=False, index=True)
    # Status: pending, confirmed, payment_completed, cancelled

    # Participant Details
    participant_name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    t_shirt_size = Column(String(10), nullable=True)

    # Multi-Tier Registration System
    uses_tier_system = Column(Boolean, default=False, nullable=False)  # Flag for tier-based registration
    current_tier_id = Column(Integer, ForeignKey('event_registration_tiers.id'), nullable=True, index=True)  # Highest tier user has

    # Timestamps
    registered_at = Column(TIMESTAMP, server_default=func.now(), nullable=False, index=True)
    confirmed_at = Column(TIMESTAMP, nullable=True)

    # Relationships
    user = relationship("User", back_populates="registrations")
    event = relationship("Event", back_populates="registrations")
    category = relationship("EventCategory", back_populates="registrations")
    payments = relationship("Payment", back_populates="registration")
    tiers = relationship("RegistrationTier", back_populates="registration", cascade="all, delete-orphan")
    current_tier = relationship("EventRegistrationTier", foreign_keys=[current_tier_id])
    activity_progress = relationship("ActivityProgress", back_populates="registration", uselist=False)

    def __repr__(self):
        return f"<Registration(id={self.id}, reg_num='{self.registration_number}', status='{self.status}')>"
