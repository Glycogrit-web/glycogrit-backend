"""
Certificates Module - Domain-Driven Design

E-certificate generation and management for completed participants.

Public API:
    Domain:
        - UserReward: Certificate storage model
        - RewardType: Certificate type enum

    Value Objects:
        - CertificateNumber: Unique identifier
        - CertificateUrl: Certificate file URL
        - DownloadCount: Download tracking

    Services:
        - CertificateService: Certificate operations

    API:
        - certificates_router: Certificate endpoints
"""

from app.models.user_reward import RewardType, UserReward
from app.modules.certificates.api.certificates import router as certificates_router
from app.modules.certificates.domain.value_objects import (
    CertificateNumber,
    CertificateUrl,
    DownloadCount,
)
from app.modules.certificates.services.certificate_service import CertificateService

__all__ = [
    "UserReward",
    "RewardType",
    "CertificateNumber",
    "CertificateUrl",
    "DownloadCount",
    "CertificateService",
    "certificates_router",
]
