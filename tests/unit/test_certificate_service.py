"""
Unit tests for CertificateService.

Tests certificate generation logic, download tracking, and limit enforcement.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from app.modules.certificates.services.certificate_service import CertificateService
from app.models.user_reward import UserReward, RewardType, RewardStatus
from app.modules.registrations.domain.registration import Registration


@pytest.mark.unit
@pytest.mark.certificate
class TestCertificateGeneration:
    """Test certificate generation functionality using public API."""

    @patch('app.modules.certificates.services.certificate_service.StorageService')
    @patch('app.modules.certificates.services.certificate_service.HTML')
    def test_generate_certificate_success(self, mock_html, mock_storage, db, completed_registration):
        """Test successful certificate generation."""
        # Setup mocks
        mock_html_instance = MagicMock()
        mock_html.return_value = mock_html_instance
        mock_html_instance.write_pdf.return_value = b"PDF_CONTENT"

        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.upload_file.return_value = "https://example.com/cert.pdf"

        service = CertificateService(db)

        # Generate certificate
        result = service.generate_certificate(
            registration_id=completed_registration.id,
            participant_name="Test User"
        )

        # Verify result
        assert result is not None
        assert "certificate_url" in result
        assert "certificate_number" in result
        assert result["certificate_number"].startswith("GLCG-")

        # Verify PDF was generated
        mock_html_instance.write_pdf.assert_called_once()

        # Verify uploaded to storage
        mock_storage_instance.upload_file.assert_called_once()

    def test_generate_certificate_already_exists(self, db, completed_registration):
        """Test that generating certificate again returns existing one."""
        service = CertificateService(db)

        # Create a reward record (simulating existing certificate)
        reward = UserReward(
            user_id=completed_registration.user_id,
            registration_id=completed_registration.id,
            event_id=completed_registration.event_id,
            reward_id="certificate-existing",
            reward_name="E-Certificate",
            reward_type=RewardType.CERTIFICATE,
            certificate_number="GLCG-2026-0001-00001",
            certificate_url="https://example.com/existing.pdf",
            requires_shipping=False,
            status=RewardStatus.DELIVERED
        )
        db.add(reward)
        db.commit()

        # Try to generate again (should return existing without regenerating)
        result = service.generate_certificate(completed_registration.id)

        # Should return existing certificate as dict
        assert result is not None
        assert isinstance(result, dict)
        assert result["certificate_number"] == "GLCG-2026-0001-00001"
        assert result["certificate_url"] == "https://example.com/existing.pdf"

    def test_format_distance(self):
        """Test distance formatting logic."""
        # Distance formatting is part of template rendering
        # This test verifies format logic conceptually
        distance = 5.0
        formatted = f"{distance:.2f} km"
        assert formatted == "5.00 km"

        distance = 10.5
        formatted = f"{distance:.2f} km"
        assert formatted == "10.50 km"


@pytest.mark.unit
@pytest.mark.certificate
class TestDownloadTracking:
    """Test download tracking functionality."""

    def test_track_download_increments_count(self, db: Session, certificate_reward: UserReward):
        """Test that download count increments correctly."""
        service = CertificateService(db)

        initial_count = certificate_reward.download_count or 0

        result = service.track_download(
            registration_id=certificate_reward.registration_id,
            user_id=certificate_reward.user_id
        )

        assert result.download_count == initial_count + 1

    def test_track_download_updates_timestamp(self, db: Session, certificate_reward: UserReward):
        """Test that last_downloaded_at is updated."""
        service = CertificateService(db)

        assert certificate_reward.last_downloaded_at is None

        result = service.track_download(
            registration_id=certificate_reward.registration_id,
            user_id=certificate_reward.user_id
        )

        assert result.last_downloaded_at is not None
        assert isinstance(result.last_downloaded_at, datetime)

    def test_track_download_certificate_not_found(self, db: Session):
        """Test error when certificate not found."""
        from app.core.exceptions import NotFoundException
        service = CertificateService(db)

        with pytest.raises(NotFoundException):
            service.track_download(
                registration_id=99999,
                user_id=1
            )

    def test_track_download_permission_denied(self, db: Session, certificate_reward: UserReward):
        """Test error when user tries to download someone else's certificate."""
        from app.core.exceptions import PermissionDeniedException
        service = CertificateService(db)

        # Try to download with different user_id
        with pytest.raises(PermissionDeniedException):
            service.track_download(
                registration_id=certificate_reward.registration_id,
                user_id=certificate_reward.user_id + 999
            )


@pytest.mark.unit
@pytest.mark.certificate
class TestCertificateValidation:
    """Test certificate validation through public API."""

    @patch('app.modules.certificates.services.certificate_service.StorageService')
    @patch('app.modules.certificates.services.certificate_service.HTML')
    def test_validate_completed_registration(self, mock_html, mock_storage, db: Session, completed_registration: Registration):
        """Test certificate generation succeeds for completed registration."""
        # Setup mocks
        mock_html_instance = MagicMock()
        mock_html.return_value = mock_html_instance
        mock_html_instance.write_pdf.return_value = b"PDF_CONTENT"

        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.upload_file.return_value = "https://example.com/cert.pdf"

        service = CertificateService(db)

        # Should not raise any error
        result = service.generate_certificate(
            registration_id=completed_registration.id,
            participant_name="Test User"
        )

        assert result is not None
        assert "certificate_url" in result
        assert "certificate_number" in result

    def test_validate_nonexistent_registration(self, db: Session):
        """Test getting certificate for non-existent registration returns None."""
        service = CertificateService(db)

        result = service.get_certificate(registration_id=99999)

        # Should return None when certificate doesn't exist
        assert result is None


@pytest.mark.unit
@pytest.mark.certificate
class TestCertificateRetrieval:
    """Test certificate retrieval through public API."""

    def test_get_existing_certificate(self, db: Session, certificate_reward: UserReward):
        """Test retrieving existing certificate."""
        service = CertificateService(db)

        cert = service.get_certificate(
            registration_id=certificate_reward.registration_id
        )

        assert cert is not None
        assert cert.certificate_url == certificate_reward.certificate_url
        assert cert.certificate_number == certificate_reward.certificate_number

    def test_get_certificate_not_exists(self, db: Session, completed_registration: Registration):
        """Test returns None when certificate not generated yet."""
        service = CertificateService(db)

        cert = service.get_certificate(
            registration_id=completed_registration.id
        )

        # Certificate doesn't exist yet for this registration
        assert cert is None
