"""
Tests for Users API endpoints.
Tests the new DDD user module API.
"""

import pytest
from fastapi.testclient import TestClient


class TestUsersEndpoints:
    """Test user management endpoints."""

    def test_get_current_user(self, authenticated_client, test_user):
        """Test get current user endpoint."""
        response = authenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["first_name"] == test_user.first_name
        assert data["last_name"] == test_user.last_name
        assert data["is_active"] == test_user.is_active

    def test_get_current_user_unauthorized(self, client):
        """Test get current user without authentication."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_update_current_user(self, authenticated_client, test_user):
        """Test update current user endpoint."""
        response = authenticated_client.put(
            f"/api/v1/users/{test_user.id}", json={"first_name": "Updated", "last_name": "Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["email"] == test_user.email  # Email shouldn't change


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
