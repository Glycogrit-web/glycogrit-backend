"""
Integration tests for complete payment and registration flows.

These tests simulate real user journeys to catch integration issues.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from decimal import Decimal

from app.models.registration import Registration
from app.models.payment import Payment
from app.models.event_registration_tier import EventRegistrationTier


class TestTierUpgradeFlow:
    """Test complete tier upgrade flow from frontend to webhook."""

    def test_tier_upgrade_flow_correct_amount_single_payment(self, client: TestClient, db, test_user, test_event, test_tiers, test_registration):
        """
        CRITICAL: Complete tier upgrade should create exactly ONE payment order with correct amount.
        Bug: Frontend was creating two orders (₹20 and ₹500).
        """
        # Mock Razorpay
        with patch('app.services.payment_gateway.razorpay_gateway.razorpay') as mock_razorpay:
            mock_client = MagicMock()
            mock_client.order.create.return_value = {
                "id": "order_ABC123",
                "amount": 100000,  # ₹1000 in paise
                "currency": "INR",
                "status": "created"
            }
            mock_razorpay.Client.return_value = mock_client

            # Step 1: Call upgrade-tier endpoint
            response = client.post(
                f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
                json={"tier_id": test_tiers[2].id},  # Upgrade to premium (₹1000)
                headers={"user_id": str(test_user.id)}  # Mock auth
            )

            assert response.status_code == 200
            data = response.json()

            # Should return payment order
            assert "payment_order" in data
            assert data["payment_order"]["amount"] == 100000  # ₹1000 in paise

            # Verify only ONE payment created
            payments = db.query(Payment).filter(
                Payment.registration_id == test_registration.id,
                Payment.is_tier_upgrade == True
            ).all()

            assert len(payments) == 1, "Should create exactly ONE upgrade payment"
            assert payments[0].amount == Decimal("1000.00")
            assert payments[0].tier_id == test_tiers[2].id
            assert payments[0].status == "pending"

    def test_tier_upgrade_webhook_confirms_and_updates_tier(self, client: TestClient, db, test_registration, test_tiers):
        """
        CRITICAL: Webhook should mark payment complete AND update current_tier_id.
        Bug: Payment completed but tier not updated.
        """
        # Create pending upgrade payment
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("1000.00"),
            currency="INR",
            gateway_name="razorpay",
            razorpay_order_id="order_webhook_test",
            status="pending",
            is_tier_upgrade=True,
            tier_id=test_tiers[2].id
        )
        db.add(payment)
        db.commit()

        # Mock webhook signature verification
        with patch('app.api.webhooks.verify_razorpay_signature', return_value=True):
            # Simulate Razorpay webhook
            webhook_payload = {
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": "pay_webhook123",
                            "order_id": "order_webhook_test",
                            "amount": 100000,
                            "status": "captured"
                        }
                    }
                }
            }

            response = client.post(
                "/api/v1/webhooks/razorpay",
                json=webhook_payload,
                headers={"X-Razorpay-Signature": "test_signature"}
            )

            assert response.status_code == 200

        # Verify payment marked as completed
        db.refresh(payment)
        assert payment.status == "completed"
        assert payment.razorpay_payment_id == "pay_webhook123"

        # Verify registration tier updated
        db.refresh(test_registration)
        assert test_registration.current_tier_id == test_tiers[2].id, "Tier should be updated"
        assert test_registration.status == "confirmed"

    def test_webhook_idempotent_multiple_events(self, client: TestClient, db, test_registration, test_tiers):
        """
        CRITICAL: Multiple webhook events should not duplicate processing.
        Razorpay sends: payment.authorized → payment.captured → order.paid
        """
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("1000.00"),
            currency="INR",
            gateway_name="razorpay",
            razorpay_order_id="order_multi",
            status="pending",
            is_tier_upgrade=True,
            tier_id=test_tiers[2].id
        )
        db.add(payment)
        db.commit()

        webhook_payloads = [
            {"event": "payment.authorized"},
            {"event": "payment.captured"},
            {"event": "order.paid"}
        ]

        with patch('app.api.webhooks.verify_razorpay_signature', return_value=True):
            for payload in webhook_payloads:
                payload["payload"] = {
                    "payment": {
                        "entity": {
                            "id": "pay_multi123",
                            "order_id": "order_multi",
                            "amount": 100000
                        }
                    }
                }

                response = client.post(
                    "/api/v1/webhooks/razorpay",
                    json=payload,
                    headers={"X-Razorpay-Signature": "test_sig"}
                )

                # All should return 200
                assert response.status_code == 200

        # Should only process once
        db.refresh(payment)
        assert payment.status == "completed"

        # Registration should only be confirmed once
        db.refresh(test_registration)
        assert test_registration.status == "confirmed"


class TestRegistrationFlowEdgeCases:
    """Test edge cases in registration flow."""

    def test_cannot_upgrade_to_sold_out_tier(self, client: TestClient, db, test_registration, test_tiers):
        """
        Edge case: Should not allow upgrade to sold-out tier.
        """
        # Mark premium tier as sold out
        test_tiers[2].max_registrations = 1
        test_tiers[2].current_registrations = 1
        db.commit()

        response = client.post(
            f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
            json={"tier_id": test_tiers[2].id},
            headers={"user_id": str(test_registration.user_id)}
        )

        # Should fail
        assert response.status_code == 400
        assert "sold out" in response.json()["detail"].lower()

    def test_cannot_upgrade_to_same_tier(self, client: TestClient, test_registration):
        """
        Edge case: Upgrading to same tier should fail.
        """
        response = client.post(
            f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
            json={"tier_id": test_registration.current_tier_id},
            headers={"user_id": str(test_registration.user_id)}
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_cannot_downgrade_tier(self, client: TestClient, db, test_registration, test_tiers):
        """
        Edge case: Should not allow tier downgrade via upgrade endpoint.
        """
        # Move user to premium tier
        test_registration.current_tier_id = test_tiers[2].id
        db.commit()

        # Try to "upgrade" to basic tier (downgrade)
        response = client.post(
            f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
            json={"tier_id": test_tiers[1].id},
            headers={"user_id": str(test_registration.user_id)}
        )

        assert response.status_code == 400
        assert "lower tier" in response.json()["detail"].lower()

    def test_free_tier_upgrade_auto_confirms(self, client: TestClient, db, test_registration, test_tiers):
        """
        Edge case: Free tier upgrades should auto-confirm without payment.
        """
        # Create second free tier
        free_tier_2 = db.query(EventRegistrationTier).filter(
            EventRegistrationTier.price == Decimal("0.00")
        ).first()

        if not free_tier_2:
            pytest.skip("Need second free tier for this test")

        response = client.post(
            f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
            json={"tier_id": free_tier_2.id},
            headers={"user_id": str(test_registration.user_id)}
        )

        assert response.status_code == 200
        data = response.json()

        # Should not require payment
        assert "payment_order" not in data or data["payment_order"] is None

        # Should auto-confirm
        db.refresh(test_registration)
        assert test_registration.current_tier_id == free_tier_2.id
        assert test_registration.status == "confirmed"


class TestPaymentFailureHandling:
    """Test payment failure scenarios."""

    def test_payment_failure_webhook_marks_failed(self, client: TestClient, db, test_registration):
        """
        Test that failed payments are properly marked in database.
        """
        payment = Payment(
            registration_id=test_registration.id,
            user_id=test_registration.user_id,
            amount=Decimal("1000.00"),
            currency="INR",
            gateway_name="razorpay",
            razorpay_order_id="order_fail",
            status="pending",
            is_tier_upgrade=True
        )
        db.add(payment)
        db.commit()

        with patch('app.api.webhooks.verify_razorpay_signature', return_value=True):
            webhook_payload = {
                "event": "payment.failed",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": "pay_failed123",
                            "order_id": "order_fail",
                            "error_description": "Payment failed due to insufficient funds"
                        }
                    }
                }
            }

            response = client.post(
                "/api/v1/webhooks/razorpay",
                json=webhook_payload,
                headers={"X-Razorpay-Signature": "test_sig"}
            )

            assert response.status_code == 200

        # Verify payment marked as failed
        db.refresh(payment)
        assert payment.status == "failed"

        # Verify registration NOT upgraded
        db.refresh(test_registration)
        assert test_registration.status != "confirmed"


class TestSecurityAndAuthorization:
    """Test security-critical scenarios."""

    def test_cannot_upgrade_another_users_registration(self, client: TestClient, db, test_registration, test_tiers):
        """
        CRITICAL SECURITY: User should not be able to upgrade another user's registration.
        """
        other_user_id = test_registration.user_id + 999

        response = client.post(
            f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
            json={"tier_id": test_tiers[2].id},
            headers={"user_id": str(other_user_id)}
        )

        # Should fail with forbidden/unauthorized
        assert response.status_code in [403, 401]

    def test_webhook_without_signature_rejected(self, client: TestClient):
        """
        CRITICAL SECURITY: Webhook without signature should be rejected.
        Prevents fake payment confirmations.
        """
        webhook_payload = {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "pay_fake"}}}
        }

        response = client.post(
            "/api/v1/webhooks/razorpay",
            json=webhook_payload
            # No X-Razorpay-Signature header
        )

        assert response.status_code == 400
        assert "signature" in response.json()["detail"].lower()

    def test_webhook_with_invalid_signature_rejected(self, client: TestClient):
        """
        CRITICAL SECURITY: Webhook with wrong signature should be rejected.
        """
        webhook_payload = {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "pay_fake"}}}
        }

        with patch('app.api.webhooks.verify_razorpay_signature', return_value=False):
            response = client.post(
                "/api/v1/webhooks/razorpay",
                json=webhook_payload,
                headers={"X-Razorpay-Signature": "invalid_signature"}
            )

            assert response.status_code == 400
            assert "signature" in response.json()["detail"].lower()
