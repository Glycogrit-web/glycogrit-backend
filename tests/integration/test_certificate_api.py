"""
Integration tests for Certificate API endpoints.

Tests the full API flow including authentication, authorization, and database operations.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.models.user import User
from app.models.registration import Registration
from app.models.user_reward import UserReward


@pytest.mark.integration
@pytest.mark.certificate
class TestCertificatePreviewEndpoint:
    """Test GET /api/v1/certificates/registration/{id} endpoint."""

    def test_preview_requires_authentication(self, client: TestClient, completed_registration: Registration):
        """Test that preview endpoint requires authentication."""
        response = client.get(f"/api/v1/certificates/registration/{completed_registration.id}")

        assert response.status_code == 401

    def test_preview_requires_ownership(self, db: Session, test_event, test_tiers):
        """Test that users can only preview their own certificates."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.core.auth import get_current_active_user

        # Create two users
        user1 = User(email="user1@test.com", first_name="User", last_name="One", is_active=True, email_verified=True)
        user2 = User(email="user2@test.com", first_name="User", last_name="Two", is_active=True, email_verified=True)
        db.add_all([user1, user2])
        db.commit()
        db.refresh(user1)
        db.refresh(user2)

        # Create registration for user1
        registration = Registration(
            user_id=user1.id,
            event_id=test_event.id,
            current_tier_id=test_tiers[0].id,
            registration_number=f"TEST-001",
            participant_name="User One",
            status="confirmed",
            uses_tier_system=True
        )
        db.add(registration)
        db.commit()
        db.refresh(registration)

        # Make activity completed
        from app.models.activity_progress import ActivityProgress
        from datetime import datetime
        progress = ActivityProgress(
            registration_id=registration.id,
            activity_name="Running",
            target_distance=5.0,
            distance_completed=5.5,
            is_completed=True,
            completed_at=datetime.utcnow()
        )
        db.add(progress)
        db.commit()

        # Authenticate as user2 (not owner)
        def override_get_db():
            try:
                yield db
            finally:
                pass

        async def override_get_current_user():
            return user2

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = override_get_current_user

        with TestClient(app) as test_client:
            response = test_client.get(f"/api/v1/certificates/registration/{registration.id}")

        app.dependency_overrides.clear()

        assert response.status_code == 403
        assert "not authorized" in response.json()['detail'].lower()

    @patch('app.services.certificate_service.CertificateService.generate_certificate')
    def test_preview_does_not_track_downloads(
        self,
        mock_generate: MagicMock,
        authenticated_client: TestClient,
        completed_registration: Registration,
        certificate_reward: UserReward,
        db: Session
    ):
        """Test that preview endpoint does not increment download count."""
        mock_generate.return_value = certificate_reward.certificate_url

        initial_count = certificate_reward.download_count

        response = authenticated_client.get(
            f"/api/v1/certificates/registration/{completed_registration.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data['preview_mode'] is True
        assert 'use /download endpoint to track downloads' in data['message']

        # Verify download count unchanged
        db.refresh(certificate_reward)
        assert certificate_reward.download_count == initial_count

    @patch('app.services.certificate_service.CertificateService.generate_certificate')
    def test_preview_shows_download_statistics(
        self,
        mock_generate: MagicMock,
        authenticated_client: TestClient,
        completed_registration: Registration,
        certificate_reward: UserReward
    ):
        """Test that preview shows download statistics."""
        mock_generate.return_value = certificate_reward.certificate_url

        response = authenticated_client.get(
            f"/api/v1/certificates/registration/{completed_registration.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert 'download_count' in data
        assert 'download_limit' in data
        assert 'remaining_downloads' in data
        assert data['download_limit'] == 10


@pytest.mark.integration
@pytest.mark.certificate
class TestCertificateDownloadEndpoint:
    """Test GET /api/v1/certificates/registration/{id}/download endpoint."""

    def test_download_requires_authentication(self, client: TestClient, completed_registration: Registration):
        """Test that download endpoint requires authentication."""
        response = client.get(f"/api/v1/certificates/registration/{completed_registration.id}/download")

        assert response.status_code == 401

    @patch('app.services.certificate_service.CertificateService.track_certificate_download')
    @patch('app.services.certificate_service.CertificateService.generate_certificate')
    def test_download_tracks_count(
        self,
        mock_generate: MagicMock,
        mock_track: MagicMock,
        authenticated_client: TestClient,
        completed_registration: Registration,
        certificate_reward: UserReward
    ):
        """Test that download endpoint tracks download count."""
        mock_generate.return_value = certificate_reward.certificate_url
        mock_track.return_value = {
            'certificate_url': certificate_reward.certificate_url,
            'certificate_number': certificate_reward.certificate_number,
            'download_count': 1,
            'download_limit': 10,
            'remaining_downloads': 9,
            'last_downloaded_at': '2024-05-04T10:00:00'
        }

        response = authenticated_client.get(
            f"/api/v1/certificates/registration/{completed_registration.id}/download"
        )

        assert response.status_code == 200
        data = response.json()
        assert 'downloads remaining' in data['message'].lower()
        assert data['download_count'] == 1
        mock_track.assert_called_once()

    @patch('app.services.certificate_service.CertificateService.track_certificate_download')
    @patch('app.services.certificate_service.CertificateService.generate_certificate')
    def test_download_limit_exceeded_returns_429(
        self,
        mock_generate: MagicMock,
        mock_track: MagicMock,
        authenticated_client: TestClient,
        completed_registration: Registration
    ):
        """Test that exceeding download limit returns HTTP 429."""
        mock_track.side_effect = ValueError("Download limit exceeded. You have already downloaded this certificate 10 times")

        response = authenticated_client.get(
            f"/api/v1/certificates/registration/{completed_registration.id}/download"
        )

        assert response.status_code == 429
        assert 'limit exceeded' in response.json()['detail'].lower()

    @patch('app.services.certificate_service.CertificateService.generate_certificate')
    def test_admin_bypasses_download_limit(
        self,
        mock_generate: MagicMock,
        authenticated_admin_client: TestClient,
        completed_registration: Registration,
        certificate_reward: UserReward
    ):
        """Test that admins bypass download limits."""
        mock_generate.return_value = certificate_reward.certificate_url

        # Set certificate at limit
        certificate_reward.download_count = 10
        certificate_reward.download_limit = 10

        response = authenticated_admin_client.get(
            f"/api/v1/certificates/registration/{completed_registration.id}/download"
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get('admin_download') is True
        assert 'limits not applied' in data['message'].lower()


@pytest.mark.integration
@pytest.mark.certificate
class TestMyCertificatesEndpoint:
    """Test GET /api/v1/certificates/my-certificates endpoint."""

    def test_my_certificates_requires_authentication(self, client: TestClient):
        """Test that my-certificates endpoint requires authentication."""
        response = client.get("/api/v1/certificates/my-certificates")

        assert response.status_code == 401

    def test_my_certificates_returns_list(
        self,
        authenticated_client: TestClient,
        certificate_reward: UserReward
    ):
        """Test that my-certificates returns user's certificates."""
        response = authenticated_client.get("/api/v1/certificates/my-certificates")

        assert response.status_code == 200
        data = response.json()
        assert 'certificates' in data
        assert 'total' in data
        assert data['total'] >= 1
        assert len(data['certificates']) >= 1

        cert = data['certificates'][0]
        assert 'certificate_url' in cert
        assert 'certificate_number' in cert
        assert 'download_count' in cert
        assert 'download_limit' in cert
        assert 'remaining_downloads' in cert

    def test_my_certificates_empty_for_new_user(self, db: Session):
        """Test that new user with no certificates gets empty list."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.core.auth import get_current_active_user

        # Create new user with no certificates
        new_user = User(
            email="newuser@test.com",
            first_name="New",
            last_name="User",
            is_active=True,
            email_verified=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        def override_get_db():
            try:
                yield db
            finally:
                pass

        async def override_get_current_user():
            return new_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = override_get_current_user

        with TestClient(app) as test_client:
            response = test_client.get("/api/v1/certificates/my-certificates")

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 0
        assert len(data['certificates']) == 0


@pytest.mark.integration
@pytest.mark.certificate
class TestAdminDownloadLimitEndpoints:
    """Test admin endpoints for managing download limits."""

    def test_update_limit_requires_admin(
        self,
        authenticated_client: TestClient,
        certificate_reward: UserReward
    ):
        """Test that updating limit requires admin privileges."""
        response = authenticated_client.patch(
            f"/api/v1/certificates/registration/{certificate_reward.registration_id}/download-limit",
            json={"new_limit": 20}
        )

        assert response.status_code == 403
        assert 'admin' in response.json()['detail'].lower()

    def test_update_limit_success(
        self,
        authenticated_admin_client: TestClient,
        certificate_reward: UserReward,
        db: Session
    ):
        """Test successful limit update by admin."""
        response = authenticated_admin_client.patch(
            f"/api/v1/certificates/registration/{certificate_reward.registration_id}/download-limit",
            json={"new_limit": 20}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['old_limit'] == 10
        assert data['new_limit'] == 20
        assert 'updated' in data['message'].lower()

        db.refresh(certificate_reward)
        assert certificate_reward.download_limit == 20

    def test_reset_count_requires_admin(
        self,
        authenticated_client: TestClient,
        certificate_reward: UserReward
    ):
        """Test that resetting count requires admin privileges."""
        response = authenticated_client.post(
            f"/api/v1/certificates/registration/{certificate_reward.registration_id}/reset-downloads"
        )

        assert response.status_code == 403

    def test_reset_count_success(
        self,
        authenticated_admin_client: TestClient,
        certificate_reward: UserReward,
        db: Session
    ):
        """Test successful count reset by admin."""
        # Set some download count
        certificate_reward.download_count = 5
        db.commit()

        response = authenticated_admin_client.post(
            f"/api/v1/certificates/registration/{certificate_reward.registration_id}/reset-downloads"
        )

        assert response.status_code == 200
        data = response.json()
        assert data['old_count'] == 5
        assert data['new_count'] == 0

        db.refresh(certificate_reward)
        assert certificate_reward.download_count == 0
        assert certificate_reward.last_downloaded_at is None

    def test_set_event_default_limit(
        self,
        authenticated_admin_client: TestClient,
        test_event,
        certificate_reward: UserReward,
        db: Session
    ):
        """Test setting event-wide default limit."""
        response = authenticated_admin_client.patch(
            f"/api/v1/certificates/events/{test_event.id}/default-download-limit",
            json={"default_limit": 15, "apply_to_existing": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['default_download_limit'] == 15
        assert data['applied_to_existing'] is True
        assert data['certificates_updated'] >= 1

        db.refresh(certificate_reward)
        assert certificate_reward.download_limit == 15


@pytest.mark.integration
@pytest.mark.certificate
class TestDownloadAnalytics:
    """Test download analytics endpoint."""

    def test_analytics_requires_admin(self, authenticated_client: TestClient):
        """Test that analytics requires admin privileges."""
        response = authenticated_client.get("/api/v1/certificates/download-analytics")

        assert response.status_code == 403

    def test_analytics_returns_data(
        self,
        authenticated_admin_client: TestClient,
        certificate_reward: UserReward
    ):
        """Test that analytics returns correct data structure."""
        response = authenticated_admin_client.get("/api/v1/certificates/download-analytics")

        assert response.status_code == 200
        data = response.json()
        assert 'total_certificates' in data
        assert 'total_downloads' in data
        assert 'average_downloads_per_certificate' in data
        assert 'download_distribution' in data
        assert 'certificates_at_limit' in data
        assert 'limit_exceeded_rate' in data

    def test_analytics_event_filter(
        self,
        authenticated_admin_client: TestClient,
        test_event,
        certificate_reward: UserReward
    ):
        """Test that analytics can be filtered by event."""
        response = authenticated_admin_client.get(
            f"/api/v1/certificates/download-analytics?event_id={test_event.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert 'event_name' in data
        assert data['total_certificates'] >= 1
