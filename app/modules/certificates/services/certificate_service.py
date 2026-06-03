"""
Certificate Service

Business logic for certificate generation and management using CQRS pattern.
"""

import asyncio
import io
import logging
from datetime import datetime

from PIL import Image
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

    async def generate_certificate(
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

        # Return existing certificate only if it has a valid URL and not forcing regeneration
        # (certificate_url is set to None when template changes to trigger regeneration)
        if existing_cert and existing_cert.certificate_url and not force_regenerate:
            return {
                "certificate_url": existing_cert.certificate_url,
                "certificate_number": existing_cert.certificate_number,
            }

        cert_number = CertificateNumber.generate(registration_id, registration.event_id)

        cert_url = await self._generate_certificate_file(
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

    async def track_download(
        self, registration_id: int, user_id: int, is_admin: bool = False, force_regenerate: bool = False
    ) -> UserReward:
        """
        Track certificate download.

        Business Rules:
        1. Only owner can download
        2. Increment download count
        3. Admins bypass download limits
        4. Auto-generate certificate if it doesn't exist

        Args:
            registration_id: Registration ID
            user_id: User ID (for permission check)
            is_admin: Whether user is admin (bypasses limits)
            force_regenerate: Force regenerate certificate even if it exists

        Returns:
            Updated UserReward

        Raises:
            NotFoundException: If registration not found
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

        # Auto-generate certificate if it doesn't exist OR if certificate_url is None
        # (certificate_url is set to None when template is reprocessed to force regeneration)
        if not cert or not cert.certificate_url:
            # Verify registration exists and get user_id for permission check
            registration = (
                self.db.query(Registration).filter(Registration.id == registration_id).first()
            )

            if not registration:
                raise NotFoundException("Registration", registration_id)

            # Check ownership before generating
            if not is_admin and registration.user_id != user_id:
                raise PermissionDeniedException("You can only download your own certificates")

            # Generate certificate (this creates the UserReward record or updates certificate_url)
            # IMPORTANT: Must await since generate_certificate is async
            logger.info(f"Generating certificate for registration {registration_id} (force_regenerate={force_regenerate})")
            await self.generate_certificate(registration_id=registration_id, force_regenerate=force_regenerate)

            # Re-fetch the newly created certificate
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

    async def _generate_certificate_file(
        self, registration: Registration, cert_number: str, participant_name: str | None = None
    ) -> str:
        """
        Generate certificate PDF and upload to storage.

        Uses custom template if available, otherwise falls back to HTML generation.

        Args:
            registration: Registration record
            cert_number: Certificate number
            participant_name: Participant's display name

        Returns:
            Certificate URL
        """
        # Load event with relationships
        from app.modules.events.domain.event import Event

        event = (
            self.db.query(Event)
            .filter(Event.id == registration.event_id)
            .first()
        )

        if not event:
            raise NotFoundException("Event", registration.event_id)

        # Check if event uses custom template
        logger.info(f"Certificate generation check for event {event.id}: uses_custom_template={event.uses_custom_template}, has_url={bool(event.certificate_template_url)}, has_config={bool(event.certificate_template_config)}")

        if event.uses_custom_template and event.certificate_template_url and event.certificate_template_config:
            logger.info(f"✅ Using custom template for event {event.id}")
            return await self._generate_from_template(registration, event, cert_number, participant_name)
        else:
            # Fallback to HTML generation
            logger.info(f"⚠️ Falling back to HTML generation for event {event.id}")
            return self._generate_from_html(registration, cert_number, participant_name)

    async def _generate_from_template(
        self,
        registration: Registration,
        event,
        cert_number: str,
        participant_name: str | None
    ) -> str:
        """
        Generate certificate from custom template.

        Args:
            registration: Registration record
            event: Event record with template config
            cert_number: Certificate number
            participant_name: Participant's display name

        Returns:
            Certificate URL
        """
        from app.modules.certificates.services.template_processor import TemplateProcessor
        from app.modules.events.domain.event import EventActivity
        from app.models.activity_progress import ActivityProgress

        # Prepare user data for all supported tags
        name = participant_name or getattr(registration, "participant_name", "Participant")

        # Get activity info if available
        activity = None
        if registration.event_activity_id:
            activity = (
                self.db.query(EventActivity)
                .filter(EventActivity.id == registration.event_activity_id)
                .first()
            )

        # Get progress data if available
        progress = (
            self.db.query(ActivityProgress)
            .filter(ActivityProgress.registration_id == registration.id)
            .first()
        )

        # Format date
        completion_date = registration.confirmed_at or registration.registered_at
        formatted_date = completion_date.strftime("%B %d, %Y") if completion_date else ""

        # Build user data dictionary
        # Data mapping for certificate tags
        # Primary tags use uppercase format ({{PARTICIPANT_NAME}}, etc.)
        # Legacy lowercase tags maintained for backward compatibility
        user_data = {
            # Required tags (uppercase format - primary standard)
            "{{PARTICIPANT_NAME}}": name,        # User name
            "{{ACTIVITY_DISTANCE}}": f"{float(progress.distance_completed):.2f} km" if progress and progress.distance_completed else "N/A",  # Distance from tier registration
            "{{ACTIVITY_NAME}}": activity.name if activity else "N/A",  # Activity name from tier registration
            "{{EVENT_NAME}}": event.name,        # Event name user registered for

            # Legacy lowercase tags (backward compatibility)
            "{{name}}": name,
            "{{full_name}}": name,
            "{{distance}}": f"{float(progress.distance_completed):.2f} km" if progress and progress.distance_completed else "N/A",
            "{{activity_name}}": activity.name if activity else "N/A",
            "{{challenge_name}}": event.name,
            "{{event_name}}": event.name,
            "{{date}}": formatted_date,
            "{{sport}}": activity.activity_type if activity else "N/A",
            "{{certificate_number}}": cert_number,
            "{{digital_signature}}": "GlycoGrit Community Fitness Club",
            "{{registration_number}}": registration.registration_number,
            "{{bib_number}}": registration.bib_number or "N/A",
        }

        # Generate certificate image
        processor = TemplateProcessor()
        cert_image_bytes = await processor.generate_certificate(
            template_url=event.certificate_template_url,
            template_config=event.certificate_template_config,
            user_data=user_data
        )

        # Convert PNG to PDF
        pdf_bytes = await self._convert_image_to_pdf(cert_image_bytes)

        # Upload to R2
        storage = StorageService()
        cert_url = storage.upload_file(
            file=io.BytesIO(pdf_bytes),
            key=f"certificates/{cert_number}.pdf",
            content_type="application/pdf",
        )

        return cert_url

    def _generate_from_html(
        self,
        registration: Registration,
        cert_number: str,
        participant_name: str | None
    ) -> str:
        """
        Generate certificate from HTML template (fallback).

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

    async def _convert_image_to_pdf(self, image_bytes: bytes) -> bytes:
        """
        Convert PNG image to PDF asynchronously.

        Runs PIL operations in thread pool to avoid blocking async event loop.

        Args:
            image_bytes: PNG image bytes

        Returns:
            PDF bytes
        """
        def _sync_convert():
            """Synchronous PIL operations run in thread pool"""
            img = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB if needed (PDF doesn't support RGBA well)
            if img.mode == "RGBA":
                # Create white background
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Save as PDF
            output = io.BytesIO()
            img.save(output, format="PDF", resolution=100.0)
            output.seek(0)

            return output.read()

        # Run in thread pool to avoid blocking event loop
        return await asyncio.to_thread(_sync_convert)
