"""
Certificate Service

Business logic for certificate generation and management using CQRS pattern.
"""

import io
import logging
from datetime import datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session
from weasyprint import HTML

from app.core.exceptions import (
    NotFoundException,
    PermissionDeniedException,
)
from app.models.user_reward import RewardType, UserReward
from app.modules.certificates.domain.value_objects import (
    CertificateNumber,
    DownloadCount,
)
from app.modules.registrations.domain.registration import Registration
from app.services.base import BaseService
from app.modules.gallery.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class CertificateService(BaseService):
    """Service for certificate operations"""

    def __init__(self, db: Session):
        super().__init__(db)

    def generate_certificate(
        self,
        registration_id: int,
        participant_name: str | None = None,
        force_regenerate: bool = False,
    ) -> dict:
        """
        Generate or retrieve certificate for registration.

        Business Rules:
        1. Registration must exist and be completed
        2. Certificate generated once per registration
        3. Can force regenerate if needed

        Args:
            registration_id: Registration ID
            participant_name: Participant's display name on the certificate
            force_regenerate: Force regenerate even if exists

        Returns:
            Dict with certificate_url and certificate_number

        Raises:
            NotFoundException: If registration not found
        """
        registration = (
            self.db.query(Registration).filter(Registration.id == registration_id).first()
        )

        if not registration:
            raise NotFoundException("Registration", registration_id)

        existing_cert = (
            self.db.query(UserReward)
            .filter(
                and_(
                    UserReward.registration_id == registration_id,
                    UserReward.reward_type == RewardType.CERTIFICATE,
                )
            )
            .first()
        )

        if existing_cert and not force_regenerate:
            return {
                "certificate_url": existing_cert.certificate_url,
                "certificate_number": existing_cert.certificate_number,
            }

        cert_number = CertificateNumber.generate(registration_id, registration.event_id)

        cert_url = self._generate_certificate_file(
            registration, cert_number.value, participant_name
        )

        if existing_cert:
            existing_cert.certificate_url = cert_url
            existing_cert.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing_cert)
            return {
                "certificate_url": existing_cert.certificate_url,
                "certificate_number": existing_cert.certificate_number,
            }
        else:
            cert_record = UserReward(
                user_id=registration.user_id,
                registration_id=registration_id,
                event_id=registration.event_id,
                reward_id=f"certificate-{registration_id}",
                reward_type=RewardType.CERTIFICATE,
                reward_name="E-Certificate",
                reward_image_url=cert_url,
                certificate_url=cert_url,
                certificate_number=cert_number.value,
                requires_shipping=False,
                download_count=0,
            )
            self.db.add(cert_record)
            self.db.commit()
            self.db.refresh(cert_record)
            return {
                "certificate_url": cert_record.certificate_url,
                "certificate_number": cert_record.certificate_number,
            }

    def track_download(
        self, registration_id: int, user_id: int, is_admin: bool = False
    ) -> UserReward:
        """
        Track certificate download.

        Business Rules:
        1. Only owner can download
        2. Increment download count
        3. Admins bypass download limits

        Args:
            registration_id: Registration ID
            user_id: User ID (for permission check)
            is_admin: Whether user is admin (bypasses limits)

        Returns:
            Updated UserReward

        Raises:
            NotFoundException: If certificate not found
            PermissionDeniedException: If not owner
        """
        cert = (
            self.db.query(UserReward)
            .filter(
                and_(
                    UserReward.registration_id == registration_id,
                    UserReward.reward_type == RewardType.CERTIFICATE,
                )
            )
            .first()
        )

        if not cert:
            raise NotFoundException("Certificate", registration_id)

        # Admins can download any certificate, others only their own
        if not is_admin and cert.user_id != user_id:
            raise PermissionDeniedException("You can only download your own certificates")

        # Check download limit (admins bypass)
        if not is_admin and cert.download_limit and cert.download_count >= cert.download_limit:
            raise ValueError(
                f"Download limit exceeded. You have already downloaded this certificate {cert.download_count} times"
            )

        download_count = DownloadCount(cert.download_count or 0)
        cert.download_count = download_count.increment().value
        cert.last_downloaded_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(cert)

        return cert

    def get_certificate(self, registration_id: int) -> UserReward | None:
        """Get certificate by registration ID"""
        return (
            self.db.query(UserReward)
            .filter(
                and_(
                    UserReward.registration_id == registration_id,
                    UserReward.reward_type == RewardType.CERTIFICATE,
                )
            )
            .first()
        )

    def get_user_certificates(self, user_id: int) -> list[UserReward]:
        """Get all certificates for user"""
        return (
            self.db.query(UserReward)
            .filter(
                and_(
                    UserReward.user_id == user_id, UserReward.reward_type == RewardType.CERTIFICATE
                )
            )
            .order_by(UserReward.created_at.desc())
            .all()
        )

    def _generate_certificate_file(
        self, registration: Registration, cert_number: str, participant_name: str | None = None
    ) -> str:
        """
        Generate certificate PDF and upload to storage.

        Args:
            registration: Registration record
            cert_number: Certificate number
            participant_name: Participant's display name

        Returns:
            Certificate URL
        """
        name = participant_name or getattr(registration, "participant_name", "Participant")
        html_content = f"""
        <html><body>
        <h1>Certificate of Completion</h1>
        <p>This certifies that <strong>{name}</strong> has successfully completed the challenge.</p>
        <p>Certificate Number: {cert_number}</p>
        </body></html>
        """
        pdf_bytes = HTML(string=html_content).write_pdf()

        storage = StorageService()
        cert_url = storage.upload_file(
            file=io.BytesIO(pdf_bytes),
            key=f"certificates/{cert_number}.pdf",
            content_type="application/pdf",
        )
        return cert_url
