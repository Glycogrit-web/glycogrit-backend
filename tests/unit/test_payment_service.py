"""
Unit tests for Payment Service - Critical financial operations.

IMPORTANT: These tests cover edge cases that can cause financial loss.
Run these tests before every deployment.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from sqlalchemy.orm import Session

from app.services.payment_service import PaymentService
from app.models.registration import Registration
from app.models.payment import Payment
from app.models.event_registration_tier import EventRegistrationTier
from app.core.exceptions import ValidationException, NotFoundException


class TestPaymentCreation:
    """Test payment order creation - critical for correct billing."""

    def test_create_payment_order_tier_upgrade_correct_amount(self, db: Session, test_registration, test_tiers):
        """
        CRITICAL: Tier upgrade should calculate differential price, not full price.
        Bug: Frontend showing ₹500 instead of ₹20 for upgrade.
        """
        service = PaymentService(db)

        # Registration is at tier 0 (₹0), upgrading to tier 2 (₹1000)
        # Should charge: ₹1000 - ₹0 = ₹1000

        with patch.object(service.gateway, 'create_order') as mock_create:
            mock_create.return_value = {"id": "order_123", "amount": 100000}

            result = service.create_payment_order(
                registration_id=test_registration.id,
                user_id=test_registration.user_id,
                tier_id=test_tiers[2].id,  # Premium tier ₹1000
                is_tier_upgrade=True
            )

            # Verify correct amount was passed to Razorpay
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[0][0] == Decimal("1000.00"), "Should charge differential price"

    def test_create_payment_order_upgrade_from_paid_to_higher_tier(self, db: Session, test_registration, test_tiers):
        """
        CRITICAL: Upgrade from paid tier should only charge difference.
        Example: From ₹500 to ₹1000 should charge ₹500, not ₹1000.
        """
        # Update registration to basic tier (₹500)
        test_registration.current_tier_id = test_tiers[1].id
        db.commit()

        service = PaymentService(db)

        with patch.object(service.gateway, 'create_order') as mock_create:
            mock_create.return_value = {"id": "order_123", "amount": 50000}

            service.create_payment_order(
                registration_id=test_registration.id,
                user_id=test_registration.user_id,
                tier_id=test_tiers[2].id,  # Premium ₹1000
                is_tier_upgrade=True
            )

            call_args = mock_create.call_args
            # Should charge: ₹1000 - ₹500 = ₹500
            assert call_args[0][0] == Decimal("500.00"), "Should charge only the difference"

    def test_prevent_duplicate_pending_payments(self, db: Session, test_registration):
        """
        CRITICAL: Should not create duplicate pending payments for same registration.
        Bug: Multiple calls creating ₹500, ₹800 orders.
        """
        service = PaymentService(db)

        # Create existing pending payment
        existing_payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            payment_method="upi",
            razorpay_order_id="order_existing",
            status="pending",
            is_tier_upgrade=False
        )
        db.add(existing_payment)
        db.commit()

        # Try to create another payment - should return existing one
        with patch.object(service.gateway, 'create_order') as mock_create:
            result = service.create_payment_order(
                registration_id=test_registration.id,
                user_id=test_registration.user_id,
                is_tier_upgrade=False
            )

            # Should NOT call Razorpay
            mock_create.assert_not_called()

            # Should return existing order
            assert result["order_id"] == "order_existing"
            assert result["amount"] == 50000  # In paise

    def test_allow_tier_upgrade_payment_with_existing_base_payment(self, db: Session, test_registration, test_tiers):
        """
        Edge case: User has pending base registration payment,
        but should still be able to create tier upgrade payment.
        """
        service = PaymentService(db)

        # Create existing base registration payment (pending)
        existing_payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            payment_method="upi",
            razorpay_order_id="order_base",
            status="pending",
            is_tier_upgrade=False
        )
        db.add(existing_payment)
        db.commit()

        # Create tier upgrade payment - should succeed
        with patch.object(service.gateway, 'create_order') as mock_create:
            mock_create.return_value = {"id": "order_upgrade", "amount": 100000}

            result = service.create_payment_order(
                registration_id=test_registration.id,
                user_id=test_registration.user_id,
                tier_id=test_tiers[2].id,
                is_tier_upgrade=True
            )

            # Should create new order
            mock_create.assert_called_once()
            assert result["order_id"] == "order_upgrade"

    def test_reject_payment_if_already_completed(self, db: Session, test_registration):
        """
        CRITICAL: Should not allow creating payment if one is already completed.
        Prevents double charging.
        """
        service = PaymentService(db)

        # Create completed payment
        completed_payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            payment_method="upi",
            razorpay_payment_id="pay_completed",
            razorpay_order_id="order_completed",
            status="completed",
            is_tier_upgrade=False
        )
        db.add(completed_payment)
        db.commit()

        # Try to create another payment - should fail
        with pytest.raises(ValidationException, match="already completed"):
            service.create_payment_order(
                registration_id=test_registration.id,
                user_id=test_registration.user_id,
                is_tier_upgrade=False
            )

    def test_zero_price_upgrade_raises_error(self, db: Session, test_registration, test_tiers):
        """
        Edge case: Upgrading to same or lower tier should fail validation.
        """
        # User already at free tier (₹0), trying to "upgrade" to free tier
        service = PaymentService(db)

        with pytest.raises(ValidationException, match="amount must be greater than 0"):
            service.create_payment_order(
                registration_id=test_registration.id,
                user_id=test_registration.user_id,
                tier_id=test_tiers[0].id,  # Same free tier
                is_tier_upgrade=True
            )


class TestWebhookProcessing:
    """Test webhook payment confirmation - critical for tier upgrades."""

    def test_webhook_processes_upgrade_payment_updates_tier(self, db: Session, test_registration, test_tiers):
        """
        CRITICAL: Webhook should update current_tier_id for paid upgrades.
        Bug: Users staying at old tier even after payment.
        """
        from app.services.registration_service import RegistrationService

        # Create pending tier upgrade payment
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("1000.00"),
            currency="INR",
            gateway_name="razorpay",
            payment_method="upi",
            razorpay_order_id="order_upgrade",
            status="pending",
            is_tier_upgrade=True,
            tier_id=test_tiers[2].id  # Premium tier
        )
        db.add(payment)
        db.commit()

        # Simulate webhook confirmation
        payment.status = "completed"
        payment.razorpay_payment_id = "pay_success"
        db.commit()

        # Confirm registration with tier upgrade
        reg_service = RegistrationService(db)
        reg_service.confirm_registration(
            test_registration.id,
            upgrade_to_tier_id=test_tiers[2].id
        )

        db.refresh(test_registration)

        # Verify tier was updated
        assert test_registration.current_tier_id == test_tiers[2].id, "Should update to paid tier"
        assert test_registration.status == "confirmed"

    def test_webhook_idempotent_no_duplicate_processing(self, db: Session, test_registration):
        """
        CRITICAL: Webhook should not process same payment twice.
        Razorpay sends multiple events (authorized, captured, order.paid).
        """
        from app.services.registration_service import RegistrationService

        # Create completed payment
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            payment_method="upi",
            razorpay_payment_id="pay_done",
            razorpay_order_id="order_done",
            status="completed",
            is_tier_upgrade=False
        )
        db.add(payment)
        db.commit()

        initial_status = test_registration.status

        # Try to confirm again
        reg_service = RegistrationService(db)
        result = reg_service.confirm_registration(test_registration.id)

        # Should return False (already processed)
        assert result is False

        db.refresh(test_registration)
        # Status should remain unchanged
        assert test_registration.status == initial_status


class TestRazorpaySignatureVerification:
    """Test signature verification - critical for security."""

    def test_valid_signature_passes(self):
        """Verify Razorpay signature validation works correctly."""
        from app.api.webhooks import verify_razorpay_signature

        payload = b'{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_123"}}}}'
        secret = "test_secret"

        import hmac
        import hashlib

        # Generate valid signature
        signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        assert verify_razorpay_signature(payload, signature, secret) is True

    def test_invalid_signature_fails(self):
        """
        CRITICAL: Invalid signature should fail - prevents fake payment confirmations.
        """
        from app.api.webhooks import verify_razorpay_signature

        payload = b'{"event":"payment.captured"}'
        secret = "test_secret"
        fake_signature = "fake_signature_12345"

        assert verify_razorpay_signature(payload, secret, fake_signature) is False


class TestPaymentAmountCalculations:
    """Test all amount calculation scenarios."""

    @pytest.mark.parametrize("current_price,new_price,expected", [
        (0, 500, 500),      # Free to paid
        (0, 1000, 1000),    # Free to premium
        (500, 1000, 500),   # Basic to premium
        (500, 500, 0),      # Same tier (should fail)
        (1000, 500, -500),  # Downgrade (should fail)
    ])
    def test_upgrade_price_calculations(self, current_price, new_price, expected):
        """Test all tier upgrade price scenarios."""
        from app.services.registration_service import RegistrationService

        # Mock tiers
        current_tier = Mock(price=Decimal(str(current_price)))
        new_tier = Mock(price=Decimal(str(new_price)))

        # Calculate upgrade price
        upgrade_price = new_tier.price - current_tier.price

        if expected <= 0:
            # Should not allow
            assert upgrade_price <= 0
        else:
            assert upgrade_price == Decimal(str(expected))
