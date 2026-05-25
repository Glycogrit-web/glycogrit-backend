"""
Webhook Event Domain Model
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.sql import func

from app.core.database import Base


class WebhookSource(str, Enum):
    """Webhook source provider"""
    RAZORPAY = "razorpay"
    SHIPROCKET = "shiprocket"
    STRAVA = "strava"
    GARMIN = "garmin"
    FITBIT = "fitbit"
    GOOGLE_FIT = "google_fit"


class WebhookStatus(str, Enum):
    """Webhook processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class WebhookEvent(Base):
    """Webhook event log"""
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)

    # Webhook metadata
    source = Column(SQLEnum(WebhookSource), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)  # payment.captured, order.shipped, etc.
    event_id = Column(String(255), unique=True, nullable=False, index=True)  # External event ID

    # Payload
    payload = Column(Text, nullable=False)  # JSON string
    headers = Column(Text, nullable=True)  # JSON string of headers

    # Processing status
    status = Column(SQLEnum(WebhookStatus), default=WebhookStatus.PENDING, nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    # Signature verification
    signature = Column(String(500), nullable=True)
    signature_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, source={self.source}, event_type={self.event_type})>"

    def can_retry(self, max_retries: int = 3) -> bool:
        """Check if webhook can be retried"""
        return self.status == WebhookStatus.FAILED and self.retry_count < max_retries

    def mark_processing(self):
        """Mark webhook as processing"""
        self.status = WebhookStatus.PROCESSING

    def mark_processed(self):
        """Mark webhook as processed"""
        self.status = WebhookStatus.PROCESSED
        self.processed_at = datetime.utcnow()

    def mark_failed(self, error_message: str):
        """Mark webhook as failed"""
        self.status = WebhookStatus.FAILED
        self.error_message = error_message
        self.retry_count += 1
