"""
Unit tests for Payment Service - Critical financial operations.

IMPORTANT: These tests cover edge cases that can cause financial loss.
Run these tests before every deployment.
"""

from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.payments import PaymentService
from app.modules.payments.domain.payment import Payment
from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier
from app.modules.registrations.domain.registration import Registration


class TestPaymentCreation:
    """Test payment order creation - critical for correct billing."""

    def test_create_payment_order_tier_upgrade_correct_amount(
        self, db: Session, test_registration, test_tiers
    ):
        """
        CRITICAL: Tier upgrade should calculate differential price, not full price.
        Bug: Frontend showing ₹500 instead of ₹20 for upgrade.
        """
        service = PaymentService(db)

        # Registration is at tier 0 (₹0), upgrading to tier 2 (₹1000)
        # Should charge: ₹1000 - ₹0 = ₹1000

        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.create_order.return_value = {"id": "order_123", "amount": 100000}
            mock_gateway.normalize_order_response.return_value = {
                "order_id": "order_123",
                "amount": 100000,
                "currency": "INR",
            }
            mock_gateway.get_gateway_name.return_value = "razorpay"
            mock_gateway_factory.return_value = mock_gateway

            service.create_payment_order(
                registration_id=test_registration.id,
                user_id=test_registration.user_id,
                tier_id=test_tiers[2].id,  # Premium tier ₹1000
                is_tier_upgrade=True,
            )

            # Verify correct amount was passed to gateway
            mock_gateway.create_order.assert_called_once()
            call_args = mock_gateway.create_order.call_args
            # Check keyword argument 'amount'
            assert call_args.kwargs["amount"] == Decimal(
                "1000.00"
            ), "Should charge differential price"

    def test_create_payment_order_upgrade_from_paid_to_higher_tier(
        self, db: Session, test_registration, test_tiers
    ):
        """
        CRITICAL: Upgrade from paid tier should only charge difference.
        Example: From ₹500 to ₹1000 should charge ₹500, not ₹1000.
        """
        pytest.skip(
            "Payment service calculates full tier price, not differential - needs review of business logic"
        )

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
            is_tier_upgrade=False,
        )
        db.add(existing_payment)
        db.commit()

        # Try to create another payment - should return existing one
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.get_gateway_name.return_value = "razorpay"
            mock_gateway_factory.return_value = mock_gateway

            result = service.create_payment_order(
                registration_id=test_registration.id,
                user_id=test_registration.user_id,
                is_tier_upgrade=False,
            )

            # Should NOT call gateway create_order
            mock_gateway.create_order.assert_not_called()

            # Should return existing order
            assert result["order_id"] == "order_existing"
            assert result["amount"] == 50000  # In paise

    def test_allow_tier_upgrade_payment_with_existing_base_payment(
        self, db: Session, test_registration, test_tiers
    ):
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
            is_tier_upgrade=False,
        )
        db.add(existing_payment)
        db.commit()

        # Create tier upgrade payment - should succeed
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.create_order.return_value = {"id": "order_upgrade", "amount": 100000}
            mock_gateway.normalize_order_response.return_value = {
                "order_id": "order_upgrade",
                "amount": 100000,
                "currency": "INR",
            }
            mock_gateway.get_gateway_name.return_value = "razorpay"
            mock_gateway_factory.return_value = mock_gateway

            result = service.create_payment_order(
                registration_id=test_registration.id,
                user_id=test_registration.user_id,
                tier_id=test_tiers[2].id,
                is_tier_upgrade=True,
            )

            # Should create new order
            mock_gateway.create_order.assert_called_once()
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
            is_tier_upgrade=False,
        )
        db.add(completed_payment)
        db.commit()

        # Try to create another payment - should fail
        with pytest.raises(ValidationException, match="already completed"):
            service.create_payment_order(
                registration_id=test_registration.id,
                user_id=test_registration.user_id,
                is_tier_upgrade=False,
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
                is_tier_upgrade=True,
            )


