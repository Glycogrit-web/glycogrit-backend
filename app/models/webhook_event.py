"""
Webhook Event Model - Track processed webhook events to prevent duplicates
"""
from sqlalchemy import Column, Integer, String, TIMESTAMP, Text, Boolean, Index
from sqlalchemy.sql import func
from app.core.database import Base


class WebhookEvent(Base):
    """
    Track processed webhook events for idempotency.

    Prevents duplicate webhook processing by storing event IDs
    from payment gateway webhooks.
    """
    __tablename__ = "webhook_events"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Webhook Event Identity
    gateway_event_id = Column(String(255), unique=True, nullable=False, index=True)
    gateway_name = Column(String(50), nullable=False, index=True)  # razorpay, stripe, etc.
    event_type = Column(String(100), nullable=False, index=True)  # payment.captured, payment.failed, etc.

    # Processing Status
    processed = Column(Boolean, nullable=False, default=False, index=True)
    processed_at = Column(TIMESTAMP, nullable=True)

    # Related Entity IDs (for quick lookup)
    payment_id = Column(Integer, nullable=True, index=True)  # Our internal payment ID
    registration_id = Column(Integer, nullable=True, index=True)
    gateway_payment_id = Column(String(100), nullable=True, index=True)  # Gateway's payment ID

    # Webhook Data
    payload = Column(Text, nullable=True)  # Store full webhook payload for debugging
    signature = Column(String(255), nullable=True)

    # Error Tracking
    processing_attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)

    # Timestamps
    received_at = Column(TIMESTAMP, server_default=func.now(), nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Composite indexes for efficient querying
    __table_args__ = (
        Index('idx_webhook_gateway_event', 'gateway_name', 'gateway_event_id'),
        Index('idx_webhook_processing', 'processed', 'received_at'),
        Index('idx_webhook_payment_lookup', 'gateway_payment_id', 'gateway_name'),
    )

    def __repr__(self):
        return (
            f"<WebhookEvent(id={self.id}, gateway={self.gateway_name}, "
            f"event_id='{self.gateway_event_id}', type='{self.event_type}', "
            f"processed={self.processed})>"
        )

    def mark_processed(self, payment_id: int = None, registration_id: int = None):
        """Mark webhook event as successfully processed"""
        self.processed = True
        self.processed_at = func.now()
        if payment_id:
            self.payment_id = payment_id
        if registration_id:
            self.registration_id = registration_id

    def record_error(self, error_message: str):
        """Record processing error"""
        self.processing_attempts += 1
        self.last_error = error_message
        self.updated_at = func.now()
