"""
Certificates API Endpoints

RESTful endpoints for certificate generation and download.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.modules.certificates.services.certificate_service import CertificateService
from app.modules.certificates.schemas.certificate import (
    CertificateResponse,
    CertificateListResponse,
)
from app.core.exceptions import (
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from app.core.rate_limit import limiter, RateLimits

router = APIRouter(
    prefix="/api/v1/certificates",
    tags=["Certificates"],
)


@router.get("/registration/{registration_id}", response_model=CertificateResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_certificate(
    request: Request,
    response: Response,
    registration_id: int,
    force_regenerate: bool = Query(False, description="Force regenerate certificate"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get or generate certificate for registration.

    This endpoint previews the certificate without tracking downloads.
    """
    service = CertificateService(db)

    try:
        cert_url = service.generate_certificate(
            registration_id=registration_id,
            force_regenerate=force_regenerate
        )

        cert = service.get_certificate(registration_id)

        return CertificateResponse(
            certificate_url=cert_url,
            certificate_number=cert.certificate_number,
            download_count=cert.download_count or 0,
            last_downloaded_at=cert.last_downloaded_at,
            created_at=cert.created_at
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/registration/{registration_id}/download", response_model=CertificateResponse)
@limiter.limit(RateLimits.DEFAULT)
async def download_certificate(
    request: Request,
    response: Response,
    registration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download certificate and track download count.

    Business Rules:
    - Only owner can download
    - Download count incremented
    """
    service = CertificateService(db)

    try:
        cert = service.track_download(
            registration_id=registration_id,
            user_id=current_user.id
        )

        return CertificateResponse.model_validate(cert)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionDeniedException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/my-certificates", response_model=CertificateListResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_my_certificates(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all certificates for current user."""
    service = CertificateService(db)

    certificates = service.get_user_certificates(current_user.id)

    return CertificateListResponse(
        certificates=[CertificateResponse.model_validate(c) for c in certificates],
        total=len(certificates)
    )