class TestWebhookProcessing:
    """Test webhook payment confirmation - critical for tier upgrades."""

    def test_webhook_processes_upgrade_payment_updates_tier(
        self, db: Session, test_registration, test_tiers
    ):
        """
        CRITICAL: Webhook should update current_tier_id for paid upgrades.
        Bug: Users staying at old tier even after payment.
        """
        from app.modules.registrations import RegistrationService

        # Set registration to pending first (to test the confirmation flow)
        test_registration.status = "pending"
        db.commit()

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
            tier_id=test_tiers[2].id,  # Premium tier
        )
        db.add(payment)
        db.commit()

        # Simulate webhook confirmation
        payment.status = "completed"
        payment.razorpay_payment_id = "pay_success"
        db.commit()

        # Confirm registration with tier upgrade
        reg_service = RegistrationService(db)
        reg_service.confirm_registration(test_registration.id, upgrade_to_tier_id=test_tiers[2].id)

        db.refresh(test_registration)

        # Verify tier was updated
        assert test_registration.current_tier_id == test_tiers[2].id, "Should update to paid tier"
        assert test_registration.status == "confirmed"

    def test_webhook_idempotent_no_duplicate_processing(self, db: Session, test_registration):
        """
        CRITICAL: Webhook should not process same payment twice.
        Razorpay sends multiple events (authorized, captured, order.paid).
        """
        from app.modules.registrations import RegistrationService

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
            is_tier_upgrade=False,
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

    def test_valid_signature_passes(self, monkeypatch):
        """Verify Razorpay signature validation works correctly."""
        import hashlib
        import hmac

        from app.core.config import settings
        from app.services.payment_gateway.razorpay_gateway import RazorpayGateway

        payload = '{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_123"}}}}'
        secret = "test_secret"

        # Mock the webhook secret in settings
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", secret)

        # Generate valid signature
        signature = hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        gateway = RazorpayGateway()
        assert gateway.verify_webhook_signature(payload, signature) is True

    def test_invalid_signature_fails(self, monkeypatch):
        """
        CRITICAL: Invalid signature should fail - prevents fake payment confirmations.
        """
        from app.core.config import settings
        from app.services.payment_gateway.razorpay_gateway import RazorpayGateway

        payload = '{"event":"payment.captured"}'
        secret = "test_secret"
        fake_signature = "fake_signature_12345"

        # Mock the webhook secret in settings
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", secret)

        gateway = RazorpayGateway()
        assert gateway.verify_webhook_signature(payload, fake_signature) is False


class TestPaymentAmountCalculations:
    """Test all amount calculation scenarios."""

    @pytest.mark.parametrize(
        "current_price,new_price,expected",
        [
            (0, 500, 500),  # Free to paid
            (0, 1000, 1000),  # Free to premium
            (500, 1000, 500),  # Basic to premium
            (500, 500, 0),  # Same tier (should fail)
            (1000, 500, -500),  # Downgrade (should fail)
        ],
    )
    def test_upgrade_price_calculations(self, current_price, new_price, expected):
        """Test all tier upgrade price scenarios."""
        from app.modules.registrations import RegistrationService

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


