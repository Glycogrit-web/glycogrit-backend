"""
Certificates API Endpoints

RESTful endpoints for certificate generation and download.
"""

from typing import Optional
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
    prefix="/certificates",
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
    # Check ownership first
    registration = db.query(Registration).filter(
        Registration.id == registration_id
    ).first()

    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    if registration.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this certificate")

    service = CertificateService(db)

    try:
        cert_data = service.generate_certificate(
            registration_id=registration_id,
            force_regenerate=force_regenerate
        )

        cert = service.get_certificate(registration_id)

        return CertificateResponse(
            certificate_url=cert_data["certificate_url"],
            certificate_number=cert_data["certificate_number"],
            download_count=cert.download_count or 0,
            last_downloaded_at=cert.last_downloaded_at,
            created_at=cert.created_at
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/registration/{registration_id}/download", response_model=CertificateResponse)
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


# Admin endpoints
@router.patch("/registration/{registration_id}/download-limit")
@limiter.limit(RateLimits.DEFAULT)
async def update_download_limit(
    request: Request,
    response: Response,
    registration_id: int,
    download_limit: int = Query(..., description="New download limit (0 for unlimited)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: Update download limit for a certificate."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    service = CertificateService(db)
    cert = service.get_certificate(registration_id)

    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    cert.download_limit = download_limit
    db.commit()
    db.refresh(cert)

    return CertificateResponse.model_validate(cert)


@router.post("/registration/{registration_id}/reset-downloads")
@limiter.limit(RateLimits.DEFAULT)
async def reset_download_count(
    request: Request,
    response: Response,
    registration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: Reset download count for a certificate."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    service = CertificateService(db)
    cert = service.get_certificate(registration_id)

    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    cert.download_count = 0
    cert.last_downloaded_at = None
    db.commit()

    return {"message": "Download count reset successfully", "registration_id": registration_id}


@router.get("/download-analytics")
@limiter.limit(RateLimits.DEFAULT)
async def get_download_analytics(
    request: Request,
    response: Response,
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: Get certificate download analytics."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    from app.models.user_reward import UserReward, RewardType

    query = db.query(UserReward).filter(UserReward.reward_type == RewardType.CERTIFICATE)

    if event_id:
        query = query.filter(UserReward.event_id == event_id)

    certs = query.all()

    return {
        "total_certificates": len(certs),
        "total_downloads": sum(c.download_count or 0 for c in certs),
        "avg_downloads": sum(c.download_count or 0 for c in certs) / len(certs) if certs else 0,
        "certificates": [CertificateResponse.model_validate(c) for c in certs]
    }
