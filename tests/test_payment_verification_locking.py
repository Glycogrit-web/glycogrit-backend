"""
Unit Tests for Payment Verification with Row Locking

Tests P2, P12: Payment verification race conditions
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.enums import PaymentMethod, PaymentStatus
from app.modules.payments.domain.payment import Payment


class TestPaymentVerificationLocking:
    """Test payment verification with row-level locking"""

    def test_single_payment_verification(self, db_session: Session):
        """Test normal payment verification (single thread)"""
        # Create test payment
        payment = Payment(
            user_id=1,
            registration_id=1,
            amount=Decimal("500.00"),
            currency="INR",
            payment_method="card",
            status=PaymentStatus.PENDING.value,
            gateway_order_id="order_test_123"
        )
        db_session.add(payment)
        db_session.commit()

        # Verify payment (should acquire lock and process)
        locked_payment = db_session.query(Payment).filter(
            Payment.gateway_order_id == "order_test_123"
        ).with_for_update().first()

        assert locked_payment is not None
        assert locked_payment.id == payment.id
        assert locked_payment.status == PaymentStatus.PENDING.value

        # Update to completed
        locked_payment.status = PaymentStatus.COMPLETED.value
        locked_payment.completed_at = datetime.now()
        db_session.commit()

        # Verify update
        updated_payment = db_session.query(Payment).filter(
            Payment.id == payment.id
        ).first()
        assert updated_payment.status == PaymentStatus.COMPLETED.value

    def test_idempotent_payment_verification(self, db_session: Session):
        """Test that verifying already completed payment is idempotent"""
        # Create completed payment
        payment = Payment(
            user_id=1,
            registration_id=1,
            amount=Decimal("500.00"),
            currency="INR",
            payment_method="card",
            status=PaymentStatus.COMPLETED.value,
            gateway_order_id="order_completed_123",
            completed_at=datetime.now()
        )
        db_session.add(payment)
        db_session.commit()

        # Try to verify again
        locked_payment = db_session.query(Payment).filter(
            Payment.gateway_order_id == "order_completed_123"
        ).with_for_update().first()

        # Should detect already completed
        if locked_payment.status == PaymentStatus.COMPLETED.value:
            # Skip processing (idempotent)
            pass
        else:
            # Should not reach here
            pytest.fail("Payment should already be completed")

        # Payment status unchanged
        assert locked_payment.status == PaymentStatus.COMPLETED.value

    @pytest.mark.skip(reason="SQLite in-memory doesn't support concurrent access from multiple threads")
    def test_concurrent_payment_verification_prevented(self, db_session: Session):
        """Test that concurrent verification is serialized by locking"""
        # Create test payment
        payment = Payment(
            user_id=1,
            registration_id=1,
            amount=Decimal("500.00"),
            currency="INR",
            payment_method="card",
            status=PaymentStatus.PENDING.value,
            gateway_order_id="order_concurrent_123"
        )
        db_session.add(payment)
        db_session.commit()

        verification_results = []
        verification_order = []

        def verify_payment_thread(thread_id):
            """Simulate payment verification in separate thread"""
            import time

            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            # Create new session for this thread
            engine = db_session.get_bind()
            Session = sessionmaker(bind=engine)
            thread_session = Session()

            try:
                # Acquire lock (blocks if another thread holds it)
                locked_payment = thread_session.query(Payment).filter(
                    Payment.gateway_order_id == "order_concurrent_123"
                ).with_for_update().first()

                verification_order.append(f"start_{thread_id}")

                # Check if already completed (with lock held)
                if locked_payment.status == PaymentStatus.COMPLETED.value:
                    verification_results.append("already_completed")
                    verification_order.append(f"end_{thread_id}")
                    return "already_completed"

                # Simulate some processing time
                time.sleep(0.1)

                # Mark as completed
                locked_payment.status = PaymentStatus.COMPLETED.value
                locked_payment.completed_at = datetime.now()
                thread_session.commit()

                verification_results.append("success")
                verification_order.append(f"end_{thread_id}")
                return "success"

            finally:
                thread_session.close()

        # Run 3 concurrent verification attempts
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(verify_payment_thread, i) for i in range(3)]
            [f.result() for f in as_completed(futures)]

        # Only ONE should succeed, others should see already_completed
        assert verification_results.count("success") == 1
        assert verification_results.count("already_completed") == 2

        # Verify execution was serialized (no interleaving)
        # Each thread should complete (end) before next starts
        for i in range(3):
            if f"start_{i}" in verification_order:
                start_idx = verification_order.index(f"start_{i}")
                end_idx = verification_order.index(f"end_{i}")

                # No other start/end between this thread's start and end
                between = verification_order[start_idx + 1:end_idx]
                other_markers = [m for m in between if m != f"end_{i}"]
                assert len(other_markers) == 0, f"Thread {i} execution was interleaved"

    @pytest.mark.skip(reason="SQLite in-memory doesn't support concurrent access from multiple threads")
    def test_webhook_vs_manual_verification_race(self, db_session: Session):
        """Test race between webhook and manual verification (P12)"""
        # Create pending payment
        payment = Payment(
            user_id=1,
            registration_id=1,
            amount=Decimal("500.00"),
            currency="INR",
            payment_method="card",
            status=PaymentStatus.PENDING.value,
            gateway_order_id="order_race_123"
        )
        db_session.add(payment)
        db_session.commit()

        results = []

        def manual_verification():
            """Simulate manual verification API call"""
            import time

            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            engine = db_session.get_bind()
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                # Acquire lock
                locked_payment = session.query(Payment).filter(
                    Payment.gateway_order_id == "order_race_123"
                ).with_for_update().first()

                if locked_payment.status == PaymentStatus.COMPLETED.value:
                    results.append("manual_already_completed")
                    return "already_completed"

                time.sleep(0.05)  # Processing time

                locked_payment.status = PaymentStatus.COMPLETED.value
                session.commit()
                results.append("manual_success")
                return "success"

            finally:
                session.close()

        def webhook_verification():
            """Simulate webhook processing"""
            import time

            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            engine = db_session.get_bind()
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                # Acquire lock (will wait if manual holds it)
                locked_payment = session.query(Payment).filter(
                    Payment.gateway_order_id == "order_race_123"
                ).with_for_update().first()

                if locked_payment.status == PaymentStatus.COMPLETED.value:
                    results.append("webhook_already_completed")
                    return "already_completed"

                time.sleep(0.05)  # Processing time

                locked_payment.status = PaymentStatus.COMPLETED.value
                session.commit()
                results.append("webhook_success")
                return "success"

            finally:
                session.close()

        # Start both simultaneously
        with ThreadPoolExecutor(max_workers=2) as executor:
            manual_future = executor.submit(manual_verification)
            webhook_future = executor.submit(webhook_verification)

            manual_future.result()
            webhook_future.result()

        # One succeeds, other sees already_completed
        assert results.count("manual_success") + results.count("webhook_success") == 1
        assert (results.count("manual_already_completed") +
                results.count("webhook_already_completed")) == 1

        # Final payment status is completed (exactly once)
        final_payment = db_session.query(Payment).filter(
            Payment.id == payment.id
        ).first()
        assert final_payment.status == PaymentStatus.COMPLETED.value


class TestPaymentStatusTransitions:
    """Test valid payment status transitions"""

    def test_pending_to_completed_transition(self, db_session: Session):
        """Test valid transition: pending → completed"""
        payment = Payment(
            user_id=1,
            registration_id=1,
            amount=Decimal("500.00"),
            payment_method=PaymentMethod.UPI.value,
            status=PaymentStatus.PENDING.value,
            gateway_order_id="order_transition_1"
        )
        db_session.add(payment)
        db_session.commit()

        # Transition to completed
        payment.status = PaymentStatus.COMPLETED.value
        payment.completed_at = datetime.now()
        db_session.commit()

        assert payment.status == PaymentStatus.COMPLETED.value

    def test_pending_to_failed_transition(self, db_session: Session):
        """Test valid transition: pending → failed"""
        payment = Payment(
            user_id=1,
            registration_id=1,
            amount=Decimal("500.00"),
            payment_method=PaymentMethod.UPI.value,
            status=PaymentStatus.PENDING.value,
            gateway_order_id="order_transition_2"
        )
        db_session.add(payment)
        db_session.commit()

        # Transition to failed
        payment.status = PaymentStatus.FAILED.value
        db_session.commit()

        assert payment.status == PaymentStatus.FAILED.value

    def test_completed_to_refunded_transition(self, db_session: Session):
        """Test valid transition: completed → refunded"""
        payment = Payment(
            user_id=1,
            registration_id=1,
            amount=Decimal("500.00"),
            payment_method=PaymentMethod.UPI.value,
            status=PaymentStatus.COMPLETED.value,
            completed_at=datetime.now(),
            gateway_order_id="order_transition_3"
        )
        db_session.add(payment)
        db_session.commit()

        # Transition to refunded
        payment.status = PaymentStatus.REFUNDED.value
        payment.refunded_at = datetime.now()
        db_session.commit()

        assert payment.status == PaymentStatus.REFUNDED.value


class TestPaymentLockTimeout:
    """Test payment lock timeout scenarios"""

    def test_lock_wait_timeout(self, db_session: Session):
        """Test behavior when lock wait times out"""
        # This would require setting lock_timeout in PostgreSQL
        # For SQLite (test), locks are immediate
        payment = Payment(
            user_id=1,
            registration_id=1,
            amount=Decimal("500.00"),
            payment_method=PaymentMethod.UPI.value,
            status=PaymentStatus.PENDING.value,
            gateway_order_id="order_timeout_test"
        )
        db_session.add(payment)
        db_session.commit()

        # In production with PostgreSQL:
        # SET lock_timeout = '5s';
        # If lock held > 5s, OperationalError raised

        # Acquire lock
        locked_payment = db_session.query(Payment).filter(
            Payment.gateway_order_id == "order_timeout_test"
        ).with_for_update().first()

        assert locked_payment is not None


# Pytest fixtures
@pytest.fixture
def db_session():
    """Create test database session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.database import Base

    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
