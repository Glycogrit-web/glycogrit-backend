"""
Certificate Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CertificateResponse(BaseModel):
    """Certificate response schema"""
    certificate_url: str
    certificate_number: str
    download_count: int
    last_downloaded_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "certificate_url": "https://certificates.glycogrit.com/CERT-123-456.pdf",
                "certificate_number": "CERT-123-456",
                "download_count": 5,
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
