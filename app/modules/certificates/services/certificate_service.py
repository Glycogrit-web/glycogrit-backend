"""
Certificate Service

Business logic for certificate generation and management using CQRS pattern.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from app.models.user_reward import UserReward, RewardType
from app.modules.certificates.domain.value_objects import (
    CertificateNumber,
    CertificateUrl,
    DownloadCount,
)
from app.modules.registrations.domain.registration import Registration
from app.services.base import BaseService
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    ValidationException,
    PermissionDeniedException,
)
import logging

logger = logging.getLogger(__name__)


class CertificateService(BaseService):
    """Service for certificate operations"""

    def __init__(self, db: Session):
        super().__init__(db)

    def generate_certificate(
        self,
        registration_id: int,
        force_regenerate: bool = False
    ) -> str:
        """
        Generate or retrieve certificate for registration.

        Business Rules:
        1. Registration must exist and be completed
        2. Certificate generated once per registration
        3. Can force regenerate if needed

        Args:
            registration_id: Registration ID
            force_regenerate: Force regenerate even if exists

        Returns:
            Certificate URL

        Raises:
            NotFoundException: If registration not found
            ValidationException: If registration not completed
        """
        # Get registration
        registration = self.db.query(Registration).filter(
            Registration.id == registration_id
        ).first()

        if not registration:
            raise NotFoundException("Registration", "id", str(registration_id))

        # Check if registration is completed
        # (For now, assume all registrations are completable)

        # Check if certificate already exists
        existing_cert = self.db.query(UserReward).filter(
            and_(
                UserReward.registration_id == registration_id,
                UserReward.reward_type == RewardType.CERTIFICATE
            )
        ).first()

        if existing_cert and not force_regenerate:
            return existing_cert.certificate_url

        # Generate certificate number
        cert_number = CertificateNumber.generate(
            registration_id,
            registration.event_id
        )

        # Generate certificate file (placeholder - actual implementation would use template)
        cert_url = self._generate_certificate_file(
            registration,
            cert_number.value
        )

        # Create or update certificate record
        if existing_cert:
            existing_cert.certificate_url = cert_url
            existing_cert.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing_cert)
            return existing_cert.certificate_url
        else:
            cert_record = UserReward(
                user_id=registration.user_id,
                registration_id=registration_id,
                event_id=registration.event_id,
                reward_type=RewardType.CERTIFICATE,
                reward_name=f"Certificate - {registration.event_id}",
                certificate_url=cert_url,
                certificate_number=cert_number.value,
                download_count=0,
            )
            self.db.add(cert_record)
            self.db.commit()
            self.db.refresh(cert_record)
            return cert_record.certificate_url

    def track_download(
        self,
        registration_id: int,
        user_id: int
    ) -> UserReward:
        """
        Track certificate download.

        Business Rules:
        1. Only owner can download
        2. Increment download count

        Args:
            registration_id: Registration ID
            user_id: User ID (for permission check)

        Returns:
            Updated UserReward

        Raises:
            NotFoundException: If certificate not found
            PermissionDeniedException: If not owner
        """
        cert = self.db.query(UserReward).filter(
            and_(
                UserReward.registration_id == registration_id,
                UserReward.reward_type == RewardType.CERTIFICATE
            )
        ).first()

        if not cert:
            raise NotFoundException("Certificate", "registration_id", str(registration_id))

        if cert.user_id != user_id:
            raise PermissionDeniedException("You can only download your own certificates")

        # Increment download count
        download_count = DownloadCount(cert.download_count or 0)
        cert.download_count = download_count.increment().value
        cert.last_downloaded_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(cert)

        return cert

    def get_certificate(
        self,
        registration_id: int
    ) -> Optional[UserReward]:
        """Get certificate by registration ID"""
        return self.db.query(UserReward).filter(
            and_(
                UserReward.registration_id == registration_id,
                UserReward.reward_type == RewardType.CERTIFICATE
            )
        ).first()

    def get_user_certificates(
        self,
        user_id: int
    ) -> list[UserReward]:
        """Get all certificates for user"""
        return self.db.query(UserReward).filter(
            and_(
                UserReward.user_id == user_id,
                UserReward.reward_type == RewardType.CERTIFICATE
            )
        ).order_by(UserReward.created_at.desc()).all()

    def _generate_certificate_file(
        self,
        registration: Registration,
        cert_number: str
    ) -> str:
        """
        Generate certificate file and upload to storage.

        This is a placeholder - actual implementation would:
        1. Use certificate template
        2. Fill in participant details
        3. Generate PDF
        4. Upload to Cloudflare R2
        5. Return public URL

        Args:
            registration: Registration record
            cert_number: Certificate number

        Returns:
            Certificate URL
        """
        # TODO: Implement actual certificate generation
        # For now, return placeholder URL
        return f"https://certificates.glycogrit.com/{cert_number}.pdf"
