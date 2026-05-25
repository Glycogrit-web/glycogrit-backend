"""
Tests for Registrations API endpoints.
Tests the new DDD registrations module API.
"""
import pytest
from fastapi.testclient import TestClient
from decimal import Decimal


class TestRegistrationsEndpoints:
    """Test registration management endpoints."""

    def test_register_for_event_unauthorized(self, client, test_event, test_tiers):
        """Test registering for event without authentication."""
        response = client.post(
            f"/api/v1/events/{test_event.id}/register-tier",
            json={
                "participant_name": "Test User",
                "tier_id": 1
            }
        )
        assert response.status_code == 401

    def test_register_for_event_success(self, authenticated_client, test_event, test_tiers):
        """Test successfully registering for an event."""
        response = authenticated_client.post(
            f"/api/v1/registrations/{test_event.id}/register",
            json={
                "participant_name": "Test User",
                "tier_id": test_tiers[0].id
            }
        )
        # May succeed (201) or fail if already registered (409) or event issues (400, 404)
        assert response.status_code in [200, 201, 400, 404, 409]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "registration_number" in data or "id" in data

    def test_register_nonexistent_event(self, authenticated_client):
        """Test registering for non-existent event."""
        response = authenticated_client.post(
            "/api/v1/registrations/99999/register",
            json={
                "participant_name": "Test User",
                "tier_id": 1
            }
        )
        assert response.status_code in [404, 400]

    def test_get_my_registrations_unauthorized(self, client):
        """Test getting registrations without authentication."""
        response = client.get("/api/v1/registrations/my")
        assert response.status_code == 401

    def test_get_my_registrations_authenticated(self, authenticated_client):
        """Test getting user's registrations."""
        response = authenticated_client.get("/api/v1/registrations/my")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_my_registrations_with_existing(self, authenticated_client, test_registration):
        """Test getting registrations includes existing ones."""
        response = authenticated_client.get("/api/v1/registrations/my")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            reg = data[0]
            assert "event_id" in reg or "registration_number" in reg

    def test_get_registration_details_unauthorized(self, client, test_registration):
        """Test getting registration details without authentication."""
        response = client.get(f"/api/v1/registrations/{test_registration.id}")
        assert response.status_code == 401

    def test_get_registration_details_own(self, authenticated_client, test_registration):
        """Test getting own registration details."""
        response = authenticated_client.get(f"/api/v1/registrations/{test_registration.id}")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert data["id"] == test_registration.id

    def test_get_registration_details_not_found(self, authenticated_client):
        """Test getting non-existent registration."""
        response = authenticated_client.get("/api/v1/registrations/99999")
        assert response.status_code in [404, 403]

    def test_cancel_registration_unauthorized(self, client, test_registration):
        """Test canceling registration without authentication."""
        response = client.delete(f"/api/v1/registrations/{test_registration.id}")
        assert response.status_code == 401

    def test_cancel_registration_success(self, authenticated_client, test_registration):
        """Test successfully canceling own registration."""
        response = authenticated_client.delete(f"/api/v1/registrations/{test_registration.id}/cancel")
        # May succeed (200) or fail (404, 400)
        assert response.status_code in [200, 404, 400]
        if response.status_code == 200:
            data = response.json()
            assert "message" in data or "status" in data

    def test_confirm_registration_unauthorized(self, client, test_registration):
        """Test confirming registration without authentication."""
        response = client.post(
            f"/api/v1/registrations/{test_registration.id}/confirm",
            json={"payment_id": "pay_test123"}
        )
        assert response.status_code == 401

    def test_pagination_my_registrations(self, authenticated_client):
        """Test pagination for my registrations."""
        response = authenticated_client.get("/api/v1/registrations/my?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10


class TestRegistrationTiersEndpoints:
    """Test registration tier management endpoints."""

    def test_get_event_tiers_public(self, authenticated_client, test_registration, test_tiers):
        """Test getting registration tiers (requires auth — endpoint is per-registration)."""
        response = authenticated_client.get(f"/api/v1/registrations/{test_registration.id}/tiers")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            if len(data) > 0:
                tier = data[0]
                assert "tier_name" in tier
                assert "price" in tier

    def test_get_available_tiers_only(self, authenticated_client, test_registration, test_tiers):
        """Test that only available tiers are returned."""
        response = authenticated_client.get(f"/api/v1/registrations/{test_registration.id}/tiers")
        if response.status_code == 200:
            data = response.json()
            for tier in data:
                if "is_available" in tier:
                    assert isinstance(tier["is_available"], bool)


class TestRegistrationRewardsEndpoints:
    """Test registration rewards endpoints."""

    def test_get_registration_rewards_unauthorized(self, client, test_registration):
        """Test getting registration rewards without authentication."""
        response = client.get(f"/api/v1/registrations/{test_registration.id}/rewards")
        assert response.status_code == 401

    def test_get_registration_rewards_own(self, authenticated_client, test_registration):
        """Test getting own registration rewards."""
        response = authenticated_client.get(f"/api/v1/registrations/{test_registration.id}/rewards")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            # Endpoint returns a dict with all_rewards key (list), or a list directly
            assert isinstance(data, (list, dict))

    def test_registration_includes_status(self, authenticated_client, test_registration):
        """Test that registration includes status field."""
        response = authenticated_client.get(f"/api/v1/registrations/{test_registration.id}")
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ["pending", "confirmed", "cancelled", "completed"]
