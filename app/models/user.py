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
    password_hash = Column(String(255), nullable=False)

    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)

    # Address
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    country = Column(String(100), nullable=True)

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organized_events = relationship("Event", back_populates="organizer")
    registrations = relationship("Registration", back_populates="user")
    payments = relationship("Payment", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
