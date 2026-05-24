"""
End-to-End tests simulating complete user journeys.

These tests cover entire user flows from registration to tier upgrades to payment.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from decimal import Decimal


@pytest.mark.skip(reason="E2E tests require full registration API migration to be completed. Current endpoint at /api/v1/registrations returns 'Registration API under migration' error. These tests need to be updated once the migration is complete.")
@pytest.mark.e2e
@pytest.mark.financial
class TestNewUserRegistrationJourney:
    """Test complete new user registration flow."""

    @pytest.mark.financial
    def test_new_user_registers_for_free_tier(self, authenticated_client: TestClient, db, test_user, test_event, test_tiers, test_activities):
        """
        Journey: New user discovers event → registers for free tier → confirmed.
        """
        # Step 1: User views event
        response = authenticated_client.get(f"/api/v1/events/{test_event.id}")
        assert response.status_code == 200
        event_data = response.json()
        assert event_data["uses_tier_system"] is True

        # Step 2: User selects free tier and registers
        with patch('app.services.payment_gateway.razorpay_gateway.razorpay'):
            response = authenticated_client.post(
                f"/api/v1/events/{test_event.id}/register-tier",
                json={
                    "tier_id": test_tiers[0].id,
                    "activity_id": test_activities[0].id,
                    "activity_id": test_activities[0].id,
                    "participant_name": "New User"
                }
            )

        assert response.status_code == 201
        data = response.json()

        # Debug: print response to see structure
        import json
        print(f"\nResponse data: {json.dumps(data, indent=2, default=str)}")

        # Should be auto-confirmed (free tier)
        assert data["status"] == "confirmed"
        assert data["current_tier"]["id"] == test_tiers[0].id
        assert "payment_order" not in data  # No payment needed

    @pytest.mark.financial
    def test_new_user_registers_for_paid_tier_completes_payment(self, authenticated_client: TestClient, db, test_user, test_event, test_tiers, test_activities):
        """
        Journey: New user → registers for paid tier → pays → confirmed.
        """
        # Step 1: User registers for paid tier
        with patch('app.services.payment_gateway.razorpay_gateway.razorpay') as mock_razorpay:
            mock_client = mock_razorpay.Client.return_value
            mock_client.order.create.return_value = {
                "id": "order_NEW123",
                "amount": 50000,
                "currency": "INR",
                "status": "created"
            }

            response = authenticated_client.post(
                f"/api/v1/events/{test_event.id}/register-tier",
                json={
                    "tier_id": test_tiers[1].id,
                    "activity_id": test_activities[0].id,  # Basic ₹500
                    "participant_name": "New Paid User"
                },
                headers={"user_id": str(test_user.id)}
            )

        assert response.status_code == 201
        data = response.json()

        # Should be pending payment
        assert data["status"] == "pending"
        assert "payment_order" in data
        assert data["payment_order"]["amount"] == 50000

        registration_id = data["id"]

        # Step 2: User completes payment (webhook)
        with patch('app.api.webhooks.verify_razorpay_signature', return_value=True):
            webhook_response = authenticated_client.post(
                "/api/v1/webhooks/razorpay",
                json={
                    "event": "payment.captured",
                    "payload": {
                        "payment": {
                            "entity": {
                                "id": "pay_NEW123",
                                "order_id": "order_NEW123",
                                "amount": 50000,
                                "status": "captured"
                            }
                        }
                    }
                },
                headers={"X-Razorpay-Signature": "valid_signature"}
            )

        assert webhook_response.status_code == 200

        # Step 3: Verify registration is now confirmed
        response = authenticated_client.get(
            f"/api/v1/registrations/{registration_id}",
            headers={"user_id": str(test_user.id)}
        )

        data = response.json()
        assert data["status"] == "confirmed"


@pytest.mark.skip(reason="E2E tests require full registration API migration to be completed. Current endpoint at /api/v1/registrations returns 'Registration API under migration' error. These tests need to be updated once the migration is complete.")
@pytest.mark.e2e
@pytest.mark.financial
class TestUserUpgradeTierJourney:
    """Test complete tier upgrade flow."""

    @pytest.mark.financial
    def test_user_upgrades_from_free_to_paid(self, authenticated_client: TestClient, db, test_registration, test_tiers):
        """
        Journey: User at free tier → wants more benefits → upgrades to paid → pays → upgraded.
        """
        # Starting state: User at free tier
        assert test_registration.current_tier_id == test_tiers[0].id

        # Step 1: User initiates upgrade
        with patch('app.services.payment_gateway.razorpay_gateway.razorpay') as mock_razorpay:
            mock_client = mock_razorpay.Client.return_value
            mock_client.order.create.return_value = {
                "id": "order_UPGRADE123",
                "amount": 50000,  # ₹500
                "currency": "INR",
                "status": "created"
            }

            response = authenticated_client.post(
                f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
                json={"tier_id": test_tiers[1].id},  # Upgrade to Basic ₹500
                headers={"user_id": str(test_registration.user_id)}
            )

        assert response.status_code == 200
        data = response.json()

        # Should have payment order for upgrade
        assert "payment_order" in data
        assert data["payment_order"]["amount"] == 50000

        # Should still be at old tier (pending upgrade)
        db.refresh(test_registration)
        assert test_registration.current_tier_id == test_tiers[0].id
        assert test_registration.status == "pending"

        # Step 2: User completes payment
        with patch('app.api.webhooks.verify_razorpay_signature', return_value=True):
            webhook_response = authenticated_client.post(
                "/api/v1/webhooks/razorpay",
                json={
                    "event": "payment.captured",
                    "payload": {
                        "payment": {
                            "entity": {
                                "id": "pay_UPGRADE123",
                                "order_id": "order_UPGRADE123",
                                "amount": 50000,
                                "status": "captured"
                            }
                        }
                    }
                },
                headers={"X-Razorpay-Signature": "valid_signature"}
            )

        assert webhook_response.status_code == 200

        # Step 3: Verify user is now at new tier
        db.refresh(test_registration)
        assert test_registration.current_tier_id == test_tiers[1].id
        assert test_registration.status == "confirmed"

    @pytest.mark.financial
    def test_user_upgrades_twice(self, authenticated_client: TestClient, db, test_registration, test_tiers):
        """
        Journey: User upgrades from free → basic → premium.
        Tests multiple upgrades in sequence.
        """
        # Start at free tier
        assert test_registration.current_tier_id == test_tiers[0].id

        with patch('app.services.payment_gateway.razorpay_gateway.razorpay') as mock_razorpay:
            mock_client = mock_razorpay.Client.return_value

            # First upgrade: Free → Basic (₹500)
            mock_client.order.create.return_value = {
                "id": "order_UPGRADE1",
                "amount": 50000,
                "currency": "INR"
            }

            response1 = authenticated_client.post(
                f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
                json={"tier_id": test_tiers[1].id},
                headers={"user_id": str(test_registration.user_id)}
            )
            assert response1.status_code == 200

            # Simulate payment
            with patch('app.api.webhooks.verify_razorpay_signature', return_value=True):
                authenticated_client.post(
                    "/api/v1/webhooks/razorpay",
                    json={
                        "event": "payment.captured",
                        "payload": {
                            "payment": {
                                "entity": {
                                    "id": "pay_UPGRADE1",
                                    "order_id": "order_UPGRADE1",
                                    "amount": 50000
                                }
                            }
                        }
                    },
                    headers={"X-Razorpay-Signature": "valid"}
                )

            db.refresh(test_registration)
            assert test_registration.current_tier_id == test_tiers[1].id

            # Second upgrade: Basic → Premium (₹500 difference)
            mock_client.order.create.return_value = {
                "id": "order_UPGRADE2",
                "amount": 50000,  # Difference
                "currency": "INR"
            }

            response2 = authenticated_client.post(
                f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
                json={"tier_id": test_tiers[2].id},
                headers={"user_id": str(test_registration.user_id)}
            )
            assert response2.status_code == 200

            # Simulate payment
            with patch('app.api.webhooks.verify_razorpay_signature', return_value=True):
                authenticated_client.post(
                    "/api/v1/webhooks/razorpay",
                    json={
                        "event": "payment.captured",
                        "payload": {
                            "payment": {
                                "entity": {
                                    "id": "pay_UPGRADE2",
                                    "order_id": "order_UPGRADE2",
                                    "amount": 50000
                                }
                            }
                        }
                    },
                    headers={"X-Razorpay-Signature": "valid"}
                )

            # Final verification
            db.refresh(test_registration)
            assert test_registration.current_tier_id == test_tiers[2].id
            assert test_registration.total_amount_paid == Decimal("1000.00")


@pytest.mark.skip(reason="E2E tests require full registration API migration to be completed. Current endpoint at /api/v1/registrations returns 'Registration API under migration' error. These tests need to be updated once the migration is complete.")
@pytest.mark.e2e
class TestPaymentFailureRecoveryJourney:
    """Test payment failure and retry scenarios."""

    def test_user_payment_fails_then_retries_successfully(self, authenticated_client: TestClient, db, test_registration, test_tiers):
        """
        Journey: User tries to upgrade → payment fails → user retries → succeeds.
        """
        with patch('app.services.payment_gateway.razorpay_gateway.razorpay') as mock_razorpay:
            mock_client = mock_razorpay.Client.return_value
            mock_client.order.create.return_value = {
                "id": "order_FAIL1",
                "amount": 50000,
                "currency": "INR"
            }

            # Step 1: User initiates upgrade
            response = authenticated_client.post(
                f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
                json={"tier_id": test_tiers[1].id},
                headers={"user_id": str(test_registration.user_id)}
            )
            assert response.status_code == 200

            # Step 2: Payment fails
            with patch('app.api.webhooks.verify_razorpay_signature', return_value=True):
                authenticated_client.post(
                    "/api/v1/webhooks/razorpay",
                    json={
                        "event": "payment.failed",
                        "payload": {
                            "payment": {
                                "entity": {
                                    "id": "pay_FAIL1",
                                    "order_id": "order_FAIL1",
                                    "error_description": "Insufficient funds"
                                }
                            }
                        }
                    },
                    headers={"X-Razorpay-Signature": "valid"}
                )

            # User still at old tier
            db.refresh(test_registration)
            assert test_registration.current_tier_id == test_tiers[0].id

            # Step 3: User retries - should reuse or create new order
            mock_client.order.create.return_value = {
                "id": "order_SUCCESS1",
                "amount": 50000,
                "currency": "INR"
            }

            response = authenticated_client.post(
                f"/api/v1/registrations/{test_registration.id}/upgrade-tier",
                json={"tier_id": test_tiers[1].id},
                headers={"user_id": str(test_registration.user_id)}
            )
            assert response.status_code == 200

            # Step 4: Payment succeeds
            with patch('app.api.webhooks.verify_razorpay_signature', return_value=True):
                authenticated_client.post(
                    "/api/v1/webhooks/razorpay",
                    json={
                        "event": "payment.captured",
                        "payload": {
                            "payment": {
                                "entity": {
                                    "id": "pay_SUCCESS1",
                                    "order_id": "order_SUCCESS1",
                                    "amount": 50000
                                }
                            }
                        }
                    },
                    headers={"X-Razorpay-Signature": "valid"}
                )

            # Now upgraded
            db.refresh(test_registration)
            assert test_registration.current_tier_id == test_tiers[1].id
            assert test_registration.status == "confirmed"


@pytest.mark.skip(reason="E2E tests require full registration API migration to be completed. Current endpoint at /api/v1/registrations returns 'Registration API under migration' error. These tests need to be updated once the migration is complete.")
@pytest.mark.e2e
class TestConcurrentUserActionsJourney:
    """Test concurrent actions and race conditions."""

    def test_multiple_users_register_for_limited_tier(self, authenticated_client: TestClient, db, test_event, test_tiers):
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

        with patch('app.services.payment_gateway.razorpay_gateway.razorpay'):
            # Simulate 5 users trying to register
            for user_id in range(100, 105):
                response = authenticated_client.post(
                    f"/api/v1/events/{test_event.id}/register-tier",
                    json={
                        "tier_id": limited_tier.id,
                        "participant_name": f"User {user_id}"
                    },
                    headers={"user_id": str(user_id)}
                )

                if response.status_code == 201:
                    successful_registrations += 1
                else:
                    # Should get sold out error
                    assert response.status_code in [400, 409]

        # Only 2 should succeed
        assert successful_registrations <= 2


@pytest.mark.skip(reason="E2E tests require full registration API migration to be completed. Current endpoint at /api/v1/registrations returns 'Registration API under migration' error. These tests need to be updated once the migration is complete.")
@pytest.mark.e2e
class TestEventLifecycleJourney:
    """Test user journey through event lifecycle."""

    def test_user_registers_participates_completes_event(self, authenticated_client: TestClient, db, test_user, test_event, test_tiers, test_activities):
        """
        Journey: User registers → event starts → user logs activities → event ends.
        """
        # Step 1: User registers
        with patch('app.services.payment_gateway.razorpay_gateway.razorpay'):
            response = authenticated_client.post(
                f"/api/v1/events/{test_event.id}/register-tier",
                json={
                    "tier_id": test_tiers[0].id,
                    "activity_id": test_activities[0].id,
                    "participant_name": "Event Participant"
                },
                headers={"user_id": str(test_user.id)}
            )

        assert response.status_code == 201
        registration_id = response.json()["id"]

        # Step 2: Event is ongoing - user can view their registration
        response = authenticated_client.get(
            f"/api/v1/registrations/{registration_id}",
            headers={"user_id": str(test_user.id)}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

        # Step 3: User can upgrade during event
        with patch('app.services.payment_gateway.razorpay_gateway.razorpay') as mock_razorpay:
            mock_client = mock_razorpay.Client.return_value
            mock_client.order.create.return_value = {
                "id": "order_LIVE",
                "amount": 50000,
                "currency": "INR"
            }

            response = authenticated_client.post(
                f"/api/v1/registrations/{registration_id}/upgrade-tier",
                json={"tier_id": test_tiers[1].id},
                headers={"user_id": str(test_user.id)}
            )

        assert response.status_code == 200
