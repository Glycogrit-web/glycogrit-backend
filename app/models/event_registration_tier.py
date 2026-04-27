"""
Event Registration Tier Model
"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Numeric, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class EventRegistrationTier(Base):
    """Event Registration Tier model - multiple pricing tiers for events"""
    __tablename__ = "event_registration_tiers"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False, index=True)

    # Tier Identity
    tier_name = Column(String(100), nullable=False)  # Free, Basic, Premium
    tier_slug = Column(String(100), nullable=False, index=True)  # free, basic, premium
    tier_order = Column(Integer, nullable=False, default=0)  # 0=Free, 1=Basic, 2=Premium (for sorting and upgrade logic)

    # Description
    description = Column(Text, nullable=True)  # Tier description shown to users

    # Pricing
    price = Column(Numeric(10, 2), nullable=False, default=0.00)  # Tier price
    currency = Column(String(10), nullable=False, default='INR')  # Currency code
    requires_payment = Column(Boolean, nullable=False, default=False)  # Payment required flag

    # Status
    is_active = Column(Boolean, nullable=False, default=True)  # Active status (hide inactive tiers)

    # Capacity
    max_registrations = Column(Integer, nullable=True)  # Max registrations for this tier
    current_registrations = Column(Integer, nullable=False, default=0)  # Current registration count

    # Rewards (JSONB array)
    # Example: ["E-Certificate", "Digital Badge", "Premium Medal", "T-Shirt"]
    rewards = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    event = relationship("Event", back_populates="registration_tiers")
    registration_tiers = relationship("RegistrationTier", back_populates="tier", foreign_keys="RegistrationTier.tier_id")

    def __repr__(self):
        return f"<EventRegistrationTier(id={self.id}, tier_name='{self.tier_name}', event_id={self.event_id}, price={self.price})>"

    @property
    def is_free(self):
        """Check if this is a free tier"""
        return self.price == 0 and not self.requires_payment

    @property
    def capacity_remaining(self):
        """Calculate remaining capacity"""
        if self.max_registrations is None:
            return None
        return max(0, self.max_registrations - self.current_registrations)

    @property
    def is_sold_out(self):
        """Check if tier is sold out"""
        if self.max_registrations is None:
            return False
        return self.current_registrations >= self.max_registrations

    def get_formatted_price(self):
        """Get formatted price string"""
        if self.is_free:
            return "Free"
        return f"{self.currency} {float(self.price):.2f}"
