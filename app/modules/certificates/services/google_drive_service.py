"""
Google Drive Service for Certificate Access
Uses Service Account for secure, token-free access to certificate files
"""
import base64
import io
import json
import logging
from typing import Optional

from app.modules.certificates.config import certificate_config

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class GoogleDriveService:
    """Service for accessing Google Drive files via Service Account"""

    def __init__(self):
        self._service = None
        self._initialize_service()

    def _initialize_service(self):
        """Initialize Google Drive API client with service account"""
        try:
            if not certificate_config.is_google_drive_enabled():
                logger.warning("⚠️  Google Service Account not configured - external certificates disabled")
                return

            # Import Google libraries only when needed
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
            except ImportError:
                logger.error("❌ Google API libraries not installed. Install: pip install google-auth google-api-python-client")
                return

            # Decode base64 credentials
            credentials_json = base64.b64decode(
                certificate_config.GOOGLE_SERVICE_ACCOUNT_JSON
            ).decode('utf-8')
            credentials_dict = json.loads(credentials_json)

            # Create credentials
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=SCOPES
            )

            # Build service
            self._service = build('drive', 'v3', credentials=credentials)
            logger.info("✅ Google Drive Service Account initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Drive service: {e}")
            self._service = None

    def is_available(self) -> bool:
        """Check if Google Drive service is available"""
        return self._service is not None

    def extract_file_id(self, drive_url: str) -> Optional[str]:
        """
        Extract file ID from Google Drive URL

        Supports formats:
        - https://drive.google.com/file/d/{FILE_ID}/view
        - https://drive.google.com/open?id={FILE_ID}
        - Direct file ID (already extracted)

        Args:
            drive_url: Google Drive URL or file ID

        Returns:
            File ID string or None if invalid
        """
        if not drive_url:
            return None

        drive_url = drive_url.strip()

        # Already a file ID (no slashes or http)
        if '/' not in drive_url and 'http' not in drive_url.lower():
            return drive_url

        # Extract from /file/d/{FILE_ID}/ format
        if '/file/d/' in drive_url:
            parts = drive_url.split('/file/d/')
            if len(parts) > 1:
                file_id = parts[1].split('/')[0].split('?')[0]
                return file_id

        # Extract from ?id={FILE_ID} format
        if '?id=' in drive_url or '&id=' in drive_url:
            for param in drive_url.replace('?', '&').split('&'):
                if param.startswith('id='):
                    return param.split('id=')[1]

        logger.warning(f"Could not extract file ID from URL: {drive_url}")
        return None

    def download_file(self, file_id: str) -> Optional[bytes]:
        """
        Download file from Google Drive by file ID

        Args:
            file_id: Google Drive file ID

        Returns:
            File bytes or None if error
        """
        if not self.is_available():
            logger.error("Google Drive service not initialized")
            return None

        try:
            from googleapiclient.http import MediaIoBaseDownload

            # Request file download
            request = self._service.files().get_media(fileId=file_id)

            # Download to memory
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.debug(f"Download progress: {progress}%")

            file_buffer.seek(0)
            file_bytes = file_buffer.read()

            logger.info(f"✅ Downloaded file {file_id} ({len(file_bytes)} bytes)")
            return file_bytes

        except Exception as e:
            logger.error(f"❌ Error downloading file {file_id}: {e}")
            return None

    def get_file_metadata(self, file_id: str) -> Optional[dict]:
        """
        Get file metadata (name, mimeType, size, etc.)

        Args:
            file_id: Google Drive file ID

        Returns:
            Dictionary with file metadata or None if error
        """
        if not self.is_available():
            return None

        try:
            file_metadata = self._service.files().get(
                fileId=file_id,
                fields='id,name,mimeType,size,createdTime,modifiedTime'
            ).execute()

            logger.info(f"Retrieved metadata for {file_id}: {file_metadata.get('name')}")
            return file_metadata

        except Exception as e:
            logger.error(f"Error getting metadata for {file_id}: {e}")
            return None

    def verify_file_access(self, file_id: str) -> bool:
        """
        Verify that the service account has access to a file

        Args:
            file_id: Google Drive file ID

        Returns:
            True if accessible, False otherwise
        """
        metadata = self.get_file_metadata(file_id)
        return metadata is not None
