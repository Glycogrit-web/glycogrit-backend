"""
Registration Tier Junction Model
"""
from sqlalchemy import Column, Integer, TIMESTAMP, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class RegistrationTier(Base):
    """Registration Tier junction model - tracks which tiers a user has registered for"""
    __tablename__ = "registration_tiers"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    registration_id = Column(Integer, ForeignKey('registrations.id', ondelete='CASCADE'), nullable=False, index=True)
    tier_id = Column(Integer, ForeignKey('event_registration_tiers.id'), nullable=False, index=True)

    # Registration Info
    registered_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Upgrade Tracking
    is_upgrade = Column(Boolean, nullable=False, default=False)  # Was this an upgrade from a lower tier?
    upgraded_from_tier_id = Column(Integer, ForeignKey('event_registration_tiers.id'), nullable=True)  # Previous tier if upgraded
    upgrade_payment_id = Column(Integer, ForeignKey('payments.id'), nullable=True)  # Payment record for the upgrade

    # Relationships
    registration = relationship("Registration", back_populates="tiers")
    tier = relationship("EventRegistrationTier", foreign_keys=[tier_id], back_populates="registration_tiers")
    upgraded_from = relationship("EventRegistrationTier", foreign_keys=[upgraded_from_tier_id])
    upgrade_payment = relationship("Payment", foreign_keys=[upgrade_payment_id])

    def __repr__(self):
        return f"<RegistrationTier(id={self.id}, registration_id={self.registration_id}, tier_id={self.tier_id}, is_upgrade={self.is_upgrade})>"

    @property
    def is_initial_registration(self):
        """Check if this is the initial registration (not an upgrade)"""
        return not self.is_upgrade

    def get_tier_name(self):
        """Get the tier name"""
        return self.tier.tier_name if self.tier else None

    def get_tier_price(self):
        """Get the tier price"""
        return self.tier.price if self.tier else None
