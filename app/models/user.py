"""
User Model
Represents user accounts in the system
"""
from sqlalchemy import Column, Integer, String, Boolean, Date, TIMESTAMP, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    ORGANIZER = "organizer"
    PARTICIPANT = "participant"
    VOLUNTEER = "volunteer"


class User(Base):
    """
    User Model

    Represents all users in the system including participants, organizers, admins, and volunteers.
    Follows the Single Responsibility Principle - handles only user data management.
    """
    __tablename__ = "users"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)

    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    profile_picture_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)

    # Role
    role = Column(SQLEnum(UserRole), default=UserRole.PARTICIPANT, nullable=False, index=True)

    # Address Information
    country = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True, index=True)
    city = Column(String(100), nullable=True, index=True)
    postal_code = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)

    # Emergency Contact
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)

    # Health Information
    blood_group = Column(String(10), nullable=True)
    medical_conditions = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(TIMESTAMP, nullable=True)

    # Relationships
    organized_events = relationship("Event", back_populates="organizer", foreign_keys="Event.organizer_id")
    registrations = relationship("Registration", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    certificates = relationship("Certificate", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    challenge_participations = relationship("ChallengeParticipation", back_populates="user", cascade="all, delete-orphan")
    leaderboard_entries = relationship("LeaderBoard", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"

    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == UserRole.ADMIN

    @property
    def is_organizer(self) -> bool:
        """Check if user can organize events"""
        return self.role in [UserRole.ADMIN, UserRole.ORGANIZER]

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert user to dictionary

        Args:
            include_sensitive: Include sensitive fields like password_hash

        Returns:
            Dictionary representation of user
        """
        data = {
            "id": self.id,
            "email": self.email,
            "phone": self.phone,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "gender": self.gender,
            "profile_picture_url": self.profile_picture_url,
            "bio": self.bio,
            "role": self.role.value if self.role else None,
            "country": self.country,
            "state": self.state,
            "city": self.city,
            "postal_code": self.postal_code,
            "address": self.address,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "phone_verified": self.phone_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

        if include_sensitive:
            data.update({
                "password_hash": self.password_hash,
                "emergency_contact_name": self.emergency_contact_name,
                "emergency_contact_phone": self.emergency_contact_phone,
                "blood_group": self.blood_group,
                "medical_conditions": self.medical_conditions,
                "allergies": self.allergies,
            })

        return data