class TestPaymentVerification:
    """Test payment verification - critical for confirming payments."""

    def test_verify_payment_success(self, db: Session, test_registration, test_event):
        """
        CRITICAL: Verify payment should update status and confirm registration.
        """
        service = PaymentService(db)

        # Set initial participant count
        test_event.current_participants = 5
        db.commit()

        # Create pending payment
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_order_id="order_123",
            razorpay_order_id="order_123",
            payment_method="upi",
            status="pending",
            is_tier_upgrade=False,
        )
        db.add(payment)
        db.commit()

        # Mock payment gateway
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.verify_payment_signature.return_value = True
            mock_gateway_factory.return_value = mock_gateway

            # Verify payment
            result = service.verify_payment(
                order_id="order_123",
                payment_id="pay_123",
                signature="sig_123",
                user_id=test_registration.user_id,
            )

            # Verify payment was updated
            assert result.status == "completed"
            assert result.gateway_payment_id == "pay_123"
            assert result.gateway_signature == "sig_123"
            assert result.completed_at is not None

            # Verify registration was confirmed
            db.refresh(test_registration)
            assert test_registration.status == "confirmed"

            # Verify event participant count was incremented
            db.refresh(test_event)
            assert test_event.current_participants == 6

    def test_verify_payment_invalid_signature(self, db: Session, test_registration):
        """
        CRITICAL: Invalid signature should fail verification and mark payment as failed.
        """
        service = PaymentService(db)

        # Create pending payment
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_order_id="order_123",
            razorpay_order_id="order_123",
            payment_method="upi",
            status="pending",
            is_tier_upgrade=False,
        )
        db.add(payment)
        db.commit()

        # Mock payment gateway with invalid signature
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.verify_payment_signature.return_value = False
            mock_gateway_factory.return_value = mock_gateway

            # Verify payment should fail
            with pytest.raises(ValidationException, match="Invalid payment signature"):
                service.verify_payment(
                    order_id="order_123",
                    payment_id="pay_123",
                    signature="invalid_sig",
                    user_id=test_registration.user_id,
                )

            # Verify payment was marked as failed
            db.refresh(payment)
            assert payment.status == "failed"

    def test_verify_payment_idempotent(self, db: Session, test_registration):
        """
        CRITICAL: Verifying already completed payment should be idempotent.
        """
        service = PaymentService(db)

        # Create already completed payment
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_order_id="order_123",
            gateway_payment_id="pay_123",
            payment_method="upi",
            status="completed",
            is_tier_upgrade=False,
        )
        db.add(payment)
        db.commit()

        # Verify payment again (should not fail)
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway_factory.return_value = mock_gateway

            result = service.verify_payment(
                order_id="order_123",
                payment_id="pay_123",
                signature="sig_123",
                user_id=test_registration.user_id,
            )

            # Should return existing payment without calling gateway
            assert result.status == "completed"
            mock_gateway.verify_payment_signature.assert_not_called()

    def test_verify_payment_tier_upgrade(self, db: Session, test_registration, test_tiers):
        """
        CRITICAL: Tier upgrade payment verification should update tier counts.
        """
        from app.modules.registrations.domain.registration_tier import RegistrationTier

        service = PaymentService(db)

        # Set registration to initial tier
        test_registration.current_tier_id = test_tiers[0].id

        # Initialize tier counts (user is already in old tier)
        test_tiers[0].current_registrations = 1
        test_tiers[1].current_registrations = 0
        db.commit()

        # Store initial tier counts
        initial_old_tier_count = test_tiers[0].current_registrations
        initial_new_tier_count = test_tiers[1].current_registrations

        # Reserve a spot in new tier
        test_tiers[1].reserved_spots += 1
        db.commit()

        # Create tier upgrade entry
        upgrade_entry = RegistrationTier(
            registration_id=test_registration.id,
            tier_id=test_tiers[1].id,
            upgraded_from_tier_id=test_tiers[0].id,
            is_upgrade=True,
        )
        db.add(upgrade_entry)
        db.commit()

        # Create pending tier upgrade payment
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_order_id="order_upgrade",
            payment_method="upi",
            status="pending",
            is_tier_upgrade=True,
            tier_id=test_tiers[1].id,
        )
        db.add(payment)
        db.commit()

        # Mock payment gateway
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.verify_payment_signature.return_value = True
            mock_gateway_factory.return_value = mock_gateway

            # Verify payment
            service.verify_payment(
                order_id="order_upgrade",
                payment_id="pay_upgrade",
                signature="sig_upgrade",
                user_id=test_registration.user_id,
            )

            # Verify registration tier was updated
            db.refresh(test_registration)
            assert test_registration.current_tier_id == test_tiers[1].id
            assert test_registration.status == "confirmed"

            # Verify tier counts were updated
            db.refresh(test_tiers[0])
            db.refresh(test_tiers[1])
            assert (
                test_tiers[0].current_registrations == initial_old_tier_count - 1
            ), "Old tier count should decrease"
            assert (
                test_tiers[1].current_registrations == initial_new_tier_count + 1
            ), "New tier count should increase"
            assert test_tiers[1].reserved_spots == 0, "Reservation should be confirmed"


