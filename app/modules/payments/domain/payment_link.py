"""
Payment Link Domain Model
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class PaymentLink(Base):
    """
    Payment Link model for shareable payment URLs.

    Razorpay payment links allow customers to pay without logging in.
    Useful for:
    - Corporate bulk registrations
    - Email/WhatsApp payment requests
    - Guest checkout
    - Offline marketing campaigns
    """
    __tablename__ = "payment_links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    registration_id = Column(Integer, ForeignKey("registrations.id", ondelete="SET NULL"), nullable=True)

    # Razorpay payment link details
    razorpay_link_id = Column(String(255), unique=True, nullable=False)
    short_url = Column(Text, nullable=False)

    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    description = Column(Text, nullable=True)
    reference_id = Column(String(255), nullable=True, index=True)

    # Customer details
    customer_name = Column(String(255), nullable=True)
    customer_email = Column(String(255), nullable=True)
    customer_contact = Column(String(20), nullable=True)

    # Link configuration
    callback_url = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    # Status values: active, paid, expired, cancelled

    # Timestamps
    expires_at = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="payment_links")
    registration = relationship("Registration", back_populates="payment_links")

    def __repr__(self):
        return f"<PaymentLink(id={self.id}, razorpay_link_id={self.razorpay_link_id}, amount={self.amount}, status={self.status})>"

    def is_expired(self) -> bool:
        """Check if payment link has expired"""
        return datetime.utcnow() > self.expires_at

    def is_active(self) -> bool:
        """Check if payment link is active and can accept payments"""
        return self.status == "active" and not self.is_expired()
