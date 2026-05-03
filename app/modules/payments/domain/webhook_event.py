"""
Webhook Event Domain Model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.db.database import Base


class WebhookEvent(Base):
    """
    Webhook Event model for reliable webhook processing.

    Stores all incoming webhook events for:
    - Idempotency (prevent duplicate processing)
    - Retry mechanism (handle failures)
    - Audit trail (track all events)
    - Debugging (inspect failed events)
    """
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)

    # Event identification
    event_id = Column(String(255), unique=True, nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    # Event types: payment.authorized, payment.captured, payment.failed,
    #              refund.created, refund.processed, settlement.processed, etc.

    # Event data
    payload = Column(JSONB, nullable=False)  # Full webhook payload
    signature = Column(Text, nullable=False)  # Webhook signature for verification

    # Processing status
    status = Column(String(50), nullable=False, default="pending", index=True)
    # Status values: pending, processing, processed, failed

    # Retry handling
    retry_count = Column(Integer, nullable=False, default=0)
    last_retry_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, event_id={self.event_id}, event_type={self.event_type}, status={self.status})>"

    def can_retry(self, max_retries: int = 5) -> bool:
        """Check if webhook can be retried"""
        return self.status == "failed" and self.retry_count < max_retries

    def increment_retry(self):
        """Increment retry counter"""
        self.retry_count += 1
        self.last_retry_at = datetime.utcnow()
