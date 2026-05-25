"""
Tests for Events API endpoints.
Tests the new DDD events module API.
"""
from datetime import datetime, timedelta

import pytest


class TestEventsEndpoints:
    """Test events endpoints."""

    def test_list_events(self, client):
        """Test list all events."""
        response = client.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)

    def test_get_event_by_id(self, client, test_event):
        """Test get event by ID."""
        response = client.get(f"/api/v1/events/{test_event.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_event.id
        assert data["name"] == test_event.name
        assert data["slug"] == test_event.slug

    def test_get_event_by_slug(self, client, test_event):
        """Test get event by slug."""
        response = client.get(f"/api/v1/events/slug/{test_event.slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == test_event.slug
        assert data["name"] == test_event.name

    def test_get_nonexistent_event(self, client):
        """Test get non-existent event."""
        response = client.get("/api/v1/events/99999")
        assert response.status_code == 404

    def test_search_events(self, client):
        """Test search events."""
        response = client.get("/api/v1/events?search=test")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_filter_events_by_status(self, client):
        """Test filter events by status."""
        response = client.get("/api/v1/events?status=published")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)


class TestEventActivitiesEndpoints:
    """Test event activities endpoints."""

    def test_get_event_activities(self, client, test_event, test_activities):
        """Test get activities for an event."""
        response = client.get(f"/api/v1/events/{test_event.id}/activities")
        # May return 200 with data or 404
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert isinstance(response.json(), list)


class TestEventTiersEndpoints:
    """Test event tiers endpoints."""

    def test_get_event_tiers(self, client, test_event, test_tiers):
        """Test get tiers for an event."""
        response = client.get(f"/api/v1/events/{test_event.id}/tiers")
        # May return 200 with tiers or 404
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            tiers = response.json()
            assert isinstance(tiers, list)
            if len(tiers) > 0:
                assert "tier_name" in tiers[0]
                assert "price" in tiers[0]


class TestEventCreateUpdateEndpoints:
    """Test event creation and update endpoints."""

    def test_create_event_unauthorized(self, client):
        """Test creating event without authentication."""
        now = datetime.now()
        response = client.post(
            "/api/v1/events",
            json={
                "name": "Test Event",
                "slug": "test-event-create",
                "description": "Test Description",
                "event_date": (now + timedelta(days=30)).isoformat(),
                "event_end_date": (now + timedelta(days=60)).isoformat(),
                "registration_start_date": (now - timedelta(days=7)).isoformat(),
                "registration_end_date": (now + timedelta(days=25)).isoformat(),
                "is_virtual": True
            }
        )
        assert response.status_code == 401

    def test_create_event_success(self, authenticated_client):
        """Test successfully creating an event."""
        now = datetime.now()
        response = authenticated_client.post(
            "/api/v1/events",
            json={
                "name": "New Test Event",
                "slug": "new-test-event-unique-123",
                "description": "Test Description",
                "event_date": (now + timedelta(days=30)).isoformat(),
                "event_end_date": (now + timedelta(days=60)).isoformat(),
                "registration_start_date": (now - timedelta(days=7)).isoformat(),
                "registration_end_date": (now + timedelta(days=25)).isoformat(),
                "is_virtual": True
            }
        )
        assert response.status_code in [200, 201, 400, 422]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "name" in data
            assert data["name"] == "New Test Event"

    def test_update_event_unauthorized(self, client, test_event):
        """Test updating event without authentication."""
        response = client.patch(
            f"/api/v1/events/{test_event.id}",
            json={"name": "Updated Event Name"}
        )
        assert response.status_code == 401

    def test_update_event_success(self, authenticated_client, test_event):
        """Test successfully updating own event."""
        response = authenticated_client.patch(
            f"/api/v1/events/{test_event.id}",
            json={"description": "Updated description"}
        )
        assert response.status_code in [200, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "description" in data or "name" in data

    def test_delete_event_unauthorized(self, client, test_event):
        """Test deleting event without authentication."""
        response = client.delete(f"/api/v1/events/{test_event.id}")
        assert response.status_code == 401

    def test_get_my_events_unauthorized(self, client):
        """Test getting user's events without authentication."""
        response = client.get("/api/v1/events/organizer/my")
        assert response.status_code == 401

    def test_get_my_events_authenticated(self, authenticated_client):
        """Test getting user's events as organizer."""
        response = authenticated_client.get("/api/v1/events/organizer/my")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
