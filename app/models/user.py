from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String(128), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255))
    phone = Column(String(20))
    avatar_url = Column(Text)

    # Profile information
    bio = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))

    # Cycling preferences
    cycling_level = Column(String(50))  # beginner, intermediate, advanced, professional
    preferred_distance = Column(String(50))  # short (0-20km), medium (20-50km), long (50-100km), ultra (100km+)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<User {self.email}>"
