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
from app.modules.registrations.domain.registration import Registration
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

        remaining = None
        if cert.download_limit:
            remaining = max(0, cert.download_limit - (cert.download_count or 0))

        return CertificateResponse(
            certificate_url=cert_data["certificate_url"],
            certificate_number=cert_data["certificate_number"],
            download_count=cert.download_count or 0,
            download_limit=cert.download_limit,
            remaining_downloads=remaining,
            last_downloaded_at=cert.last_downloaded_at,
            created_at=cert.created_at,
            preview_mode=True,
            message="Certificate preview - use /download endpoint to track downloads"
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
        is_admin = current_user.role == "admin"
        cert = service.track_download(
            registration_id=registration_id,
            user_id=current_user.id,
            is_admin=is_admin
        )

        remaining = None
        download_limit = getattr(cert, 'download_limit', None)
        download_count = getattr(cert, 'download_count', 0) or 0

        if download_limit:
            remaining = max(0, download_limit - download_count)

        message = None
        admin_download = None
        if is_admin:
            admin_download = True
            message = "Admin download - limits not applied"
        elif remaining is not None:
            message = f"{remaining} downloads remaining"

        return CertificateResponse(
            certificate_url=getattr(cert, 'certificate_url', ''),
            certificate_number=getattr(cert, 'certificate_number', ''),
            download_count=download_count,
            download_limit=download_limit,
            remaining_downloads=remaining,
            last_downloaded_at=getattr(cert, 'last_downloaded_at', None),
            created_at=getattr(cert, 'created_at', None),
            message=message,
            admin_download=admin_download
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionDeniedException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        # Download limit exceeded
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))


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

    cert_responses = []
    for c in certificates:
        remaining = None
        if c.download_limit:
            remaining = max(0, c.download_limit - (c.download_count or 0))

        cert_responses.append(CertificateResponse(
            certificate_url=c.certificate_url,
            certificate_number=c.certificate_number,
            download_count=c.download_count or 0,
            download_limit=c.download_limit,
            remaining_downloads=remaining,
            last_downloaded_at=c.last_downloaded_at,
            created_at=c.created_at
        ))

    return CertificateListResponse(
        certificates=cert_responses,
        total=len(cert_responses)
    )


# Admin endpoints
@router.patch("/registration/{registration_id}/download-limit")
@limiter.limit(RateLimits.DEFAULT)
async def update_download_limit(
    request: Request,
    response: Response,
    registration_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: Update download limit for a certificate."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    new_limit = body.get("new_limit")
    if new_limit is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="new_limit is required")

    service = CertificateService(db)
    cert = service.get_certificate(registration_id)

    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    old_limit = cert.download_limit
    cert.download_limit = new_limit
    db.commit()
    db.refresh(cert)

    return {
        "message": "Download limit updated successfully",
        "old_limit": old_limit,
        "new_limit": new_limit
    }


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

    old_count = cert.download_count or 0
    cert.download_count = 0
    cert.last_downloaded_at = None
    db.commit()

    return {
        "message": "Download count reset successfully",
        "old_count": old_count,
        "new_count": 0
    }


@router.patch("/events/{event_id}/default-download-limit")
@limiter.limit(RateLimits.DEFAULT)
async def set_event_default_limit(
    request: Request,
    response: Response,
    event_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: Set default download limit for an event."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    default_limit = body.get("default_limit")
    apply_to_existing = body.get("apply_to_existing", False)

    if default_limit is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="default_limit is required")

    from app.models.user_reward import UserReward, RewardType

    # Update existing certificates if requested
    certificates_updated = 0
    if apply_to_existing:
        certs = db.query(UserReward).filter(
            UserReward.event_id == event_id,
            UserReward.reward_type == RewardType.CERTIFICATE
        ).all()

        for cert in certs:
            cert.download_limit = default_limit
            certificates_updated += 1

        db.commit()

    return {
        "default_download_limit": default_limit,
        "applied_to_existing": apply_to_existing,
        "certificates_updated": certificates_updated
    }


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
    from app.modules.events.domain.event import Event

    query = db.query(UserReward).filter(UserReward.reward_type == RewardType.CERTIFICATE)

    event_name = None
    if event_id:
        query = query.filter(UserReward.event_id == event_id)
        event = db.query(Event).filter(Event.id == event_id).first()
        if event:
            event_name = event.name

    certs = query.all()
    total_certs = len(certs)
    total_downloads = sum(c.download_count or 0 for c in certs)
    avg_downloads = total_downloads / total_certs if total_certs else 0

    # Calculate download distribution
    download_counts = [c.download_count or 0 for c in certs]
    distribution = {}
    for count in download_counts:
        distribution[str(count)] = distribution.get(str(count), 0) + 1

    # Calculate certificates at limit and limit exceeded rate
    certs_at_limit = sum(1 for c in certs if c.download_limit and c.download_count >= c.download_limit)
    limit_exceeded_rate = (certs_at_limit / total_certs * 100) if total_certs else 0

    result = {
        "total_certificates": total_certs,
        "total_downloads": total_downloads,
        "average_downloads_per_certificate": avg_downloads,
        "download_distribution": distribution,
        "certificates_at_limit": certs_at_limit,
        "limit_exceeded_rate": limit_exceeded_rate,
        "certificates": [CertificateResponse.model_validate(c) for c in certs]
    }

    if event_name:
        result["event_name"] = event_name

    return result
