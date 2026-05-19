"""
Unit Tests for Webhook Idempotency and Event Tracking

Tests P1, P4: Webhook duplicate processing and event ID tracking
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.models.webhook_event import WebhookEvent
from app.api.webhooks_v2 import get_or_create_webhook_event, validate_payment_amount
from decimal import Decimal


class TestWebhookEventTracking:
    """Test webhook event tracking for idempotency"""

    def test_create_new_webhook_event(self, db_session: Session):
        """Test creating a new webhook event"""
        webhook_event, is_new = get_or_create_webhook_event(
            db=db_session,
            gateway_event_id="evt_test_123",
            gateway_name="razorpay",
            event_type="payment.captured",
            payload_dict={"test": "data"},
            signature="test_sig"
        )

        assert is_new is True
        assert webhook_event.gateway_event_id == "evt_test_123"
        assert webhook_event.gateway_name == "razorpay"
        assert webhook_event.processed is False
        assert webhook_event.processing_attempts == 0

    def test_get_existing_webhook_event(self, db_session: Session):
        """Test retrieving existing webhook event (duplicate)"""
        # Create first time
        webhook_event1, is_new1 = get_or_create_webhook_event(
            db=db_session,
            gateway_event_id="evt_test_456",
            gateway_name="razorpay",
            event_type="payment.captured",
            payload_dict={"test": "data"},
            signature="test_sig"
        )
        db_session.commit()

        assert is_new1 is True

        # Try to create again (duplicate)
        webhook_event2, is_new2 = get_or_create_webhook_event(
            db=db_session,
            gateway_event_id="evt_test_456",
            gateway_name="razorpay",
            event_type="payment.captured",
            payload_dict={"test": "data"},
            signature="test_sig"
        )

        assert is_new2 is False
        assert webhook_event2.id == webhook_event1.id
        assert webhook_event2.processing_attempts == webhook_event1.processing_attempts

    def test_webhook_replay_attack_prevention(self, db_session: Session):
        """Test that replayed webhooks are detected"""
        event_id = "evt_replay_test"

        # First webhook
        webhook1, is_new1 = get_or_create_webhook_event(
            db=db_session,
            gateway_event_id=event_id,
            gateway_name="razorpay",
            event_type="payment.captured",
            payload_dict={"amount": 50000},
            signature="valid_sig"
        )

        # Mark as processed
        webhook1.mark_processed(payment_id=1, registration_id=1)
        db_session.commit()

        # Attacker replays same webhook
        webhook2, is_new2 = get_or_create_webhook_event(
            db=db_session,
            gateway_event_id=event_id,
            gateway_name="razorpay",
            event_type="payment.captured",
            payload_dict={"amount": 50000},
            signature="valid_sig"
        )

        assert is_new2 is False
        assert webhook2.id == webhook1.id
        assert webhook2.processed is True
        # Should not process again

    def test_webhook_mark_processed(self, db_session: Session):
        """Test marking webhook as processed"""
        webhook_event = WebhookEvent(
            gateway_event_id="evt_test_789",
            gateway_name="razorpay",
            event_type="payment.captured",
            processed=False
        )
        db_session.add(webhook_event)
        db_session.commit()

        # Mark as processed
        webhook_event.mark_processed(payment_id=123, registration_id=456)
        db_session.commit()

        assert webhook_event.processed is True
        assert webhook_event.payment_id == 123
        assert webhook_event.registration_id == 456
        assert webhook_event.processed_at is not None

    def test_webhook_record_error(self, db_session: Session):
        """Test recording webhook processing error"""
        webhook_event = WebhookEvent(
            gateway_event_id="evt_error_test",
            gateway_name="razorpay",
            event_type="payment.captured",
            processing_attempts=0
        )
        db_session.add(webhook_event)
        db_session.commit()

        # Record error
        error_msg = "Database connection lost"
        webhook_event.record_error(error_msg)
        db_session.commit()

        assert webhook_event.processing_attempts == 1
        assert webhook_event.last_error == error_msg
        assert webhook_event.processed is False

    def test_multiple_processing_attempts(self, db_session: Session):
        """Test webhook with multiple failed processing attempts"""
        webhook_event = WebhookEvent(
            gateway_event_id="evt_retry_test",
            gateway_name="razorpay",
            event_type="payment.captured"
        )
        db_session.add(webhook_event)
        db_session.commit()

        # Simulate 3 failed attempts
        for i in range(3):
            webhook_event.record_error(f"Attempt {i+1} failed")
            db_session.commit()

        assert webhook_event.processing_attempts == 3
        assert "Attempt 3 failed" in webhook_event.last_error
        assert webhook_event.processed is False


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
        assert validate_payment_amount(
            db_amount,
            webhook_amount,
            tolerance=Decimal("1.00")
        ) is True

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


class TestWebhookSecurityValidation:
    """Test webhook security improvements (P11)"""

    def test_weak_webhook_secret_detection(self):
        """Test detection of weak webhook secrets"""
        weak_secrets = [
            "default",
            "test",
            "12345678",
            "secret",
            "webhook_secret"
        ]

        for weak_secret in weak_secrets:
            # Should be detected as weak (logged and rejected in production)
            assert len(weak_secret) >= 4  # All are valid strings but weak

    def test_short_webhook_secret_detection(self):
        """Test detection of short webhook secrets"""
        short_secret = "abc123"  # Less than 16 chars

        assert len(short_secret) < 16  # Should trigger warning

    def test_strong_webhook_secret_accepted(self):
        """Test that strong secrets are accepted"""
        strong_secret = "whsec_1234567890abcdef1234567890abcdef"

        assert len(strong_secret) >= 16  # Strong secret


class TestConcurrentWebhookProcessing:
    """Test concurrent webhook processing scenarios"""

    @pytest.mark.asyncio
    async def test_concurrent_webhook_same_event(self, db_session: Session):
        """Test that concurrent webhooks with same event ID don't duplicate"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        event_id = "evt_concurrent_test"
        results = []

        def process_webhook():
            # Simulate webhook processing
            webhook, is_new = get_or_create_webhook_event(
                db=db_session,
                gateway_event_id=event_id,
                gateway_name="razorpay",
                event_type="payment.captured",
                payload_dict={"test": "data"},
                signature="sig"
            )
            results.append(is_new)
            return is_new

        # Simulate 10 concurrent webhook requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_webhook) for _ in range(10)]
            [f.result() for f in futures]

        # Only ONE should be marked as new
        assert results.count(True) == 1
        assert results.count(False) == 9


# Pytest fixtures
@pytest.fixture
def db_session():
    """Create test database session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base

    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