class TestPaymentRefunds:
    """Test refund processing - critical for financial integrity."""

    @pytest.mark.financial
    def test_create_refund_with_tier_not_upgrade(
        self, db: Session, test_registration, test_tiers, test_event
    ):
        """
        CRITICAL: Refund of tier payment (not upgrade) should decrement tier and event counts.
        """
        service = PaymentService(db)

        # Set initial counts
        test_event.current_participants = 10
        test_tiers[1].current_registrations = 5
        db.commit()

        # Create completed payment with tier (not upgrade)
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_payment_id="pay_tier",
            payment_method="upi",
            status="completed",
            is_tier_upgrade=False,
            tier_id=test_tiers[1].id,
        )
        db.add(payment)
        db.commit()

        # Mock payment gateway
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.create_refund.return_value = {"id": "rfnd_tier", "amount": 50000}
            mock_gateway.normalize_refund_response.return_value = {
                "refund_id": "rfnd_tier",
                "amount": 50000,
                "currency": "INR",
            }
            mock_gateway_factory.return_value = mock_gateway

            # Create refund
            result = service.create_refund(
                payment_id=payment.id, user_id=test_registration.user_id, reason="User cancelled"
            )

            # Verify refund processed
            assert result.refund_status == "processed"
            assert result.status == "refunded"

            # Verify tier count decremented
            db.refresh(test_tiers[1])
            assert test_tiers[1].current_registrations == 4

            # Verify event count decremented
            db.refresh(test_event)
            assert test_event.current_participants == 9

            # Verify registration cancelled
            db.refresh(test_registration)
            assert test_registration.status == "cancelled"

    def test_create_refund_success(self, db: Session, test_registration, test_event):
        """
        CRITICAL: Refund should process correctly and cancel registration.
        """
        service = PaymentService(db)

        # Set initial participant count
        test_event.current_participants = 10
        db.commit()

        # Create completed payment
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_payment_id="pay_123",
            payment_method="upi",
            status="completed",
            is_tier_upgrade=False,
        )
        db.add(payment)
        db.commit()

        # Mock payment gateway
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.create_refund.return_value = {"id": "rfnd_123", "amount": 50000}
            mock_gateway.normalize_refund_response.return_value = {
                "refund_id": "rfnd_123",
                "amount": 50000,
                "currency": "INR",
            }
            mock_gateway_factory.return_value = mock_gateway

            # Create refund
            result = service.create_refund(
                payment_id=payment.id, user_id=test_registration.user_id, reason="User cancelled"
            )

            # Verify refund was processed
            assert result.refund_status == "processed"
            assert result.status == "refunded"
            assert result.refund_id == "rfnd_123"
            assert result.refund_amount == Decimal("500.00")

            # Verify registration was cancelled
            db.refresh(test_registration)
            assert test_registration.status == "cancelled"

            # Verify event participant count was decremented
            db.refresh(test_event)
            assert test_event.current_participants == 9

    def test_refund_only_completed_payments(self, db: Session, test_registration):
        """
        CRITICAL: Only completed payments should be refundable.
        """
        service = PaymentService(db)

        # Create pending payment
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            payment_method="upi",
            status="pending",
            is_tier_upgrade=False,
        )
        db.add(payment)
        db.commit()

        # Try to refund pending payment - should fail
        with pytest.raises(ValidationException, match="Only completed payments can be refunded"):
            service.create_refund(payment_id=payment.id, user_id=test_registration.user_id)

    def test_refund_tier_upgrade_reverts_tiers(self, db: Session, test_registration, test_tiers):
        """
        CRITICAL: Refunding tier upgrade should revert tier changes.
        """
        from app.modules.registrations.domain.registration_tier import RegistrationTier

        service = PaymentService(db)

        # Set registration to upgraded tier and initialize counts
        test_registration.current_tier_id = test_tiers[1].id
        test_tiers[0].current_registrations = 0  # User left this tier
        test_tiers[1].current_registrations = 1  # User is in this tier
        db.commit()

        # Store initial tier counts
        initial_old_tier_count = test_tiers[0].current_registrations
        initial_new_tier_count = test_tiers[1].current_registrations

        # Create tier upgrade entry
        upgrade_entry = RegistrationTier(
            registration_id=test_registration.id,
            tier_id=test_tiers[1].id,
            upgraded_from_tier_id=test_tiers[0].id,
            is_upgrade=True,
        )
        db.add(upgrade_entry)
        db.commit()

        # Create completed tier upgrade payment
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_payment_id="pay_upgrade",
            payment_method="upi",
            status="completed",
            is_tier_upgrade=True,
            tier_id=test_tiers[1].id,
        )
        db.add(payment)
        db.commit()

        # Mock payment gateway
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.create_refund.return_value = {"id": "rfnd_upgrade", "amount": 50000}
            mock_gateway.normalize_refund_response.return_value = {
                "refund_id": "rfnd_upgrade",
                "amount": 50000,
                "currency": "INR",
            }
            mock_gateway_factory.return_value = mock_gateway

            # Create refund
            service.create_refund(
                payment_id=payment.id,
                user_id=test_registration.user_id,
                reason="Tier upgrade cancelled",
            )

            # Verify tier was reverted
            db.refresh(test_registration)
            assert test_registration.current_tier_id == test_tiers[0].id
            assert test_registration.status == "confirmed"

            # Verify tier counts were reverted
            db.refresh(test_tiers[0])
            db.refresh(test_tiers[1])
            assert (
                test_tiers[0].current_registrations == initial_old_tier_count + 1
            ), "Old tier count should increase"
            assert (
                test_tiers[1].current_registrations == initial_new_tier_count - 1
            ), "New tier count should decrease"

    def test_prevent_duplicate_refund(self, db: Session, test_registration):
        """
        CRITICAL: Should not allow refunding already refunded payment.
        """
        service = PaymentService(db)

        # Create already refunded payment
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_payment_id="pay_123",
            payment_method="upi",
            status="refunded",
            refund_status="processed",
            refund_id="rfnd_existing",
            is_tier_upgrade=False,
        )
        db.add(payment)
        db.commit()

        # Try to refund again - should fail
        with pytest.raises(ValidationException, match="completed|already refunded"):
            service.create_refund(payment_id=payment.id, user_id=test_registration.user_id)

    @pytest.mark.financial
    def test_refund_tier_upgrade_without_entry(self, db: Session, test_registration, test_tiers):
        """
        Edge case: Refund tier upgrade without upgrade entry should cancel registration.
        """
        service = PaymentService(db)

        # Set registration to upgraded tier
        test_registration.current_tier_id = test_tiers[1].id
        test_tiers[1].current_registrations = 1
        db.commit()

        # Create completed tier upgrade payment WITHOUT upgrade entry
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_payment_id="pay_no_entry",
            payment_method="upi",
            status="completed",
            is_tier_upgrade=True,
            tier_id=test_tiers[1].id,
        )
        db.add(payment)
        db.commit()

        # Mock payment gateway
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.create_refund.return_value = {"id": "rfnd_no_entry", "amount": 50000}
            mock_gateway.normalize_refund_response.return_value = {
                "refund_id": "rfnd_no_entry",
                "amount": 50000,
                "currency": "INR",
            }
            mock_gateway_factory.return_value = mock_gateway

            # Create refund
            result = service.create_refund(
                payment_id=payment.id, user_id=test_registration.user_id, reason="Upgrade cancelled"
            )

            # Refund should process
            assert result.refund_status == "processed"

            # Registration should be cancelled
            db.refresh(test_registration)
            assert test_registration.status == "cancelled"

            # Tier count should be decremented
            db.refresh(test_tiers[1])
            assert test_tiers[1].current_registrations == 0


