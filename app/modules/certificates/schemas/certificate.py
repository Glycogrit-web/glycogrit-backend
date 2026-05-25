"""
Certificate Schemas
"""

from datetime import datetime

from pydantic import BaseModel


class CertificateResponse(BaseModel):
    """Certificate response schema"""
    certificate_url: str
    certificate_number: str
    download_count: int
    download_limit: int | None = None
    remaining_downloads: int | None = None
    last_downloaded_at: datetime | None = None
    created_at: datetime
    preview_mode: bool | None = None
    message: str | None = None
    admin_download: bool | None = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "certificate_url": "https://certificates.glycogrit.com/CERT-123-456.pdf",
                "certificate_number": "CERT-123-456",
                "download_count": 5,
                "download_limit": 10,
                "remaining_downloads": 5,
                "last_downloaded_at": "2024-01-15T10:30:00",
                "created_at": "2024-01-10T08:00:00"
            }
        }


class CertificateListResponse(BaseModel):
    """List of certificates"""
    certificates: list[CertificateResponse]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "certificates": [],
                "total": 3
            }
        }
