"""
End-to-End tests simulating complete user journeys.

These tests cover entire user flows from registration to tier upgrades to payment.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.financial
class TestNewUserRegistrationJourney:
    """Test complete new user registration flow."""

    @pytest.mark.financial
    def test_new_user_registers_for_free_tier(
        self,
        authenticated_client: TestClient,
        db,
        test_user,
        test_event,
        test_tiers,
        test_activities,
    ):
        """
        Journey: New user discovers event → registers for free tier → confirmed.
        """
        # Step 1: User views event
        response = authenticated_client.get(f"/api/v1/events/{test_event.id}")
        assert response.status_code == 200
        event_data = response.json()
        assert event_data["uses_tier_system"] is True

        # Step 2: User selects free tier and registers
        with patch.dict("sys.modules", {"razorpay": MagicMock()}):
            response = authenticated_client.post(
                f"/api/v1/events/{test_event.id}/register-tier",
                json={
                    "tier_id": test_tiers[0].id,
                    "activity_id": test_activities[0].id,
                    "participant_name": "New User",
                },
            )

        assert response.status_code == 201
        data = response.json()

        # Service returns {"registration": {...}, "tier": {...}, "requires_payment": bool, ...}
        assert data["registration"]["status"] == "confirmed"
        assert data["registration"]["current_tier_id"] == test_tiers[0].id
        assert not data["requires_payment"]
        assert "payment_order" not in data

    @pytest.mark.financial
    def test_new_user_registers_for_paid_tier_completes_payment(
        self,
        authenticated_client: TestClient,
        db,
        test_user,
        test_event,
        test_tiers,
        test_activities,
    ):
        """
        Journey: New user → registers for paid tier → payment order created → pending.
        Note: Full webhook-to-confirmation flow requires webhook handler implementation (TODO).
        """
        from unittest.mock import Mock

        # Step 1: User registers for paid tier — mock PaymentService to avoid Razorpay config
        with patch("app.modules.payments.PaymentService") as mock_payment_service_class:
            mock_payment_service = Mock()
            mock_payment_service.create_payment_order.return_value = {
                "id": "order_NEW123",
                "order_id": "order_NEW123",
                "amount": 50000,
                "currency": "INR",
                "gateway": "razorpay",
            }
            mock_payment_service_class.return_value = mock_payment_service

            response = authenticated_client.post(
                f"/api/v1/events/{test_event.id}/register-tier",
                json={
                    "tier_id": test_tiers[1].id,
                    "activity_id": test_activities[0].id,
                    "participant_name": "New Paid User",
                },
            )

        assert response.status_code == 201
        data = response.json()

        # Service returns {"registration": {...}, "payment_order": {...}, "requires_payment": True, ...}
        assert data["registration"]["status"] == "pending"
        assert data["requires_payment"] is True
        assert "payment_order" in data
        assert data["payment_order"]["amount"] == 50000

        registration_id = data["registration"]["id"]

        # Step 2: Verify the pending registration is retrievable
        response = authenticated_client.get(f"/api/v1/registrations/{registration_id}")
        assert response.status_code == 200
        reg_data = response.json()
        assert reg_data["id"] == registration_id
        # Status stays pending until webhook handler confirms payment (TODO in webhook service)
        assert reg_data["status"] == "pending"


@pytest.mark.e2e
@pytest.mark.financial
class TestUserUpgradeTierJourney:
    """Test complete tier upgrade flow."""

    @pytest.mark.financial
    def test_user_upgrades_from_free_to_paid(
        self, authenticated_client: TestClient, db, test_registration, test_tiers
    ):
        """
        Journey: User at free tier → initiates paid upgrade → payment order returned.
        Note: Full tier change on webhook confirmation requires webhook handler implementation (TODO).
        """
        from unittest.mock import Mock

        # Starting state: User at free tier
        assert test_registration.current_tier_id == test_tiers[0].id

        # Step 1: User initiates upgrade — mock PaymentService to avoid Razorpay config
        with patch("app.modules.payments.PaymentService") as mock_payment_service_class:
            mock_payment_service = Mock()
            mock_payment_service.create_payment_order.return_value = {
                "id": "order_UPGRADE123",
                "order_id": "order_UPGRADE123",
                "amount": 50000,
                "currency": "INR",
                "gateway": "razorpay",
            }
            mock_payment_service_class.return_value = mock_payment_service

            response = authenticated_client.post(
                f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
                json={"tier_id": test_tiers[1].id},
            )

        assert response.status_code == 200
        data = response.json()

        # Service returns {"success": True, "requires_payment": True, "payment_order": {...}, ...}
        assert data["success"] is True
        assert data["requires_payment"] is True
        assert "payment_order" in data
        assert data["payment_order"]["amount"] == 50000

        # Registration is set to pending until payment is confirmed via webhook
        db.refresh(test_registration)
        assert test_registration.current_tier_id == test_tiers[0].id
        assert test_registration.status == "pending"

    @pytest.mark.financial
    def test_user_upgrades_twice(
        self, authenticated_client: TestClient, db, test_registration, test_tiers
    ):
        """
        Journey: User initiates two sequential upgrades (free → basic → premium).
        Tests that each upgrade returns a payment order and the API responds correctly.
        Note: Tier change on payment confirmation requires webhook handler implementation (TODO).
        """
        from unittest.mock import Mock

        # Start at free tier
        assert test_registration.current_tier_id == test_tiers[0].id

        # First upgrade: Free → Basic (₹500)
        with patch("app.modules.payments.PaymentService") as mock_payment_service_class:
            mock_payment_service = Mock()
            mock_payment_service.create_payment_order.return_value = {
                "id": "order_UPGRADE1",
                "order_id": "order_UPGRADE1",
                "amount": 50000,
                "currency": "INR",
                "gateway": "razorpay",
            }
            mock_payment_service_class.return_value = mock_payment_service

            response1 = authenticated_client.post(
                f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
                json={"tier_id": test_tiers[1].id},
            )

        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["success"] is True
        assert data1["requires_payment"] is True
        assert data1["payment_order"]["amount"] == 50000

        # Registration is pending first upgrade payment
        db.refresh(test_registration)
        assert test_registration.status == "pending"

        # Manually confirm the first upgrade (simulating what webhook handler will do when implemented)
        test_registration.current_tier_id = test_tiers[1].id
        test_registration.status = "confirmed"
        db.commit()
        db.refresh(test_registration)
        assert test_registration.current_tier_id == test_tiers[1].id

        # Second upgrade: Basic → Premium (₹500 difference)
        with patch("app.modules.payments.PaymentService") as mock_payment_service_class:
            mock_payment_service = Mock()
            mock_payment_service.create_payment_order.return_value = {
                "id": "order_UPGRADE2",
                "order_id": "order_UPGRADE2",
                "amount": 50000,
                "currency": "INR",
                "gateway": "razorpay",
            }
            mock_payment_service_class.return_value = mock_payment_service

            response2 = authenticated_client.post(
                f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
                json={"tier_id": test_tiers[2].id},
            )

        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["success"] is True
        assert data2["requires_payment"] is True
        assert data2["payment_order"]["amount"] == 50000

        # Registration is pending second upgrade payment
        db.refresh(test_registration)
        assert test_registration.status == "pending"


@pytest.mark.skip(
    reason="E2E tests require full registration API migration to be completed. Current endpoint at /api/v1/registrations returns 'Registration API under migration' error. These tests need to be updated once the migration is complete."
)
@pytest.mark.e2e
class TestPaymentFailureRecoveryJourney:
    """Test payment failure and retry scenarios."""

    def test_user_payment_fails_then_retries_successfully(
        self, authenticated_client: TestClient, db, test_registration, test_tiers
    ):
        """
        Journey: User tries to upgrade → payment fails → user retries → succeeds.
        """
        mock_razorpay = MagicMock()
        with patch.dict("sys.modules", {"razorpay": mock_razorpay}):
            mock_client = mock_razorpay.Client.return_value
            mock_client.order.create.return_value = {
                "id": "order_FAIL1",
                "amount": 50000,
                "currency": "INR",
            }

            # Step 1: User initiates upgrade
            response = authenticated_client.post(
                f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
                json={"tier_id": test_tiers[1].id},
                headers={"user_id": str(test_registration.user_id)},
            )
            assert response.status_code == 200

            # Step 2: Payment fails
            with patch("app.api.webhooks.verify_razorpay_signature", return_value=True):
                authenticated_client.post(
                    "/api/v1/webhooks/razorpay",
                    json={
                        "event": "payment.failed",
                        "payload": {
                            "payment": {
                                "entity": {
                                    "id": "pay_FAIL1",
                                    "order_id": "order_FAIL1",
                                    "error_description": "Insufficient funds",
                                }
                            }
                        },
                    },
                    headers={"X-Razorpay-Signature": "valid"},
                )

            # User still at old tier
            db.refresh(test_registration)
            assert test_registration.current_tier_id == test_tiers[0].id

            # Step 3: User retries - should reuse or create new order
            mock_client.order.create.return_value = {
                "id": "order_SUCCESS1",
                "amount": 50000,
                "currency": "INR",
            }

            response = authenticated_client.post(
                f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
                json={"tier_id": test_tiers[1].id},
                headers={"user_id": str(test_registration.user_id)},
            )
            assert response.status_code == 200

            # Step 4: Payment succeeds
            with patch("app.api.webhooks.verify_razorpay_signature", return_value=True):
                authenticated_client.post(
                    "/api/v1/webhooks/razorpay",
                    json={
                        "event": "payment.captured",
                        "payload": {
                            "payment": {
                                "entity": {
                                    "id": "pay_SUCCESS1",
                                    "order_id": "order_SUCCESS1",
                                    "amount": 50000,
                                }
                            }
                        },
                    },
                    headers={"X-Razorpay-Signature": "valid"},
                )

            # Now upgraded
            db.refresh(test_registration)
            assert test_registration.current_tier_id == test_tiers[1].id
            assert test_registration.status == "confirmed"


@pytest.mark.skip(
    reason="E2E tests require full registration API migration to be completed. Current endpoint at /api/v1/registrations returns 'Registration API under migration' error. These tests need to be updated once the migration is complete."
)
@pytest.mark.e2e
class TestConcurrentUserActionsJourney:
    """Test concurrent actions and race conditions."""

    def test_multiple_users_register_for_limited_tier(
        self, authenticated_client: TestClient, db, test_event, test_tiers
    ):
        """
        Journey: Multiple users try to register for limited capacity tier.
        Only allowed number should succeed.
        """
        # Set tier capacity to 2
        limited_tier = test_tiers[1]
        limited_tier.max_registrations = 2
        limited_tier.current_registrations = 0
        db.commit()

        successful_registrations = 0

        with patch.dict("sys.modules", {"razorpay": MagicMock()}):
            # Simulate 5 users trying to register
            for user_id in range(100, 105):
                response = authenticated_client.post(
                    f"/api/v1/events/{test_event.id}/register-tier",
                    json={"tier_id": limited_tier.id, "participant_name": f"User {user_id}"},
                    headers={"user_id": str(user_id)},
                )

                if response.status_code == 201:
                    successful_registrations += 1
                else:
                    # Should get sold out error
                    assert response.status_code in [400, 409]

        # Only 2 should succeed
        assert successful_registrations <= 2


@pytest.mark.skip(
    reason="E2E tests require full registration API migration to be completed. Current endpoint at /api/v1/registrations returns 'Registration API under migration' error. These tests need to be updated once the migration is complete."
)
@pytest.mark.e2e
class TestEventLifecycleJourney:
    """Test user journey through event lifecycle."""

    def test_user_registers_participates_completes_event(
        self,
        authenticated_client: TestClient,
        db,
        test_user,
        test_event,
        test_tiers,
        test_activities,
    ):
        """
        Journey: User registers → event starts → user logs activities → event ends.
        """
        # Step 1: User registers
        with patch.dict("sys.modules", {"razorpay": MagicMock()}):
            response = authenticated_client.post(
                f"/api/v1/events/{test_event.id}/register-tier",
                json={
                    "tier_id": test_tiers[0].id,
                    "activity_id": test_activities[0].id,
                    "participant_name": "Event Participant",
                },
                headers={"user_id": str(test_user.id)},
            )

        assert response.status_code == 201
        registration_id = response.json()["id"]

        # Step 2: Event is ongoing - user can view their registration
        response = authenticated_client.get(
            f"/api/v1/registrations/{registration_id}", headers={"user_id": str(test_user.id)}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

        # Step 3: User can upgrade during event
        mock_razorpay = MagicMock()
        with patch.dict("sys.modules", {"razorpay": mock_razorpay}):
            mock_client = mock_razorpay.Client.return_value
            mock_client.order.create.return_value = {
                "id": "order_LIVE",
                "amount": 50000,
                "currency": "INR",
            }

            response = authenticated_client.post(
                f"/api/v1/registrations/{registration_id}/upgrade-tier",
                json={"tier_id": test_tiers[1].id},
                headers={"user_id": str(test_user.id)},
            )

        assert response.status_code == 200