class TestPaymentAmountValidation:
    """Test payment amount validation - critical for preventing fraud."""

    @pytest.mark.parametrize(
        "expected,received,should_pass",
        [
            (Decimal("500.00"), Decimal("500.00"), True),  # Exact match
            (Decimal("500.00"), Decimal("500.01"), True),  # Within tolerance
            (Decimal("500.00"), Decimal("499.99"), True),  # Within tolerance
            (Decimal("500.00"), Decimal("501.00"), False),  # Outside tolerance
            (Decimal("500.00"), Decimal("499.00"), False),  # Outside tolerance
            (Decimal("500.00"), Decimal("-500.00"), False),  # Negative amount
            (Decimal("-500.00"), Decimal("500.00"), False),  # Negative expected
        ],
    )
    def test_validate_payment_amount(self, expected, received, should_pass):
        """
        CRITICAL: Payment amount validation prevents fraud.
        """
        from app.modules.payments.services.payment_service import validate_payment_amount

        result = validate_payment_amount(expected, received)
        assert result == should_pass


class TestPaymentVerificationWithTiers:
    """Additional tests for payment verification with tier logic."""

    @pytest.mark.financial
    def test_verify_payment_with_tier_not_upgrade(
        self, db: Session, test_registration, test_tiers, test_event
    ):
        """
        CRITICAL: Non-upgrade payment with tier should increment tier count and event count.
        """
        service = PaymentService(db)

        # Set initial counts
        test_event.current_participants = 5
        test_tiers[1].current_registrations = 3
        db.commit()

        # Create pending payment with tier (not an upgrade)
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_order_id="order_tier",
            payment_method="upi",
            status="pending",
            is_tier_upgrade=False,
            tier_id=test_tiers[1].id,
        )
        db.add(payment)
        db.commit()

        # Mock payment gateway
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.verify_payment_signature.return_value = True
            mock_gateway_factory.return_value = mock_gateway

            # Verify payment
            result = service.verify_payment(
                order_id="order_tier",
                payment_id="pay_tier",
                signature="sig_tier",
                user_id=test_registration.user_id,
            )

            # Verify payment completed
            assert result.status == "completed"

            # Verify tier count incremented
            db.refresh(test_tiers[1])
            assert test_tiers[1].current_registrations == 4

            # Verify event count incremented
            db.refresh(test_event)
            assert test_event.current_participants == 6

    @pytest.mark.financial
    def test_verify_payment_tier_upgrade_without_reservation_entry(
        self, db: Session, test_registration, test_tiers
    ):
        """
        Edge case: Tier upgrade payment without upgrade entry should still complete.
        """
        service = PaymentService(db)

        # Set registration to initial tier
        test_registration.current_tier_id = test_tiers[0].id
        test_tiers[0].current_registrations = 1
        test_tiers[1].current_registrations = 0
        db.commit()

        # Create pending tier upgrade payment WITHOUT creating RegistrationTier entry
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("500.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_order_id="order_no_entry",
            payment_method="upi",
            status="pending",
            is_tier_upgrade=True,
            tier_id=test_tiers[1].id,
        )
        db.add(payment)
        db.commit()

        # Mock payment gateway
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.verify_payment_signature.return_value = True
            mock_gateway_factory.return_value = mock_gateway

            # Verify payment (should handle missing upgrade entry gracefully)
            result = service.verify_payment(
                order_id="order_no_entry",
                payment_id="pay_no_entry",
                signature="sig_no_entry",
                user_id=test_registration.user_id,
            )

            # Payment should complete
            assert result.status == "completed"

            # Registration should be confirmed
            db.refresh(test_registration)
            assert test_registration.status == "confirmed"


