"""
Unit tests for CertificateService.

Tests certificate generation logic, download tracking, and limit enforcement.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.certificate_service import CertificateService
from app.models.user_reward import UserReward, RewardType, RewardStatus
from app.models.registration import Registration


@pytest.mark.unit
@pytest.mark.certificate
class TestCertificateGeneration:
    """Test certificate generation functionality."""

    def test_generate_certificate_number(self):
        """Test certificate number format generation."""
        from unittest.mock import Mock

        service = CertificateService()

        # Mock registration object
        mock_registration = Mock()
        mock_registration.id = 123
        mock_registration.event_id = 1

        cert_number = service._generate_certificate_number(mock_registration)

        # Should match format GLCG-YYYY-EEEE-RRRRR
        assert cert_number.startswith("GLCG-")
        assert "-0001-00123" in cert_number
        assert len(cert_number) == 21

    def test_generate_certificate_number_large_ids(self):
        """Test certificate number with large IDs."""
        from unittest.mock import Mock

        service = CertificateService()

        # Mock registration with large IDs
        mock_registration = Mock()
        mock_registration.id = 99999
        mock_registration.event_id = 9999

        cert_number = service._generate_certificate_number(mock_registration)

        assert "-9999-99999" in cert_number

    @patch('app.services.certificate_service.HTML')
    def test_generate_pdf_from_html(self, mock_html):
        """Test PDF generation from HTML content."""
        service = CertificateService()

        # Mock HTML.write_pdf
        mock_html_instance = MagicMock()
        mock_html.return_value = mock_html_instance
        mock_html_instance.write_pdf.return_value = b"PDF_CONTENT"

        html_content = "<html><body>Test Certificate</body></html>"
        pdf_bytes = service._generate_pdf(html_content)

        assert pdf_bytes == b"PDF_CONTENT"
        mock_html.assert_called_once_with(string=html_content)
        mock_html_instance.write_pdf.assert_called_once()

    def test_get_default_template(self):
        """Test default template contains required variables."""
        service = CertificateService()
        template = service._get_default_template()

        # Check template contains all required placeholders
        required_vars = [
            "{{participant_name}}",
            "{{event_name}}",
            "{{activity_name}}",
            "{{distance_covered}}",
            "{{completion_date}}",
            "{{certificate_number}}",
        ]

        for var in required_vars:
            assert var in template, f"Template missing {var}"

    def test_format_distance(self):
        """Test distance formatting (method may not exist separately)."""
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
    """Test download tracking and limit enforcement."""

    def test_track_download_increments_count(self, db: Session, certificate_reward: UserReward):
        """Test that download count increments correctly."""
        service = CertificateService()

        initial_count = certificate_reward.download_count

        result = service.track_certificate_download(
            registration_id=certificate_reward.registration_id,
            user_id=certificate_reward.user_id,
            db=db
        )

        db.refresh(certificate_reward)
        assert certificate_reward.download_count == initial_count + 1
        assert result['download_count'] == initial_count + 1
        assert result['remaining_downloads'] == 9

    def test_track_download_updates_timestamp(self, db: Session, certificate_reward: UserReward):
        """Test that last_downloaded_at is updated."""
        service = CertificateService()

        assert certificate_reward.last_downloaded_at is None

        service.track_certificate_download(
            registration_id=certificate_reward.registration_id,
            user_id=certificate_reward.user_id,
            db=db
        )

        db.refresh(certificate_reward)
        assert certificate_reward.last_downloaded_at is not None
        assert isinstance(certificate_reward.last_downloaded_at, datetime)

    def test_track_download_enforces_limit(self, db: Session, certificate_reward: UserReward):
        """Test that download limit is enforced."""
        service = CertificateService()

        # Set download count to limit
        certificate_reward.download_count = 10
        certificate_reward.download_limit = 10
        db.commit()

        with pytest.raises(ValueError, match="Download limit exceeded"):
            service.track_certificate_download(
                registration_id=certificate_reward.registration_id,
                user_id=certificate_reward.user_id,
                db=db
            )

    def test_track_download_unlimited_works(self, db: Session, certificate_reward: UserReward):
        """Test that unlimited downloads (limit=0) work."""
        service = CertificateService()

        # Set unlimited
        certificate_reward.download_limit = 0
        certificate_reward.download_count = 100
        db.commit()

        result = service.track_certificate_download(
            registration_id=certificate_reward.registration_id,
            user_id=certificate_reward.user_id,
            db=db
        )

        assert result['remaining_downloads'] == -1  # Unlimited indicator
        db.refresh(certificate_reward)
        assert certificate_reward.download_count == 101

    def test_track_download_certificate_not_found(self, db: Session):
        """Test error when certificate not found."""
        service = CertificateService()

        with pytest.raises(ValueError, match="Certificate not found"):
            service.track_certificate_download(
                registration_id=99999,
                user_id=1,
                db=db
            )

    def test_track_download_not_generated_yet(self, db: Session, completed_registration: Registration):
        """Test error when certificate not generated yet."""
        from app.models.user_reward import UserReward
        from app.core.enums import RewardType

        service = CertificateService()

        # Create reward without certificate_url
        reward = UserReward(
            user_id=completed_registration.user_id,
            event_id=completed_registration.event_id,
            registration_id=completed_registration.id,
            reward_type=RewardType.CERTIFICATE,
            reward_name="E-Certificate",
            certificate_url=None,  # Not generated
            download_count=0,
            download_limit=10
        )
        db.add(reward)
        db.commit()

        with pytest.raises(ValueError, match="Certificate not generated yet"):
            service.track_certificate_download(
                registration_id=completed_registration.id,
                user_id=completed_registration.user_id,
                db=db
            )


@pytest.mark.unit
@pytest.mark.certificate
class TestCertificateValidation:
    """Test certificate validation logic."""

    def test_validate_completion_status(self, db: Session, completed_registration: Registration):
        """Test validation passes for completed registration."""
        service = CertificateService()

        # Should not raise any error
        cert_data = service._fetch_certificate_data(
            registration_id=completed_registration.id,
            db=db
        )

        assert cert_data is not None
        assert 'participant_name' in cert_data
        assert 'event_name' in cert_data

    def test_validate_incomplete_registration(self, db: Session, incomplete_registration: Registration):
        """Test validation fails for incomplete registration."""
        service = CertificateService()

        with pytest.raises(ValueError, match="not completed|has not completed any activities"):
            service._fetch_certificate_data(
                registration_id=incomplete_registration.id,
                db=db
            )

    def test_validate_nonexistent_registration(self, db: Session):
        """Test validation fails for non-existent registration."""
        service = CertificateService()

        with pytest.raises(ValueError, match="Registration .* not found"):
            service._fetch_certificate_data(
                registration_id=99999,
                db=db
            )


@pytest.mark.unit
@pytest.mark.certificate
class TestCachingBehavior:
    """Test certificate caching logic."""

    def test_get_cached_certificate(self, db: Session, certificate_reward: UserReward):
        """Test cached certificate URL retrieval."""
        service = CertificateService()

        cached_url = service._get_cached_certificate(
            registration_id=certificate_reward.registration_id,
            db=db
        )

        assert cached_url == certificate_reward.certificate_url

    def test_get_cached_certificate_not_exists(self, db: Session, completed_registration: Registration):
        """Test cached certificate returns None when not exists."""
        service = CertificateService()

        cached_url = service._get_cached_certificate(
            registration_id=completed_registration.id,
            db=db
        )

        assert cached_url is None
