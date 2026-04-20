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

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
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

    # Address
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    country = Column(String(100), nullable=True)

    # Role
    role = Column(String(50), nullable=False, server_default='user', index=True)  # user, admin, super_admin

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)  # True for OAuth users

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organized_events = relationship("Event", back_populates="organizer")
    registrations = relationship("Registration", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    strava_connection = relationship("StravaConnection", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin or super_admin role"""
        return self.role in ('admin', 'super_admin')
