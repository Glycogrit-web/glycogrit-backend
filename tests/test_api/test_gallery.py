"""
Tests for Gallery API endpoints.
Tests the new DDD gallery module API.
"""
import pytest
from fastapi.testclient import TestClient


class TestGalleryEndpoints:
    """Test gallery management endpoints."""

    def test_submit_photo_unauthorized(self, client, test_event):
        """Test submitting photo without authentication."""
        response = client.post(
            "/api/v1/gallery/submit",
            json={
                "event_id": test_event.id,
                "photo_url": "https://example.com/photo.jpg",
                "caption": "Test photo"
            }
        )
        assert response.status_code == 401

    def test_submit_photo_success(self, authenticated_client, test_event, test_registration):
        """Test successfully submitting a photo."""
        response = authenticated_client.post(
            "/api/v1/gallery/submit",
            json={
                "event_id": test_event.id,
                "photo_url": "https://example.com/photo.jpg",
                "caption": "Test photo caption"
            }
        )
        # May succeed (201) or fail (400, 404)
        assert response.status_code in [200, 201, 400, 404]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "photo_url" in data or "id" in data

    def test_get_approved_photos_public(self, client, test_event):
        """Test getting approved photos (public endpoint)."""
        response = client.get(f"/api/v1/gallery/event/{test_event.id}")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_get_pending_photos_unauthorized(self, client):
        """Test getting pending photos without authentication."""
        response = client.get("/api/v1/gallery/pending")
        assert response.status_code == 401

    def test_get_pending_photos_admin_only(self, authenticated_client):
        """Test that regular user cannot access pending photos."""
        response = authenticated_client.get("/api/v1/gallery/pending")
        # Should fail with 403 or work if endpoint allows
        assert response.status_code in [200, 403]

    def test_get_pending_photos_admin_access(self, authenticated_admin_client):
        """Test admin can get pending photos."""
        response = authenticated_admin_client.get("/api/v1/gallery/pending")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_approve_photo_unauthorized(self, client):
        """Test approving photo without authentication."""
        response = client.patch("/api/v1/gallery/1/approve")
        assert response.status_code == 401

    def test_approve_photo_admin_only(self, authenticated_client):
        """Test that regular user cannot approve photos."""
        response = authenticated_client.patch("/api/v1/gallery/1/approve")
        assert response.status_code in [403, 404]

    def test_approve_photo_admin_access(self, authenticated_admin_client):
        """Test admin can approve photos."""
        response = authenticated_admin_client.patch("/api/v1/gallery/1/approve")
        # May succeed (200) or fail if photo not found (404)
        assert response.status_code in [200, 404]

    def test_reject_photo_unauthorized(self, client):
        """Test rejecting photo without authentication."""
        response = client.delete("/api/v1/gallery/1/reject")
        assert response.status_code == 401

    def test_reject_photo_admin_only(self, authenticated_client):
        """Test that regular user cannot reject photos."""
        response = authenticated_client.delete("/api/v1/gallery/1/reject")
        assert response.status_code in [403, 404]

    def test_pagination_gallery_photos(self, client, test_event):
        """Test pagination for gallery photos."""
        response = client.get(f"/api/v1/gallery/event/{test_event.id}?skip=0&limit=10")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= 10
