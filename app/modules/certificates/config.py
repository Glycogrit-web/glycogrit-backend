"""
Certificate Module Configuration
Separate configuration for external certificate distribution via Google Drive
"""
import os
from typing import Optional

class CertificateConfig:
    """Configuration for certificate distribution system"""

    # Google Service Account for Drive Access (Base64 encoded JSON key file content)
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    # Whether Google Drive integration is enabled
    @classmethod
    def is_google_drive_enabled(cls) -> bool:
        """Check if Google Drive integration is properly configured"""
        return bool(cls.GOOGLE_SERVICE_ACCOUNT_JSON and cls.GOOGLE_SERVICE_ACCOUNT_JSON.strip())

    # CSV Processing Settings
    MAX_CSV_SIZE_MB: int = 10  # Maximum CSV file size in MB
    MAX_CSV_ROWS: int = 10000  # Maximum number of rows to process

    # Certificate Requirements
    # Required columns (flexible matching for Autocrat-generated names)
    REQUIRED_EMAIL_COLUMN = 'email'  # Exact match required

    # Certificate URL column patterns (Autocrat generates variable names)
    # Examples: "Merged Doc URL - Auto Certificate", "Link to merged Doc - Auto Certificate"
    # We search for columns containing these patterns (case-insensitive)
    CERTIFICATE_URL_PATTERNS = [
        'merged doc url',  # Matches "Merged Doc URL", "Merged Doc URL - Auto Certificate"
        'link to merged',  # Matches "Link to merged Doc", "Link to merged Doc - Auto Certificate"
        'certificate url', # Fallback for generic "Certificate URL" columns
    ]

    # Optional columns (case-insensitive matching)
    OPTIONAL_CSV_COLUMNS = [
        'name', 'participant_name', 'registration_number',
        'distance', 'Distance',
        'sport', 'Sport', 'activity_type', 'Activity Type'
    ]


# Global configuration instance
certificate_config = CertificateConfig()
