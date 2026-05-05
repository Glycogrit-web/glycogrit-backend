"""
Certificate Generation Service

This service handles the generation of PDF certificates for completed race participants.
Uses WeasyPrint for PDF generation and Jinja2 for template rendering.
"""

from weasyprint import HTML
from jinja2 import Template
from datetime import datetime
from typing import Dict, Optional
import io
import logging

from app.services.storage_service import StorageService
from app.core.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CertificateService:
    """Service for generating and managing e-certificates."""

    def __init__(self):
        self.storage_service = StorageService()

    def generate_certificate(
        self,
        registration_id: int,
        force_regenerate: bool = False,
        db: Optional[Session] = None
    ) -> str:
        """
        Generate certificate for a completed registration.

        Args:
            registration_id: ID of the registration
            force_regenerate: If True, regenerate even if certificate exists
            db: Database session (optional, will create if not provided)

        Returns:
            str: R2 URL of the generated certificate

        Raises:
            ValueError: If registration not found or not completed
        """
        logger.info(f"Starting certificate generation for registration_id={registration_id}")

        # Create database session if not provided
        if db is None:
            db = next(get_db())

        try:
            # 1. Check if certificate already exists
            if not force_regenerate:
                existing_url = self._get_cached_certificate(registration_id, db)
                if existing_url:
                    logger.info(f"Certificate already exists for registration_id={registration_id}, returning cached URL")
                    return existing_url

            # 2. Fetch registration data
            logger.info(f"Fetching certificate data for registration_id={registration_id}")
            data = self._fetch_certificate_data(registration_id, db)

            # 3. Validate completion
            if not data.get('is_completed'):
                raise ValueError(f"Registration {registration_id} not completed yet")

            # 4. Load template
            logger.info(f"Loading template for event_id={data['event_id']}")
            template_html = self._load_template(data['event_id'], db)

            # 5. Fill template with data
            logger.info("Filling template with participant data")
            filled_html = self._fill_template(template_html, data)

            # 6. Generate PDF
            logger.info("Generating PDF from HTML")
            start_time = datetime.now()
            pdf_bytes = self._generate_pdf(filled_html)
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"PDF generated in {generation_time:.0f}ms, size={len(pdf_bytes)/1024:.2f}KB")

            # 7. Upload to R2
            logger.info("Uploading certificate to R2 storage")
            certificate_url = self._upload_certificate(
                registration_id=registration_id,
                user_id=data['user_id'],
                event_id=data['event_id'],
                pdf_bytes=pdf_bytes,
                db=db
            )

            # 8. Update UserReward record
            logger.info("Updating UserReward record with certificate URL")
            self._update_reward_record(
                registration_id=registration_id,
                certificate_url=certificate_url,
                certificate_number=data['certificate_number'],
                db=db
            )

            logger.info(f"Certificate generation completed successfully for registration_id={registration_id}")
            return certificate_url

        except Exception as e:
            logger.error(f"Certificate generation failed for registration_id={registration_id}: {str(e)}")
            raise

    def _fetch_certificate_data(self, registration_id: int, db: Session) -> Dict:
        """
        Fetch all data needed for certificate generation.

        Args:
            registration_id: ID of the registration
            db: Database session

        Returns:
            Dict containing all certificate data

        Raises:
            ValueError: If registration not found
        """
        # Import here to avoid circular imports
        from app.modules.registrations.domain.registration import Registration
        from app.models.activity_progress import ActivityProgress

        # Query registration with all related data
        registration = db.query(Registration).filter(
            Registration.id == registration_id
        ).first()

        if not registration:
            raise ValueError(f"Registration {registration_id} not found")

        # Get related entities
        activity_progress = registration.activity_progress
        event = registration.event
        user = registration.user
        activity = registration.activity  # EventActivity relationship

        # Check if activity is completed
        is_completed = activity_progress and activity_progress.is_completed

        # Build certificate data dictionary
        data = {
            'registration_id': registration_id,
            'user_id': user.id,
            'event_id': event.id,
            'is_completed': is_completed,

            # Certificate content
            'participant_name': registration.participant_name or user.full_name,
            'event_name': event.name,
            'event_location': f"{event.city}, {event.state}" if event.city else event.location_name or "Virtual",
            'activity_name': activity.name if activity else "Challenge",
            'distance_covered': f"{float(activity_progress.distance_completed):.2f}" if activity_progress else "0.00",
            'completion_date': activity_progress.completed_at.strftime('%B %d, %Y') if activity_progress and activity_progress.completed_at else datetime.now().strftime('%B %d, %Y'),
            'event_date': event.event_date.strftime('%B %d, %Y') if event.event_date else datetime.now().strftime('%B %d, %Y'),
            'certificate_number': self._generate_certificate_number(registration),
            'organizer_name': event.organizer.full_name if event.organizer else "GlycoGrit Team",
            'logo_url': event.banner_image_url or 'https://via.placeholder.com/80x80.png?text=Logo',
        }

        logger.debug(f"Certificate data fetched: {data['certificate_number']} for {data['participant_name']}")
        return data

    def _generate_certificate_number(self, registration) -> str:
        """
        Generate unique certificate number.

        Format: GLCG-{YEAR}-{EVENT_ID}-{REGISTRATION_ID}

        Args:
            registration: Registration object

        Returns:
            str: Unique certificate number
        """
        year = datetime.now().year
        cert_number = f"GLCG-{year}-{registration.event_id:04d}-{registration.id:05d}"
        logger.debug(f"Generated certificate number: {cert_number}")
        return cert_number

    def _load_template(self, event_id: int, db: Session) -> str:
        """
        Load certificate template HTML.

        Args:
            event_id: ID of the event
            db: Database session

        Returns:
            str: Template HTML string
        """
        # TODO: In Phase 2, implement database template loading
        # For now, return default template
        return self._get_default_template()

    def _get_default_template(self) -> str:
        """
        Get default certificate template HTML.

        Returns:
            str: Default template HTML
        """
        # Simple default template for Phase 1
        # In Phase 2, this will be loaded from a file or database
        template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        @page {
            size: A4 landscape;
            margin: 0;
        }
        body {
            font-family: 'Arial', sans-serif;
            margin: 0;
            width: 297mm;
            height: 210mm;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            padding: 40px 60px;
            border-radius: 20px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            max-width: 800px;
        }
        .title {
            font-size: 48pt;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 20px;
            text-transform: uppercase;
        }
        .subtitle {
            font-size: 18pt;
            color: #4a5568;
            margin-bottom: 30px;
        }
        .participant-name {
            font-size: 56pt;
            font-weight: 700;
            color: #2d3748;
            margin: 30px 0;
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
        }
        .achievement {
            font-size: 18pt;
            color: #4a5568;
            line-height: 1.8;
            margin: 25px 0;
        }
        .details {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 30px;
        }
        .detail-item {
            background: #f7fafc;
            padding: 15px 25px;
            border-radius: 10px;
        }
        .detail-label {
            font-size: 12pt;
            color: #667eea;
            font-weight: 600;
            text-transform: uppercase;
        }
        .detail-value {
            font-size: 16pt;
            color: #2d3748;
            font-weight: 700;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e2e8f0;
            font-size: 10pt;
            color: #718096;
        }
        .cert-number {
            position: absolute;
            top: 20px;
            right: 30px;
            font-size: 10pt;
            color: white;
        }
    </style>
