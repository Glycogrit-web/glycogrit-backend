"""
User Model
"""
from sqlalchemy import Column, Integer, String, Boolean, Date, TIMESTAMP, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """User model - accounts with authentication"""
    __tablename__ = "users"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Authentication - At least one of email or phone must be provided
    email = Column(String(255), unique=True, nullable=True, index=True)  # Made nullable for phone-only registration
    phone = Column(String(20), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users

    # OAuth fields
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'facebook', etc.
    oauth_id = Column(String(255), nullable=True, index=True)  # Provider's user ID
    profile_picture_url = Column(String(500), nullable=True)  # Profile image from OAuth

    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    age = Column(Integer, nullable=True)  # For quick access during registration
    t_shirt_size = Column(String(10), nullable=True)  # Saved from registration

    # Address
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    postal_code = Column(String(10), nullable=True, index=True)  # PIN code for address auto-fill
    country = Column(String(100), nullable=True)

    # Role
    role = Column(String(50), nullable=False, server_default='user', index=True)  # user, admin, super_admin

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)  # True for OAuth users

    # Fitness Sync Preferences
    primary_sync_source = Column(String(50), nullable=True)  # 'strava', 'google_fit', etc. - Only this source auto-syncs

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organized_events = relationship("Event", back_populates="organizer")
    registrations = relationship("Registration", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    payment_links = relationship("PaymentLink", back_populates="user")
    strava_connection = relationship("StravaConnection", back_populates="user", uselist=False)
    garmin_connection = relationship("GarminConnection", back_populates="user", uselist=False)
    fitness_trackers = relationship("FitnessTrackerConnection", back_populates="user")
    rewards = relationship("UserReward", back_populates="user", foreign_keys="[UserReward.user_id]")
    activity_progress = relationship("ActivityProgress", back_populates="user")

    def __repr__(self):
        identifier = self.email or self.phone or f"id:{self.id}"
        return f"<User(id={self.id}, identifier='{identifier}')>"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin or super_admin role"""
        return self.role in ('admin', 'super_admin')

    def has_email(self) -> bool:
        """Check if user has email configured"""
        return self.email is not None and self.email != ''

    def has_phone(self) -> bool:
        """Check if user has phone configured"""
        return self.phone is not None and self.phone != ''

    def can_disconnect_email(self) -> bool:
        """Check if email can be safely disconnected (has phone as alternative)"""
        return self.has_email() and self.has_phone()

    def can_disconnect_phone(self) -> bool:
        """Check if phone can be safely disconnected (has email as alternative)"""
        return self.has_phone() and self.has_email()

    @property
    def has_password(self) -> bool:
        """Check if user has password set (False for OAuth-only users)"""
        return self.password_hash is not None and self.password_hash != ''
