"""
CSV Processing Service for Bulk Certificate Upload
Processes Autocrat-generated CSV with certificate URLs from Google Drive
"""
import csv
import io
import logging
from datetime import datetime
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.models.user import User
from app.modules.certificates.config import certificate_config
from app.modules.registrations.domain.registration import Registration
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class CSVProcessorService(BaseService):
    """Service for processing certificate CSV uploads from Autocrat"""

    def __init__(self, db: Session):
        super().__init__(db)

    def validate_csv_format(self, csv_content: str) -> Tuple[bool, str, List[str]]:
        """
        Validate CSV has required columns

        Returns:
            Tuple of (is_valid, error_message, column_names)
        """
        try:
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)

            if not reader.fieldnames:
                return False, "CSV file is empty or has no headers", []

            columns = [col.strip() for col in reader.fieldnames]

            # Check for required columns (case-insensitive)
            columns_lower = [col.lower() for col in columns]

            missing = []
            for required in certificate_config.REQUIRED_CSV_COLUMNS:
                if required.lower() not in columns_lower:
                    missing.append(required)

            if missing:
                return False, f"Missing required columns: {', '.join(missing)}", columns

            return True, "", columns

        except Exception as e:
            return False, f"Invalid CSV format: {str(e)}", []

    def process_certificate_csv(
        self,
        csv_content: str,
        event_id: int,
        uploaded_by_admin_id: int
    ) -> Dict:
        """
        Process CSV and update registrations with certificate URLs

        Args:
            csv_content: CSV file content as string
            event_id: Event ID to match registrations
            uploaded_by_admin_id: Admin user ID uploading the CSV

        Returns:
            Dictionary with processing statistics
        """
        # Validate format
        is_valid, error, columns = self.validate_csv_format(csv_content)
        if not is_valid:
            raise ValidationException(error)

        # Find column indices (case-insensitive)
        columns_lower = {col.lower(): i for i, col in enumerate(columns)}
        email_idx = columns_lower.get('email')
        cert_url_idx = columns_lower.get('merged doc url')

        if email_idx is None or cert_url_idx is None:
            raise ValidationException("Could not find required columns in CSV")

        # Process rows
        csv_file = io.StringIO(csv_content)
        reader = csv.reader(csv_file)
        next(reader)  # Skip header

        stats = {
            'total_rows': 0,
            'successful': 0,
            'failed': 0,
            'not_found': 0,
            'already_has_certificate': 0,
            'errors': []
        }

        for row_num, row in enumerate(reader, start=2):
            stats['total_rows'] += 1

            try:
                # Validate row has enough columns
                if len(row) <= max(email_idx, cert_url_idx):
                    stats['failed'] += 1
                    stats['errors'].append(f"Row {row_num}: Incomplete data")
                    continue

                email = row[email_idx].strip().lower()
                cert_url = row[cert_url_idx].strip()

                # Skip empty rows
                if not email or not cert_url:
                    stats['failed'] += 1
                    stats['errors'].append(f"Row {row_num}: Empty email or URL")
                    continue

                # Find user by email
                user = self.db.query(User).filter(
                    User.email == email
                ).first()

                if not user:
                    stats['not_found'] += 1
                    stats['errors'].append(f"Row {row_num}: User not found - {email}")
                    continue

                # Find registration for this event
                registration = self.db.query(Registration).filter(
                    Registration.user_id == user.id,
                    Registration.event_id == event_id
                ).first()

                if not registration:
                    stats['not_found'] += 1
                    stats['errors'].append(
                        f"Row {row_num}: No registration found - {email} for event {event_id}"
                    )
                    continue

                # Check if already has external certificate
                if registration.external_certificate_url:
                    stats['already_has_certificate'] += 1
                    logger.info(
                        f"Row {row_num}: Registration {registration.id} already has certificate (will overwrite)"
                    )

                # Update registration with certificate URL
                registration.external_certificate_url = cert_url
                registration.external_certificate_unlocked = False  # Admin must unlock
                registration.external_certificate_uploaded_at = datetime.utcnow()
                registration.external_certificate_uploaded_by = uploaded_by_admin_id

                stats['successful'] += 1
                logger.info(f"✅ Updated registration {registration.id} with certificate URL")

            except Exception as e:
                stats['failed'] += 1
                error_msg = f"Row {row_num}: {str(e)}"
                stats['errors'].append(error_msg)
                logger.error(error_msg)

        # Commit all changes
        try:
            self.db.commit()
            logger.info(
                f"📊 CSV Processing Complete: {stats['successful']}/{stats['total_rows']} successful"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Failed to commit changes: {e}")
            raise ValidationException(f"Database commit failed: {str(e)}")

        return stats

    def get_registrations_with_certificates(self, event_id: int) -> List[Dict]:
        """
        Get all registrations that have external certificates for an event

        Args:
            event_id: Event ID

        Returns:
            List of registration dictionaries with certificate info
        """
        registrations = (
            self.db.query(Registration)
            .filter(
                Registration.event_id == event_id,
                Registration.external_certificate_url.isnot(None)
            )
            .all()
        )

        results = []
        for reg in registrations:
            results.append({
                'id': reg.id,
                'registration_number': reg.registration_number,
                'participant_name': reg.participant_name,
                'user_email': reg.user.email if reg.user else None,
                'external_certificate_url': reg.external_certificate_url,
                'external_certificate_unlocked': reg.external_certificate_unlocked,
                'external_certificate_uploaded_at': reg.external_certificate_uploaded_at,
            })

        return results
