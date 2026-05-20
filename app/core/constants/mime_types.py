"""
MIME Types Constants

Centralized constants for MIME types used throughout the application,
particularly for file uploads and content type validation.
"""


class MimeTypes:
    """Common MIME type constants."""

    # Image Types
    IMAGE_JPEG = "image/jpeg"
    IMAGE_JPG = "image/jpg"
    IMAGE_PNG = "image/png"
    IMAGE_GIF = "image/gif"
    IMAGE_WEBP = "image/webp"
    IMAGE_SVG = "image/svg+xml"
    IMAGE_BMP = "image/bmp"
    IMAGE_TIFF = "image/tiff"

    # Document Types
    APPLICATION_PDF = "application/pdf"
    APPLICATION_JSON = "application/json"
    APPLICATION_XML = "application/xml"
    TEXT_PLAIN = "text/plain"
    TEXT_HTML = "text/html"
    TEXT_CSS = "text/css"
    TEXT_CSV = "text/csv"

    # Office Document Types
    APPLICATION_DOC = "application/msword"
    APPLICATION_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    APPLICATION_XLS = "application/vnd.ms-excel"
    APPLICATION_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    APPLICATION_PPT = "application/vnd.ms-powerpoint"
    APPLICATION_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    # Archive Types
    APPLICATION_ZIP = "application/zip"
    APPLICATION_GZIP = "application/gzip"
    APPLICATION_TAR = "application/x-tar"

    # Video Types
    VIDEO_MP4 = "video/mp4"
    VIDEO_MPEG = "video/mpeg"
    VIDEO_WEBM = "video/webm"
    VIDEO_AVI = "video/x-msvideo"

    # Audio Types
    AUDIO_MP3 = "audio/mpeg"
    AUDIO_WAV = "audio/wav"
    AUDIO_OGG = "audio/ogg"

    # Form Data
    APPLICATION_FORM_URLENCODED = "application/x-www-form-urlencoded"
    MULTIPART_FORM_DATA = "multipart/form-data"

    # Binary
    APPLICATION_OCTET_STREAM = "application/octet-stream"


class AllowedMimeTypes:
    """Grouped MIME types for validation purposes."""

    # Image formats allowed for upload
    IMAGES = [
        MimeTypes.IMAGE_JPEG,
        MimeTypes.IMAGE_JPG,
        MimeTypes.IMAGE_PNG,
        MimeTypes.IMAGE_WEBP,
        MimeTypes.IMAGE_GIF,
    ]

    # Profile picture allowed formats
    PROFILE_PICTURES = [
        MimeTypes.IMAGE_JPEG,
        MimeTypes.IMAGE_JPG,
        MimeTypes.IMAGE_PNG,
        MimeTypes.IMAGE_WEBP,
    ]

    # Event banner allowed formats
    EVENT_BANNERS = [
        MimeTypes.IMAGE_JPEG,
        MimeTypes.IMAGE_JPG,
        MimeTypes.IMAGE_PNG,
        MimeTypes.IMAGE_WEBP,
    ]

    # Gallery image allowed formats
    GALLERY_IMAGES = [
        MimeTypes.IMAGE_JPEG,
        MimeTypes.IMAGE_JPG,
        MimeTypes.IMAGE_PNG,
        MimeTypes.IMAGE_WEBP,
    ]

    # Certificate formats
    CERTIFICATES = [
        MimeTypes.APPLICATION_PDF,
        MimeTypes.IMAGE_PNG,
        MimeTypes.IMAGE_JPEG,
    ]

    # Document uploads
    DOCUMENTS = [
        MimeTypes.APPLICATION_PDF,
        MimeTypes.APPLICATION_DOC,
        MimeTypes.APPLICATION_DOCX,
    ]

    # CSV imports
    CSV_FILES = [
        MimeTypes.TEXT_CSV,
        MimeTypes.APPLICATION_OCTET_STREAM,  # Some browsers send CSV as this
    ]


class FileExtensions:
    """File extension mappings to MIME types."""

    EXTENSION_TO_MIME = {
        ".jpg": MimeTypes.IMAGE_JPEG,
        ".jpeg": MimeTypes.IMAGE_JPEG,
        ".png": MimeTypes.IMAGE_PNG,
        ".gif": MimeTypes.IMAGE_GIF,
        ".webp": MimeTypes.IMAGE_WEBP,
        ".svg": MimeTypes.IMAGE_SVG,
        ".pdf": MimeTypes.APPLICATION_PDF,
        ".json": MimeTypes.APPLICATION_JSON,
        ".csv": MimeTypes.TEXT_CSV,
        ".txt": MimeTypes.TEXT_PLAIN,
        ".html": MimeTypes.TEXT_HTML,
        ".css": MimeTypes.TEXT_CSS,
        ".doc": MimeTypes.APPLICATION_DOC,
        ".docx": MimeTypes.APPLICATION_DOCX,
        ".xls": MimeTypes.APPLICATION_XLS,
        ".xlsx": MimeTypes.APPLICATION_XLSX,
        ".zip": MimeTypes.APPLICATION_ZIP,
        ".mp4": MimeTypes.VIDEO_MP4,
        ".mp3": MimeTypes.AUDIO_MP3,
    }

    MIME_TO_EXTENSION = {v: k for k, v in EXTENSION_TO_MIME.items()}


def get_mime_type(filename: str) -> str:
    """
    Get MIME type from filename.

    Args:
        filename: The filename to check

    Returns:
        MIME type string or application/octet-stream if unknown
    """
    import os

    ext = os.path.splitext(filename)[1].lower()
    return FileExtensions.EXTENSION_TO_MIME.get(ext, MimeTypes.APPLICATION_OCTET_STREAM)


def get_file_extension(mime_type: str) -> str:
    """
    Get file extension from MIME type.

    Args:
        mime_type: The MIME type to check

    Returns:
        File extension string or empty string if unknown
    """
    return FileExtensions.MIME_TO_EXTENSION.get(mime_type, "")


def is_valid_mime_type(mime_type: str, allowed_types: list[str]) -> bool:
    """
    Check if MIME type is in allowed list.

    Args:
        mime_type: The MIME type to validate
        allowed_types: List of allowed MIME types

    Returns:
        True if mime_type is in allowed_types, False otherwise
    """
    return mime_type in allowed_types
