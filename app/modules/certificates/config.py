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
    #
    # IMPORTANT: Pattern matching prioritizes specificity!
    # - Patterns are checked in order (lower index = higher priority)
    # - Autocrat patterns use substring matching (flexible)
    # - Generic "certificate url" pattern requires EXACT match (not substring)
    #
    # Examples of what matches:
    # - "Merged Doc URL" → matches pattern 0 (merged doc url)
    # - "Merged Doc URL - Auto Certificate" → matches pattern 0 (merged doc url)
    # - "Link to merged Doc" → matches pattern 1 (link to merged)
    # - "Certificate URL" (exact) → matches pattern 2 (certificate url)
    # - "Merged Doc URL - Custom Suffix" → matches pattern 0 (merged doc url)
    #
    # Why This Matters:
    # When a CSV contains BOTH "Certificate URL" (empty, from system export)
    # and "Merged Doc URL - Auto Certificate" (populated, from Autocrat),
    # the system will correctly select the Autocrat column due to priority.
    #
    CERTIFICATE_URL_PATTERNS = [
        'merged doc url',  # Priority 0: Autocrat primary pattern (substring match)
        'link to merged',  # Priority 1: Autocrat alternative pattern (substring match)
        'certificate url', # Priority 2: Generic fallback (EXACT match only)
    ]

    # Optional columns (case-insensitive matching)
    OPTIONAL_CSV_COLUMNS = [
        'name', 'participant_name', 'registration_number',
        'distance', 'Distance',
        'sport', 'Sport', 'activity_type', 'Activity Type'
    ]


# Global configuration instance
certificate_config = CertificateConfig()
