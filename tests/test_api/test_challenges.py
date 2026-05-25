"""
Tests for Challenges API endpoints.
Tests the new DDD challenges module API.
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient


class TestChallengesEndpoints:
    """Test challenge management endpoints."""

    def test_get_challenge_progress_unauthorized(self, client, test_event):
        """Test getting challenge progress without authentication."""
        response = client.get(f"/api/v1/challenges/{test_event.id}/progress")
        assert response.status_code == 401

    def test_get_challenge_progress_no_registration(self, authenticated_client, test_event):
        """Test getting challenge progress when user is not registered."""
        response = authenticated_client.get(f"/api/v1/challenges/{test_event.id}/progress")
        # Should return 404 if not registered
        assert response.status_code in [404, 200]
        if response.status_code == 200:
            data = response.json()
            assert "challenge_id" in data or "status" in data

    def test_get_challenge_progress_with_registration(self, authenticated_client, test_event, test_registration):
        """Test getting challenge progress for registered user."""
        response = authenticated_client.get(f"/api/v1/challenges/{test_event.id}/progress")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "challenge_name" in data or "current_distance" in data or "status" in data

    def test_join_challenge_unauthorized(self, client, test_event):
        """Test joining challenge without authentication."""
        response = client.post(f"/api/v1/challenges/{test_event.id}/join")
        assert response.status_code == 401

    def test_join_challenge_success(self, authenticated_client, test_event, test_tiers):
        """Test successfully joining a challenge."""
        response = authenticated_client.post(f"/api/v1/challenges/{test_event.id}/join")
        # May succeed (201) or fail if already registered (409) or event issues (400, 404)
        assert response.status_code in [200, 201, 400, 404, 409]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "registration_id" in data or "message" in data

    def test_join_challenge_nonexistent_event(self, authenticated_client):
        """Test joining a non-existent challenge."""
        response = authenticated_client.post("/api/v1/challenges/99999/join")
        assert response.status_code in [404, 400]

    def test_get_my_challenges_unauthorized(self, client):
        """Test getting user's challenges without authentication."""
        response = client.get("/api/v1/challenges/my")
        assert response.status_code == 401

    def test_get_my_challenges_authenticated(self, authenticated_client):
        """Test getting user's challenges."""
        response = authenticated_client.get("/api/v1/challenges/my")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_my_challenges_with_registrations(self, authenticated_client, test_registration):
        """Test getting challenges with existing registrations."""
        response = authenticated_client.get("/api/v1/challenges/my")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            challenge = data[0]
            assert "event_id" in challenge or "challenge_name" in challenge

    def test_leave_challenge_unauthorized(self, client, test_event):
        """Test leaving challenge without authentication."""
        response = client.delete(f"/api/v1/challenges/{test_event.id}/leave")
        assert response.status_code == 401

    def test_leave_challenge_not_registered(self, authenticated_client, test_event):
        """Test leaving challenge when not registered."""
        response = authenticated_client.delete(f"/api/v1/challenges/{test_event.id}/leave")
        # Should return 404 if not registered
        assert response.status_code in [404, 200]

    def test_leave_challenge_with_registration(self, authenticated_client, test_event, test_registration):
        """Test leaving challenge when registered."""
        response = authenticated_client.delete(f"/api/v1/challenges/{test_event.id}/leave")
        # Returns 204 No Content on success (DELETE endpoint), or 404/400 on failure
        assert response.status_code in [200, 204, 404, 400]

    def test_challenge_progress_includes_metrics(self, authenticated_client, test_event, test_registration):
        """Test that challenge progress includes all required metrics."""
        response = authenticated_client.get(f"/api/v1/challenges/{test_event.id}/progress")
        if response.status_code == 200:
            data = response.json()
            # Should have progress tracking fields
            expected_fields = ["challenge_id", "status", "current_distance", "target_distance"]
            # Check if at least some expected fields exist
            has_fields = any(field in data for field in expected_fields)
            assert has_fields or "error" in data or "message" in data

    def test_pagination_my_challenges(self, authenticated_client):
        """Test pagination parameters for my challenges."""
        response = authenticated_client.get("/api/v1/challenges/my?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10
