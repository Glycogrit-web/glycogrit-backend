"""
Registration Export Service
Handles CSV export with email column for Autocrat certificate processing
"""
import csv
import io
import logging
from typing import List

from sqlalchemy.orm import Session, joinedload

from app.modules.registrations.domain.registration import Registration
from app.models.user import User
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class RegistrationExportService(BaseService):
    """Service for exporting registration data to CSV format"""

    def __init__(self, db: Session):
        super().__init__(db)

    def export_registrations_csv(self, event_id: int) -> str:
        """
        Export registrations for an event to CSV format

        Includes email column for Autocrat compatibility and certificate generation

        Args:
            event_id: Event ID to export registrations for

        Returns:
            CSV content as string
        """
        # Fetch registrations with user data (eager load to avoid N+1 queries)
        registrations = (
            self.db.query(Registration)
            .options(joinedload(Registration.user))
            .filter(Registration.event_id == event_id)
            .order_by(Registration.registered_at)
            .all()
        )

        # Define CSV columns
        headers = [
            'Registration ID',
            'Registration Number',
            'BIB Number',
            'Email',  # ← NEW: Required for Autocrat
            'Participant Name',
            'Age',
            'Gender',
            'T-Shirt Size',
            'Status',
            'Total Paid',
            'Payment Status',
            'Registered Date',
            'Confirmed Date',
            'Shipping Email',
            'Shipping Phone',
            'Shipping Address',
            'Shipping City',
            'Shipping State',
            'Shipping Postal Code',
            'Shipping Country',
        ]

        # Build CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)

        for reg in registrations:
            # Safely access user email
            user_email = reg.user.email if reg.user else 'N/A'

            writer.writerow([
                reg.id,
                reg.registration_number,
                reg.bib_number or 'N/A',
                user_email,  # ← User's primary email for Autocrat matching
                reg.participant_name,
                reg.age or 'N/A',
                reg.gender or 'N/A',
                reg.t_shirt_size or 'N/A',
                reg.status,
                f"{float(reg.total_amount_paid):.2f}" if reg.total_amount_paid else '0.00',
                reg.last_payment_status or 'N/A',
                reg.registered_at.strftime('%Y-%m-%d %H:%M:%S') if reg.registered_at else 'N/A',
                reg.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if reg.confirmed_at else 'N/A',
                reg.shipping_email or 'N/A',
                reg.shipping_phone or 'N/A',
                reg.shipping_address_line1 or 'N/A',
                reg.shipping_city or 'N/A',
                reg.shipping_state or 'N/A',
                reg.shipping_postal_code or 'N/A',
                reg.shipping_country or 'India',
            ])

        csv_content = output.getvalue()
        output.close()

        logger.info(f"📥 Exported {len(registrations)} registrations for event {event_id}")

        return csv_content
