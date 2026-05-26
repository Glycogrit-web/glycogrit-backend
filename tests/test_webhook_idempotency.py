"""
Unit Tests for Webhook Idempotency and Event Tracking

Tests P1, P4: Webhook duplicate processing and event ID tracking
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.modules.payments.services.payment_service import validate_payment_amount
from app.modules.webhooks.domain.webhook_event import WebhookEvent, WebhookSource, WebhookStatus
from app.modules.webhooks.services.webhook_service import WebhookService


class TestWebhookEventTracking:
    """Test webhook event tracking for idempotency"""

    def test_create_new_webhook_event(self, db_session: Session):
        """Test creating a new webhook event"""
        service = WebhookService(db_session)

        webhook_event = service.receive_webhook(
            source=WebhookSource.RAZORPAY,
            event_type="payment.captured",
            event_id="evt_test_123",
            payload={"test": "data"},
            signature="test_sig",
        )

        assert webhook_event is not None
        assert webhook_event.event_id == "evt_test_123"
        assert webhook_event.source == WebhookSource.RAZORPAY
        assert webhook_event.status == WebhookStatus.PENDING
        assert webhook_event.retry_count == 0

    def test_get_existing_webhook_event(self, db_session: Session):
        """Test retrieving existing webhook event (duplicate)"""
        service = WebhookService(db_session)

        # Create first time
        webhook_event1 = service.receive_webhook(
            source=WebhookSource.RAZORPAY,
            event_type="payment.captured",
            event_id="evt_test_456",
            payload={"test": "data"},
            signature="test_sig",
        )

        webhook_id1 = webhook_event1.id

        # Try to create again (duplicate)
        webhook_event2 = service.receive_webhook(
            source=WebhookSource.RAZORPAY,
            event_type="payment.captured",
            event_id="evt_test_456",
            payload={"test": "data"},
            signature="test_sig",
        )

        # Should return the same webhook event
        assert webhook_event2.id == webhook_id1
        assert webhook_event2.retry_count == webhook_event1.retry_count

    def test_webhook_replay_attack_prevention(self, db_session: Session):
        """Test that replayed webhooks are detected"""
        service = WebhookService(db_session)
        event_id = "evt_replay_test"

        # First webhook
        webhook1 = service.receive_webhook(
            source=WebhookSource.RAZORPAY,
            event_type="payment.captured",
            event_id=event_id,
            payload={"amount": 50000},
            signature="valid_sig",
        )

        # Mark as processed
        webhook1.mark_processed()
        db_session.commit()

        # Attacker replays same webhook
        webhook2 = service.receive_webhook(
            source=WebhookSource.RAZORPAY,
            event_type="payment.captured",
            event_id=event_id,
            payload={"amount": 50000},
            signature="valid_sig",
        )

        # Should return the same webhook
        assert webhook2.id == webhook1.id
        assert webhook2.status == WebhookStatus.PROCESSED
        # Should not process again

    def test_webhook_mark_processed(self, db_session: Session):
        """Test marking webhook as processed"""
        webhook_event = WebhookEvent(
            event_id="evt_test_789",
            source=WebhookSource.RAZORPAY,
            event_type="payment.captured",
            payload='{"test": "data"}',
            status=WebhookStatus.PENDING,
        )
        db_session.add(webhook_event)
        db_session.commit()

        # Mark as processed
        webhook_event.mark_processed()
        db_session.commit()

        assert webhook_event.status == WebhookStatus.PROCESSED
        assert webhook_event.processed_at is not None

    def test_webhook_record_error(self, db_session: Session):
        """Test recording webhook processing error"""
        webhook_event = WebhookEvent(
            event_id="evt_error_test",
            source=WebhookSource.RAZORPAY,
            event_type="payment.captured",
            payload='{"test": "data"}',
            retry_count=0,
            status=WebhookStatus.PENDING,
        )
        db_session.add(webhook_event)
        db_session.commit()

        # Record error
        error_msg = "Database connection lost"
        webhook_event.mark_failed(error_msg)
        db_session.commit()

        assert webhook_event.retry_count == 1
        assert webhook_event.error_message == error_msg
        assert webhook_event.status == WebhookStatus.FAILED

    def test_multiple_processing_attempts(self, db_session: Session):
        """Test webhook with multiple failed processing attempts"""
        webhook_event = WebhookEvent(
            event_id="evt_retry_test",
            source=WebhookSource.RAZORPAY,
            event_type="payment.captured",
            payload='{"test": "data"}',
            status=WebhookStatus.PENDING,
        )
        db_session.add(webhook_event)
        db_session.commit()

        # Simulate 3 failed attempts
        for i in range(3):
            webhook_event.mark_failed(f"Attempt {i+1} failed")
            db_session.commit()

        assert webhook_event.retry_count == 3
        assert "Attempt 3 failed" in webhook_event.error_message
        assert webhook_event.status == WebhookStatus.FAILED


class TestPaymentAmountValidation:
    """Test payment amount validation (P5)"""

    def test_exact_amount_match(self):
        """Test payment with exact amount match"""
        db_amount = Decimal("500.00")
        webhook_amount = Decimal("500.00")

        assert validate_payment_amount(db_amount, webhook_amount) is True

    def test_amount_within_tolerance(self):
        """Test payment with amount within 1 paisa tolerance"""
        db_amount = Decimal("500.00")
        webhook_amount = Decimal("500.01")  # 1 paisa difference

        assert validate_payment_amount(db_amount, webhook_amount) is True

    def test_amount_exceeds_tolerance(self):
        """Test payment with amount difference > tolerance"""
        db_amount = Decimal("500.00")
        webhook_amount = Decimal("501.00")  # ₹1 difference

        assert validate_payment_amount(db_amount, webhook_amount) is False

    def test_amount_fraud_detection(self):
        """Test detection of fraudulent amount manipulation"""
        # User should pay ₹1000
        db_amount = Decimal("1000.00")

        # Attacker sends webhook with ₹1
        webhook_amount = Decimal("1.00")

        assert validate_payment_amount(db_amount, webhook_amount) is False

    def test_custom_tolerance(self):
        """Test amount validation with custom tolerance"""
        db_amount = Decimal("1000.00")
        webhook_amount = Decimal("1000.50")

        # Default tolerance (1 paisa) - should fail
        assert validate_payment_amount(db_amount, webhook_amount) is False

        # Custom tolerance (₹1) - should pass
        assert validate_payment_amount(db_amount, webhook_amount, tolerance=Decimal("1.00")) is True

    def test_zero_amount_payment(self):
        """Test validation for free tier (₹0)"""
        db_amount = Decimal("0.00")
        webhook_amount = Decimal("0.00")

        assert validate_payment_amount(db_amount, webhook_amount) is True

    def test_negative_amount_detection(self):
        """Test that negative amounts are caught"""
        db_amount = Decimal("500.00")
        webhook_amount = Decimal("-500.00")

        assert validate_payment_amount(db_amount, webhook_amount) is False


@pytest.mark.skip(
    reason="Concurrent test requires PostgreSQL with proper transaction isolation. SQLite in-memory doesn't support concurrent access from multiple threads."
)
class TestConcurrentWebhookProcessing:
    """Test concurrent webhook processing scenarios"""

    def test_concurrent_webhook_same_event(self, db_session: Session):
        """Test that concurrent webhooks with same event ID don't duplicate"""
        from concurrent.futures import ThreadPoolExecutor

        event_id = "evt_concurrent_test"
        results = []

        def process_webhook():
            # Simulate webhook processing
            service = WebhookService(db_session)
            webhook = service.receive_webhook(
                source=WebhookSource.RAZORPAY,
                event_type="payment.captured",
                event_id=event_id,
                payload={"test": "data"},
                signature="sig",
            )
            # Check if this is a new event or existing
            results.append(webhook.id)
            return webhook.id

        # Simulate 10 concurrent webhook requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_webhook) for _ in range(10)]
            webhook_ids = [f.result() for f in futures]

        # All should return the same webhook ID (no duplicates)
        assert len(set(webhook_ids)) == 1


# Pytest fixtures
@pytest.fixture
def db_session():
    """Create test database session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.database import Base

    # Import models to ensure tables are registered
    from app.modules.webhooks.domain.webhook_event import WebhookEvent

    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()

    yield session

    session.rollback()
    session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
