"""
Registration Model
"""
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.enums import RegistrationStatus, PaymentStatus, TShirtSize, Gender


class Registration(Base):
    """Registration model - event sign-ups"""
    __tablename__ = "registrations"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False, index=True)
    event_activity_id = Column(Integer, ForeignKey('event_activities.id'), nullable=True, index=True)

    # Registration Details
    registration_number = Column(String(50), unique=True, nullable=False, index=True)
    bib_number = Column(String(50), unique=True, nullable=True, index=True)
    status = Column(String(50), default=RegistrationStatus.PENDING.value, nullable=False, index=True)
    # Status: Use RegistrationStatus enum (PENDING, CONFIRMED, PAYMENT_COMPLETED, CANCELLED)

    # Participant Details
    participant_name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    t_shirt_size = Column(String(10), nullable=True)

    # Shipping Address (for reward delivery)
    shipping_address_line1 = Column(String(255), nullable=True)
    shipping_address_line2 = Column(String(255), nullable=True)
    shipping_city = Column(String(100), nullable=True)
    shipping_state = Column(String(100), nullable=True)
    shipping_postal_code = Column(String(20), nullable=True)
    shipping_country = Column(String(100), nullable=True, default='India')
    shipping_phone = Column(String(20), nullable=True)
    shipping_email = Column(String(255), nullable=True)

    # Multi-Tier Registration System
    uses_tier_system = Column(Boolean, default=False, nullable=False)  # Flag for tier-based registration
    current_tier_id = Column(Integer, ForeignKey('event_registration_tiers.id'), nullable=True, index=True)  # Highest tier user has

    # Payment Tracking
    total_amount_paid = Column(Numeric(10, 2), nullable=False, default=0.00)  # Sum of all successful payments
    successful_payments_count = Column(Integer, nullable=False, default=0)  # Number of successful payment transactions
    last_payment_status = Column(String(20), nullable=True, index=True)  # 'pending', 'success', 'failed', 'refunded'
    last_payment_amount = Column(Numeric(10, 2), nullable=True)  # Amount of most recent payment attempt
    last_payment_date = Column(TIMESTAMP, nullable=True)  # Timestamp of most recent payment attempt

    # Timestamps
    registered_at = Column(TIMESTAMP, server_default=func.now(), nullable=False, index=True)
    confirmed_at = Column(TIMESTAMP, nullable=True)

    # Relationships
    user = relationship("User", back_populates="registrations")
    event = relationship("Event", back_populates="registrations")
    activity = relationship("EventActivity", back_populates="registrations")
    payments = relationship("Payment", back_populates="registration")
    payment_links = relationship("PaymentLink", back_populates="registration")
    tiers = relationship("RegistrationTier", back_populates="registration", cascade="all, delete-orphan")
    current_tier = relationship("EventRegistrationTier", foreign_keys=[current_tier_id])
    activity_progress = relationship("ActivityProgress", back_populates="registration", uselist=False)
    rewards = relationship("UserReward", back_populates="registration")

    def __repr__(self):
        return f"<Registration(id={self.id}, reg_num='{self.registration_number}', status='{self.status}')>"

    def record_successful_payment(self, amount: float):
        """Record a successful payment transaction"""
        from datetime import datetime
        self.total_amount_paid = (self.total_amount_paid or 0) + amount
        self.successful_payments_count = (self.successful_payments_count or 0) + 1
        self.last_payment_status = PaymentStatus.COMPLETED.value
        self.last_payment_amount = amount
        self.last_payment_date = datetime.utcnow()

    def record_failed_payment(self, amount: float):
        """Record a failed payment attempt"""
        from datetime import datetime
        self.last_payment_status = PaymentStatus.FAILED.value
        self.last_payment_amount = amount
        self.last_payment_date = datetime.utcnow()

    def record_pending_payment(self, amount: float):
        """Record a pending payment"""
        from datetime import datetime
        self.last_payment_status = PaymentStatus.PENDING.value
        self.last_payment_amount = amount
        self.last_payment_date = datetime.utcnow()

    def record_refund(self, amount: float):
        """Record a refund"""
        from datetime import datetime
        self.total_amount_paid = max(0, (self.total_amount_paid or 0) - amount)
        self.last_payment_status = 'refunded'
        self.last_payment_amount = amount
        self.last_payment_date = datetime.utcnow()

    @property
    def balance_owed(self) -> float:
        """Calculate balance owed based on current tier price"""
        if not self.current_tier:
            return 0.0
        tier_price = float(self.current_tier.price or 0)
        total_paid = float(self.total_amount_paid or 0)
        return max(0, tier_price - total_paid)

    @property
    def has_outstanding_balance(self) -> bool:
        """Check if there's an outstanding balance"""
        return self.balance_owed > 0
