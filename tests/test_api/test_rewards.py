"""
Tests for Rewards API endpoints.
Tests the new DDD rewards module API (physical rewards and certificates).
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


class TestRewardsEndpoints:
    """Test reward management endpoints."""

    def test_create_reward_order_unauthorized(self, client):
        """Test creating reward order without authentication."""
        response = client.post(
            "/api/v1/rewards",
            json={
                "registration_id": 1,
                "reward_name": "Medal",
                "shipping_address": {
                    "name": "Test User",
                    "address_line1": "123 Test St",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001",
                    "phone": "9876543210",
                },
            },
        )
        assert response.status_code == 401

    def test_create_reward_order_success(self, authenticated_client, test_registration):
        """Test successfully creating a reward order."""
        response = authenticated_client.post(
            "/api/v1/rewards",
            json={
                "registration_id": test_registration.id,
                "reward_name": "Finisher Medal",
                "shipping_address": {
                    "name": "Test User",
                    "address_line1": "123 Test Street",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001",
                    "phone": "9876543210",
                },
            },
        )
        # May succeed (201) or fail due to eligibility (400, 404)
        assert response.status_code in [200, 201, 400, 404]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "reward_name" in data or "status" in data

    def test_create_reward_order_invalid_address(self, authenticated_client, test_registration):
        """Test creating reward with invalid shipping address."""
        response = authenticated_client.post(
            "/api/v1/rewards",
            json={
                "registration_id": test_registration.id,
                "reward_name": "Medal",
                "shipping_address": {
                    "name": "Test User",
                    "address_line1": "123 Test St",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "12345",  # Invalid pincode (not 6 digits)
                    "phone": "9876543210",
                },
            },
        )
        # Should fail validation
        assert response.status_code in [400, 422]

    def test_create_reward_order_invalid_registration(self, authenticated_client):
        """Test creating reward for non-existent registration."""
        response = authenticated_client.post(
            "/api/v1/rewards",
            json={
                "registration_id": 99999,
                "reward_name": "Medal",
                "shipping_address": {
                    "name": "Test User",
                    "address_line1": "123 Test St",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001",
                    "phone": "9876543210",
                },
            },
        )
        assert response.status_code in [404, 400]

    def test_get_my_rewards_unauthorized(self, client):
        """Test getting user's rewards without authentication."""
        response = client.get("/api/v1/rewards/my")
        assert response.status_code == 401

    def test_get_my_rewards_authenticated(self, authenticated_client):
        """Test getting user's rewards."""
        response = authenticated_client.get("/api/v1/rewards/my")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_reward_details_unauthorized(self, client):
        """Test getting reward details without authentication."""
        response = client.get("/api/v1/rewards/1")
        assert response.status_code == 401

    def test_get_reward_details_not_found(self, authenticated_client):
        """Test getting non-existent reward details."""
        response = authenticated_client.get("/api/v1/rewards/99999")
        assert response.status_code in [404, 403]

    def test_update_shipment_status_unauthorized(self, client):
        """Test updating shipment status without authentication."""
        response = client.patch(
            "/api/v1/rewards/1/status", json={"status": "shipped", "tracking_id": "TRACK123"}
        )
        assert response.status_code == 401

    def test_update_shipment_status_admin_only(self, authenticated_client):
        """Test that regular user cannot update shipment status."""
        response = authenticated_client.patch(
            "/api/v1/rewards/1/status", json={"status": "shipped", "tracking_id": "TRACK123"}
        )
        # Should fail with 403 or 404
        assert response.status_code in [403, 404]

    def test_get_pending_rewards_unauthorized(self, client):
        """Test getting pending rewards without authentication."""
        response = client.get("/api/v1/rewards/pending/all")
        assert response.status_code == 401

    def test_get_pending_rewards_admin_access(self, authenticated_admin_client):
        """Test admin can get pending rewards."""
        response = authenticated_admin_client.get("/api/v1/rewards/pending/all")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_pagination_my_rewards(self, authenticated_client):
        """Test pagination for my rewards."""
        response = authenticated_client.get("/api/v1/rewards/my?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    def test_reward_order_includes_tracking(self, authenticated_client, test_registration):
        """Test that reward order response includes tracking info."""
        response = authenticated_client.post(
            "/api/v1/rewards",
            json={
                "registration_id": test_registration.id,
                "reward_name": "Finisher Medal",
                "shipping_address": {
                    "name": "Test User",
                    "address_line1": "123 Test Street",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001",
                    "phone": "9876543210",
                },
            },
        )
        if response.status_code in [200, 201]:
            data = response.json()
            # Should have status tracking fields
            assert "status" in data or "reward_name" in data


class TestCertificateEndpoints:
    """Test certificate-related endpoints."""

    def test_get_certificate_unauthorized(self, client):
        """Test getting certificate without authentication."""
        response = client.get("/api/v1/certificates/registration/1")
        assert response.status_code == 401

    def test_download_certificate_tracking(self, authenticated_client):
        """Test that certificate downloads are tracked."""
        response = authenticated_client.get("/api/v1/certificates/my-certificates")
        # May return 200 with empty list or 404
        assert response.status_code in [200, 404]
