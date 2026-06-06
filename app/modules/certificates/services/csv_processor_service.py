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
        distance_idx = columns_lower.get('distance')  # Optional distance column
        # Try multiple column names for activity type (case-insensitive)
        activity_type_idx = (
            columns_lower.get('sport') or
            columns_lower.get('activity_type') or
            columns_lower.get('activity type')
        )

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
                # Validate row has enough columns for required fields
                required_indices = [email_idx, cert_url_idx]
                if len(row) <= max(idx for idx in required_indices if idx is not None):
                    stats['failed'] += 1
                    stats['errors'].append(f"Row {row_num}: Incomplete data")
                    continue

                email = row[email_idx].strip().lower()
                cert_url = row[cert_url_idx].strip() if cert_url_idx < len(row) else ""

                # Extract optional distance field (case-insensitive)
                distance_str = ""
                distance_value = None
                if distance_idx is not None and distance_idx < len(row):
                    distance_str = row[distance_idx].strip()
                    if distance_str:
                        try:
                            distance_value = float(distance_str)
                            if distance_value < 0:
                                logger.warning(f"Row {row_num}: Negative distance {distance_value}, setting to 0")
                                distance_value = 0
                        except ValueError:
                            logger.warning(f"Row {row_num}: Invalid distance value '{distance_str}', ignoring")
                            distance_value = None

                # Extract optional activity type/sport field (case-insensitive)
                activity_type_value = None
                if activity_type_idx is not None and activity_type_idx < len(row):
                    activity_type_str = row[activity_type_idx].strip().lower()
                    if activity_type_str:
                        # Normalize common variations
                        activity_type_map = {
                            'run': 'running', 'running': 'running', 'runner': 'running',
                            'cycle': 'cycling', 'cycling': 'cycling', 'bike': 'cycling', 'biking': 'cycling',
                            'walk': 'walking', 'walking': 'walking'
                        }
                        activity_type_value = activity_type_map.get(activity_type_str, activity_type_str)

                # SECURITY: Handle null/empty values explicitly
                # If email is empty, skip row
                if not email:
                    stats['failed'] += 1
                    stats['errors'].append(f"Row {row_num}: Empty email")
                    continue

                # IMPORTANT: Allow empty/null URLs to clear certificate URLs
                # This enables admin to remove certificates via CSV import
                # Empty URL will set external_certificate_url to empty string
                if not cert_url:
                    logger.warning(f"Row {row_num}: Empty URL for {email} - will clear certificate URL if exists")
                    # Continue processing to allow URL clearing

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

                # SECURITY: Track if overwriting existing certificate
                had_existing_cert = bool(registration.external_certificate_url)
                if had_existing_cert:
                    stats['already_has_certificate'] += 1
                    if cert_url:
                        logger.info(
                            f"Row {row_num}: Registration {registration.id} REPLACING certificate URL"
                        )
                    else:
                        logger.warning(
                            f"Row {row_num}: Registration {registration.id} CLEARING certificate URL (empty value provided)"
                        )

                # IMPORTANT: Update registration with certificate URL
                # This REPLACES any existing URL (even if new URL is empty/null)
                # Empty URLs will clear the certificate, allowing admin to revoke access
                registration.external_certificate_url = cert_url if cert_url else None

                # Update distance from CSV if provided
                registration.external_certificate_distance = distance_value

                # Update activity type from CSV if provided
                registration.external_certificate_activity_type = activity_type_value

                # SECURITY: Always lock certificate when updating URL (even if clearing)
                # Admin must explicitly unlock after URL change
                registration.external_certificate_unlocked = False

                # Update metadata
                registration.external_certificate_uploaded_at = datetime.utcnow()
                registration.external_certificate_uploaded_by = uploaded_by_admin_id

                stats['successful'] += 1

                if cert_url:
                    distance_info = f" (distance: {distance_value}km)" if distance_value else ""
                    sport_info = f", sport: {activity_type_value}" if activity_type_value else ""
                    logger.info(f"✅ Updated registration {registration.id} with certificate URL{distance_info}{sport_info} (locked)")
                else:
                    logger.info(f"✅ Cleared certificate URL for registration {registration.id}")

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