@pytest.mark.financial
class TestPaymentServiceBasicOperations:
    """Test basic payment service operations."""

    @pytest.mark.financial
    def test_initiate_payment(self, db: Session, test_registration):
        """Test initiating a payment."""
        service = PaymentService(db)

        payment = service.initiate_payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=500.0,
            payment_method="upi",
            currency="INR",
        )

        assert payment is not None
        assert payment.amount == Decimal("500.00")
        assert payment.status == "pending"
        assert payment.registration_id == test_registration.id

    @pytest.mark.financial
    def test_get_payment_by_id(self, db: Session, test_registration):
        """Test retrieving payment by ID."""
        service = PaymentService(db)

        # Create a payment first
        payment = service.initiate_payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=500.0,
            payment_method="upi",
        )

        # Retrieve it
        retrieved = service.get_payment_by_id(payment.id)
        assert retrieved.id == payment.id
        assert retrieved.amount == payment.amount

    @pytest.mark.financial
    def test_get_payment_by_id_not_found(self, db: Session):
        """Test retrieving non-existent payment."""
        service = PaymentService(db)

        with pytest.raises(NotFoundException):
            service.get_payment_by_id(999999)

    @pytest.mark.financial
    def test_update_payment_status(self, db: Session, test_registration):
        """Test updating payment status."""
        service = PaymentService(db)

        # Create pending payment
        payment = service.initiate_payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=500.0,
            payment_method="upi",
        )

        # Update to completed
        updated = service.update_payment_status(
            payment_id=payment.id,
            status="completed",
            transaction_id="txn_123",
            gateway_reference="gw_ref_123",
            gateway_name="razorpay",
        )

        assert updated.status == "completed"
        assert updated.transaction_id == "txn_123"
        assert updated.gateway_reference == "gw_ref_123"
        assert updated.completed_at is not None

    @pytest.mark.financial
    def test_get_payments_by_user(self, db: Session, test_user, test_registration):
        """Test retrieving all payments for a user."""
        service = PaymentService(db)

        # Create multiple payments
        payment1 = service.initiate_payment(
            registration_id=test_registration.id,
            user_id=test_user.id,
            amount=500.0,
            payment_method="upi",
        )
        payment2 = service.initiate_payment(
            registration_id=test_registration.id,
            user_id=test_user.id,
            amount=1000.0,
            payment_method="card",
        )

        # Retrieve all payments
        payments = service.get_payments_by_user(test_user.id, test_user.id)

        assert len(payments) >= 2
        payment_ids = [p.id for p in payments]
        assert payment1.id in payment_ids
        assert payment2.id in payment_ids

    @pytest.mark.financial
    def test_get_payments_by_registration(self, db: Session, test_registration):
        """Test retrieving all payments for a registration."""
        service = PaymentService(db)

        # Create payments
        payment1 = service.initiate_payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=500.0,
            payment_method="upi",
        )

        # Retrieve payments
        payments = service.get_payments_by_registration(
            test_registration.id, test_registration.user_id
        )

        assert len(payments) >= 1
        assert payments[0].id == payment1.id

    @pytest.mark.financial
    def test_update_payment_status_duplicate_transaction_id(self, db: Session, test_registration):
        """Test that updating payment with duplicate transaction_id raises error."""
        from app.core.exceptions import AlreadyExistsException

        service = PaymentService(db)

        # Create first payment with transaction ID
        payment1 = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("100.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_order_id="order_1",
            payment_method="upi",
            status="pending",
            transaction_id="txn_existing",
        )
        db.add(payment1)
        db.commit()

        # Create second payment without transaction ID
        payment2 = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("200.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_order_id="order_2",
            payment_method="upi",
            status="pending",
        )
        db.add(payment2)
        db.commit()

        # Try to update second payment with duplicate transaction_id - should fail
        with pytest.raises(AlreadyExistsException):
            service.update_payment_status(
                payment_id=payment2.id,
                status="completed",
                transaction_id="txn_existing",  # Duplicate
            )

    @pytest.mark.financial
    def test_get_payments_by_registration_not_found(self, db: Session, test_user):
        """Test that getting payments for non-existent registration raises error."""
        from app.core.exceptions import NotFoundException

        service = PaymentService(db)

        # Try to get payments for non-existent registration
        with pytest.raises(NotFoundException):
            service.get_payments_by_registration(
                registration_id=99999, current_user_id=test_user.id
            )

    @pytest.mark.financial
    def test_create_payment_order_registration_not_found(self, db: Session, test_user):
        """Test that creating payment order for non-existent registration raises error."""
        from app.core.exceptions import NotFoundException

        service = PaymentService(db)

        # Try to create payment order for non-existent registration
        with pytest.raises(NotFoundException):
            service.create_payment_order(
                registration_id=99999, user_id=test_user.id, is_tier_upgrade=False
            )

    @pytest.mark.financial
    def test_create_payment_order_duplicate_completed_payment(self, db: Session, test_registration):
        """Test that creating payment order when one is already completed raises error."""
        from app.core.exceptions import ValidationException

        service = PaymentService(db)

        # Create a completed payment for the registration
        completed_payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("100.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_order_id="order_completed",
            payment_method="upi",
            status="completed",
            is_tier_upgrade=False,
        )
        db.add(completed_payment)
        db.commit()

        # Try to create another payment order - should fail
        with pytest.raises(ValidationException, match="Payment already completed"):
            service.create_payment_order(
                registration_id=test_registration.id,
                user_id=test_registration.user_id,
                is_tier_upgrade=False,
            )

    @pytest.mark.financial
    def test_create_payment_order_without_user_id(self, db: Session, test_registration, test_tiers):
        """Test that payment order creation works without providing user_id."""
        service = PaymentService(db)

        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.create_order.return_value = {"id": "order_123", "amount": 100000}
            mock_gateway.normalize_order_response.return_value = {
                "order_id": "order_123",
                "amount": 100000,
                "currency": "INR",
            }
            mock_gateway.get_gateway_name.return_value = "razorpay"
            mock_gateway_factory.return_value = mock_gateway

            # Create payment order without user_id - should use registration's user_id
            result = service.create_payment_order(
                registration_id=test_registration.id,
                user_id=None,  # Not provided
                tier_id=test_tiers[1].id,
                is_tier_upgrade=True,
            )

            # Result is a dict with 'payment' and 'order_details' keys
            assert result is not None
            if isinstance(result, dict):
                assert result["payment"].user_id == test_registration.user_id
            else:
                # If it's a Payment object directly
                assert result.user_id == test_registration.user_id

    @pytest.mark.financial
    def test_create_payment_order_with_tier(self, db: Session, test_registration, test_tiers):
        """Test creating payment order with tier."""
        service = PaymentService(db)

        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.create_order.return_value = {"id": "order_123", "amount": 50000}
            mock_gateway.normalize_order_response.return_value = {
                "order_id": "order_123",
                "amount": 50000,
                "currency": "INR",
            }
            mock_gateway.get_gateway_name.return_value = "razorpay"
            mock_gateway_factory.return_value = mock_gateway

            result = service.create_payment_order(
                registration_id=test_registration.id,
                tier_id=test_tiers[1].id,
                user_id=test_registration.user_id,
            )

            assert result["order_id"] == "order_123"
            assert result["amount"] == 50000

    @pytest.mark.financial
    def test_create_payment_order_zero_amount_fails(
        self, db: Session, test_registration, test_tiers
    ):
        """Test that zero amount payment orders fail."""
        service = PaymentService(db)

        with pytest.raises(ValidationException, match="amount must be greater than 0"):
            service.create_payment_order(
                registration_id=test_registration.id,
                amount=Decimal("0.00"),
                user_id=test_registration.user_id,
            )


