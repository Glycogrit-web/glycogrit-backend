"""
Payment Model
"""
from sqlalchemy import Column, Integer, String, Numeric, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Payment(Base):
    """Payment model - transaction records"""
    __tablename__ = "payments"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    registration_id = Column(Integer, ForeignKey('registrations.id'), nullable=False, index=True)

    # Payment Details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default='INR')
    payment_method = Column(String(50), nullable=False)  # credit_card, upi, net_banking, etc
    status = Column(String(50), default='pending', nullable=False, index=True)
    # Status: pending, completed, failed, refunded

    # Transaction Info
    transaction_id = Column(String(100), unique=True, nullable=True, index=True)
    gateway_reference = Column(String(100), nullable=True)
    gateway_name = Column(String(50), nullable=True)  # razorpay, stripe, etc

    # Generic Gateway Fields (provider-agnostic)
    gateway_order_id = Column(String(100), nullable=True, index=True)  # Gateway's order ID
    gateway_payment_id = Column(String(100), nullable=True, index=True)  # Gateway's payment ID
    gateway_signature = Column(String(255), nullable=True)  # Payment signature for verification

    # Razorpay-specific fields (kept for backward compatibility and Razorpay-specific features)
    razorpay_order_id = Column(String(100), nullable=True, index=True)
    razorpay_payment_id = Column(String(100), nullable=True, index=True)
    razorpay_signature = Column(String(255), nullable=True)

    # Refund tracking (generic for all gateways)
    refund_id = Column(String(100), nullable=True)  # Gateway's refund ID
    refund_amount = Column(Numeric(10, 2), nullable=True)
    refund_status = Column(String(50), nullable=True)  # pending, processed, failed
    refunded_at = Column(TIMESTAMP, nullable=True)

    # Timestamps
    initiated_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    completed_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="payments")
    registration = relationship("Registration", back_populates="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount}, status='{self.status}')>"
