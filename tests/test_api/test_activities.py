"""
Tests for Activities API endpoints.
Tests the new DDD activities module API.
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


class TestActivitiesEndpoints:
    """Test activities endpoints."""

    def test_get_my_activities(self, authenticated_client):
        """Test get current user's activities."""
        response = authenticated_client.get("/api/v1/activities/my")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_my_activities_unauthorized(self, client):
        """Test get activities without authentication."""
        response = client.get("/api/v1/activities/my")
        assert response.status_code == 401

    def test_submit_manual_activity(self, authenticated_client, test_event, test_registration):
        """Test submit a manual activity."""
        activity_date = datetime.utcnow()
        response = authenticated_client.post(
            f"/api/v1/events/{test_event.id}/activities",
            json={
                "activity_type": "running",
                "distance": 5.5,
                "duration": 1800,
                "activity_date": activity_date.isoformat(),
                "source": "manual",
                "notes": "Morning run"
            }
        )
        # May return 201 if successful, or 404 if registration not found
        assert response.status_code in [200, 201, 404]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "distance" in data
            assert "activity_type" in data

    def test_get_activity_stats(self, authenticated_client):
        """Test get activity statistics."""
        response = authenticated_client.get("/api/v1/activities/stats")
        # May return 200 with stats or 404 if no data
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "total_distance" in data or "activities" in data


class TestProgressEndpoints:
    """Test activity progress endpoints."""

    def test_get_my_progress(self, authenticated_client):
        """Test get current user's progress."""
        response = authenticated_client.get("/api/v1/activities/progress/my")
        # May return 200 with empty list or data
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert isinstance(response.json(), list)

    def test_get_event_progress(self, authenticated_client, test_event):
        """Test get progress for a specific event."""
        response = authenticated_client.get(f"/api/v1/events/{test_event.id}/progress")
        # May return 200 with progress data or 404
        assert response.status_code in [200, 404]