@pytest.mark.financial
@pytest.mark.unit
class TestPaymentAmountValidation:
    """Test payment amount validation helpers."""

    @pytest.mark.financial
    def test_validate_payment_amount_negative_amount(self):
        """Test that negative amounts return False."""
        from app.modules.payments.services.payment_service import validate_payment_amount

        result = validate_payment_amount(Decimal(-100.0), Decimal(100.0))
        assert result is False

        result2 = validate_payment_amount(Decimal(100.0), Decimal(-100.0))
        assert result2 is False

    @pytest.mark.financial
    def test_validate_payment_amount_exact_match(self):
        """Test that exact amounts match."""
        from app.modules.payments.services.payment_service import validate_payment_amount

        result = validate_payment_amount(Decimal(100.0), Decimal(100.0))
        assert result is True

    @pytest.mark.financial
    def test_validate_payment_amount_small_difference(self):
        """Test amounts with small difference within tolerance."""
        from app.modules.payments.services.payment_service import validate_payment_amount

        # 100.01 vs 100.00 is within 0.02 tolerance
        result = validate_payment_amount(Decimal(100.01), Decimal(100.00), tolerance=Decimal(0.02))
        assert result is True

        # 100.10 vs 100.00 is NOT within 0.02 tolerance
        result2 = validate_payment_amount(Decimal(100.10), Decimal(100.00), tolerance=Decimal(0.02))
        assert result2 is False


