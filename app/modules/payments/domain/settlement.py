"""
Settlement Domain Models
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.database import Base


class Settlement(Base):
    """
    Settlement model for tracking when funds reach bank account.

    Settlements represent actual money transferred from Razorpay to your bank.
    Important for:
    - Cash flow tracking
    - Financial reconciliation
    - Accounting
    """
    __tablename__ = "settlements"

    id = Column(Integer, primary_key=True, index=True)

    # Razorpay settlement details
    razorpay_settlement_id = Column(String(255), unique=True, nullable=False)

    # Financial details
    amount = Column(Numeric(10, 2), nullable=False)  # Net amount settled
    fees = Column(Numeric(10, 2), nullable=True)  # Razorpay fees
    tax = Column(Numeric(10, 2), nullable=True)  # Tax on fees

    # Bank details
    utr = Column(String(255), nullable=True, index=True)  # Unique Transaction Reference

    # Status
    status = Column(String(50), nullable=False, index=True)
    # Status values: processed, failed, reversed

    # Timestamps
    settled_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    payment_settlements = relationship("PaymentSettlement", back_populates="settlement", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Settlement(id={self.id}, razorpay_settlement_id={self.razorpay_settlement_id}, amount={self.amount}, status={self.status})>"


class PaymentSettlement(Base):
    """
    Junction table linking payments to settlements.

    A settlement can contain multiple payments.
    A payment can be split across multiple settlements (rare).
    """
    __tablename__ = "payment_settlements"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True)
    settlement_id = Column(Integer, ForeignKey("settlements.id", ondelete="CASCADE"), nullable=False, index=True)

    # Amount from this payment in this settlement
    amount = Column(Numeric(10, 2), nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    payment = relationship("Payment", back_populates="payment_settlements")
    settlement = relationship("Settlement", back_populates="payment_settlements")

    def __repr__(self):
        return f"<PaymentSettlement(payment_id={self.payment_id}, settlement_id={self.settlement_id}, amount={self.amount})>"