</head>
<body>
    <div class="cert-number">Certificate No: {{certificate_number}}</div>

    <div class="container">
        <div class="title">Certificate of Achievement</div>
        <div class="subtitle">This is proudly presented to</div>

        <div class="participant-name">{{participant_name}}</div>

        <div class="achievement">
            for successfully completing the<br>
            <strong>{{event_name}}</strong><br>
            held on {{event_date}} at {{event_location}}
        </div>

        <div class="details">
            <div class="detail-item">
                <div class="detail-label">Activity</div>
                <div class="detail-value">{{activity_name}}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Distance</div>
                <div class="detail-value">{{distance_covered}} km</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Completed</div>
                <div class="detail-value">{{completion_date}}</div>
            </div>
        </div>

        <div class="footer">
            Generated by GlycoGrit • Fitness Challenge Platform<br>
            Organizer: {{organizer_name}}
        </div>
    </div>
</body>
</html>
"""
        return template

    def _fill_template(self, template_html: str, data: Dict) -> str:
        """
        Fill template with actual data using Jinja2.

        Args:
            template_html: Template HTML string
            data: Dictionary with certificate data

        Returns:
            str: Filled HTML string
        """
        template = Template(template_html)
        filled_html = template.render(**data)
        logger.debug(f"Template filled, HTML length: {len(filled_html)} characters")
        return filled_html

    def _generate_pdf(self, html_content: str) -> bytes:
        """
        Generate PDF from HTML using WeasyPrint.

        Args:
            html_content: HTML content as string

        Returns:
            bytes: PDF file bytes
        """
        try:
            # Create HTML document and write to BytesIO
            pdf_file = io.BytesIO()
            HTML(string=html_content).write_pdf(pdf_file)
            pdf_bytes = pdf_file.getvalue()
            logger.debug(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            raise ValueError(f"Failed to generate PDF: {str(e)}")

    def _upload_certificate(
        self,
        registration_id: int,
        user_id: int,
        event_id: int,
        pdf_bytes: bytes,
        db: Session
    ) -> str:
        """
        Upload certificate to Cloudflare R2.

        Args:
            registration_id: Registration ID
            user_id: User ID
            event_id: Event ID
            pdf_bytes: PDF file bytes
            db: Database session

        Returns:
            str: Certificate URL
        """
        # Generate R2 key
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        key = f"certificates/event_{event_id}/user_{user_id}/cert_{registration_id}_{timestamp}.pdf"

        # Upload to R2
        file_obj = io.BytesIO(pdf_bytes)

        try:
            certificate_url = self.storage_service.upload_file(
                file=file_obj,
                key=key,
                content_type='application/pdf'
            )
            logger.info(f"Certificate uploaded to R2: {key}")
            return certificate_url
        except Exception as e:
            logger.error(f"Failed to upload certificate to R2: {str(e)}")
            raise ValueError(f"Failed to upload certificate: {str(e)}")

    def _update_reward_record(
        self,
        registration_id: int,
        certificate_url: str,
        certificate_number: str,
        db: Session
    ):
        """
        Update or create UserReward record with certificate URL.

        Args:
            registration_id: Registration ID
            certificate_url: URL of the certificate
            certificate_number: Unique certificate number
            db: Database session
        """
        # Import here to avoid circular imports
        from app.models.user_reward import UserReward
        from app.models.user_reward import RewardType, RewardStatus
        from app.modules.registrations.domain.registration import Registration

        # Find existing certificate reward
        reward = db.query(UserReward).filter(
            UserReward.registration_id == registration_id,
            UserReward.reward_type == RewardType.CERTIFICATE
        ).first()

        if reward:
            # Update existing reward
            reward.reward_image_url = certificate_url
            reward.status = RewardStatus.DELIVERED
            reward.delivered_at = datetime.utcnow()
            # Store certificate metadata in shipping_details JSONB field
            if not reward.shipping_details:
                reward.shipping_details = {}
            reward.shipping_details['certificate_url'] = certificate_url
            reward.shipping_details['certificate_number'] = certificate_number
            reward.shipping_details['download_count'] = reward.shipping_details.get('download_count', 0)
            reward.shipping_details['download_limit'] = 10
            logger.info(f"Updated existing reward record for registration_id={registration_id}")
        else:
            # Create new reward record
            registration = db.query(Registration).get(registration_id)
            reward = UserReward(
                user_id=registration.user_id,
                event_id=registration.event_id,
                registration_id=registration_id,
                reward_id="certificate",
                reward_type=RewardType.CERTIFICATE,
                reward_name="E-Certificate",
                reward_image_url=certificate_url,
                requires_shipping=False,
                status=RewardStatus.DELIVERED,
                awarded_at=datetime.utcnow(),
                delivered_at=datetime.utcnow(),
                shipping_details={
                    'certificate_url': certificate_url,
                    'certificate_number': certificate_number,
                    'download_count': 0,
                    'download_limit': 10
                }
            )
            db.add(reward)
            logger.info(f"Created new reward record for registration_id={registration_id}")

        db.commit()
        logger.debug(f"Reward record saved with certificate_number={certificate_number}")

    def track_certificate_download(
        self,
        registration_id: int,
        user_id: int,
        db: Session
    ) -> Dict:
        """
        Track certificate download and enforce limits.

        Args:
            registration_id: Registration ID
            user_id: User ID requesting download
            db: Database session

        Returns:
            Dict with certificate_url and download info

        Raises:
            ValueError: If download limit exceeded or certificate not found
        """
        # Import here to avoid circular imports
        from app.models.user_reward import UserReward
        from app.models.user_reward import RewardType

        # Get reward record
        reward = db.query(UserReward).filter(
            UserReward.registration_id == registration_id,
            UserReward.user_id == user_id,
            UserReward.reward_type == RewardType.CERTIFICATE
        ).first()

        if not reward:
            raise ValueError("Certificate not found for this registration")

        # Get certificate data from shipping_details JSONB
        if not reward.shipping_details or 'certificate_url' not in reward.shipping_details:
            # Fallback to reward_image_url if shipping_details not set
            certificate_url = reward.reward_image_url
            if not certificate_url:
                raise ValueError("Certificate not generated yet")
            # Initialize shipping_details
            reward.shipping_details = {
                'certificate_url': certificate_url,
                'certificate_number': 'N/A',
                'download_count': 0,
                'download_limit': 10
            }

        certificate_data = reward.shipping_details
        certificate_url = certificate_data.get('certificate_url')
        certificate_number = certificate_data.get('certificate_number', 'N/A')
        download_count = certificate_data.get('download_count', 0)
        download_limit = certificate_data.get('download_limit', 10)

        if not certificate_url:
            raise ValueError("Certificate not generated yet")

        # Check download limit (0 means unlimited)
        if download_limit > 0 and download_count >= download_limit:
            raise ValueError(
                f"Download limit exceeded. You have already downloaded this certificate "
                f"{download_count} times (limit: {download_limit}). "
                f"Please contact support if you need additional downloads."
            )

        # Increment download count in shipping_details
        certificate_data['download_count'] = download_count + 1
        certificate_data['last_downloaded_at'] = datetime.utcnow().isoformat()
        reward.shipping_details = certificate_data
        db.commit()

        remaining = download_limit - certificate_data['download_count'] if download_limit > 0 else -1

        logger.info(
            f"Certificate download tracked: registration_id={registration_id}, "
            f"downloads={certificate_data['download_count']}/{download_limit}"
        )

        return {
            'certificate_url': certificate_url,
            'certificate_number': certificate_number,
            'download_count': certificate_data['download_count'],
            'download_limit': download_limit,
            'remaining_downloads': remaining,
            'last_downloaded_at': certificate_data.get('last_downloaded_at')
        }

    def _get_cached_certificate(self, registration_id: int, db: Session) -> Optional[str]:
        """
        Check if certificate already generated and return URL.

        Args:
            registration_id: Registration ID
            db: Database session

        Returns:
            Optional[str]: Certificate URL if exists, None otherwise
        """
        # Import here to avoid circular imports
        from app.models.user_reward import UserReward
        from app.models.user_reward import RewardType

        reward = db.query(UserReward).filter(
            UserReward.registration_id == registration_id,
            UserReward.reward_type == RewardType.CERTIFICATE
        ).first()

        if reward:
            # Check shipping_details for certificate_url
            if reward.shipping_details and 'certificate_url' in reward.shipping_details:
                certificate_url = reward.shipping_details['certificate_url']
                logger.debug(f"Found cached certificate for registration_id={registration_id}")
                return certificate_url
            # Fallback to reward_image_url
            elif reward.reward_image_url:
                logger.debug(f"Found cached certificate (fallback) for registration_id={registration_id}")
                return reward.reward_image_url

        return None

    def bulk_generate_certificates(self, event_id: int, db: Session) -> Dict:
        """
        Generate certificates for all completed participants of an event.

        Note: In Phase 3, this will be async with Celery.
        For Phase 1, this is synchronous.

        Args:
            event_id: Event ID
            db: Database session

        Returns:
            Dict with generation results
        """
        # Import here to avoid circular imports
        from app.modules.registrations.domain.registration import Registration
        from app.models.activity_progress import ActivityProgress

        logger.info(f"Starting bulk certificate generation for event_id={event_id}")

        # Fetch all completed registrations
        completed_registrations = db.query(Registration).join(
            ActivityProgress
        ).filter(
            Registration.event_id == event_id,
            ActivityProgress.is_completed == True,
            ActivityProgress.completed_at.isnot(None)
        ).all()

        total = len(completed_registrations)
        successful = 0
        failed = 0
        errors = []

        logger.info(f"Found {total} completed registrations for event_id={event_id}")

        for registration in completed_registrations:
            try:
                self.generate_certificate(registration.id, db=db)
                successful += 1
                logger.debug(f"Certificate generated for registration_id={registration.id}")
            except Exception as e:
                failed += 1
                error_msg = f"registration_id={registration.id}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Failed to generate certificate for {error_msg}")

        result = {
            'event_id': event_id,
            'total_certificates': total,
            'successful': successful,
            'failed': failed,
            'errors': errors[:10],  # Return first 10 errors
            'status': 'completed'
        }

        logger.info(f"Bulk generation completed: {successful}/{total} successful, {failed} failed")
        return result