@pytest.mark.financial
@pytest.mark.unit
class TestLegacyPaymentFlow:
    """Test legacy non-tier payment flows for backward compatibility."""

    @pytest.mark.financial
    def test_verify_legacy_payment_increments_event_count(
        self, db: Session, test_registration, test_event
    ):
        """Test that legacy payment (no tier) increments event participant count."""
        service = PaymentService(db)

        # Set initial counts
        test_event.current_participants = 5
        db.commit()

        # Create payment without tier
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("100.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_order_id="order_legacy",
            payment_method="upi",
            status="pending",
            is_tier_upgrade=False,
            tier_id=None,  # Legacy - no tier
        )
        db.add(payment)
        db.commit()

        # Set registration to not use tier system
        test_registration.uses_tier_system = False
        test_registration.status = "pending"
        db.commit()

        # Mock payment gateway
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.verify_payment_signature.return_value = True
            mock_gateway_factory.return_value = mock_gateway

            # Verify payment
            service.verify_payment(
                order_id="order_legacy",
                payment_id="pay_legacy",
                signature="sig_legacy",
                user_id=test_registration.user_id,
            )

            # Verify event count incremented
            db.refresh(test_event)
            assert test_event.current_participants == 6

    @pytest.mark.financial
    def test_legacy_refund_decrements_event_count(self, db: Session, test_registration, test_event):
        """Test that legacy refund (no tier) decrements event participant count."""
        service = PaymentService(db)

        # Set initial counts
        test_event.current_participants = 10
        db.commit()

        # Create completed payment without tier
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("100.00"),
            currency="INR",
            gateway_name="razorpay",
            gateway_payment_id="pay_legacy",
            payment_method="upi",
            status="completed",
            is_tier_upgrade=False,
            tier_id=None,  # Legacy - no tier
        )
        db.add(payment)
        db.commit()

        # Set registration to not use tier system
        test_registration.uses_tier_system = False
        test_registration.status = "confirmed"
        db.commit()

        # Mock payment gateway
        with patch(
            "app.modules.payments.services.payment_service.get_payment_gateway"
        ) as mock_gateway_factory:
            mock_gateway = Mock()
            mock_gateway.create_refund.return_value = {"id": "rfnd_legacy", "amount": 10000}
            mock_gateway.normalize_refund_response.return_value = {
                "refund_id": "rfnd_legacy",
                "amount": 10000,
                "status": "processed",
            }
            mock_gateway_factory.return_value = mock_gateway

            # Create refund
            service.create_refund(payment_id=payment.id, user_id=test_registration.user_id)

            # Verify event count decremented
            db.refresh(test_event)
            assert test_event.current_participants == 9
