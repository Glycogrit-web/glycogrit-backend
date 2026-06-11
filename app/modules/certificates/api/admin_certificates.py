"""
Admin Certificate Management Endpoints
For bulk certificate upload and unlocking via CSV
"""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.rate_limit import RateLimits, limiter
from app.models.user import User
from app.modules.certificates.services.csv_processor_service import CSVProcessorService
from app.modules.certificates.services.google_drive_service import GoogleDriveService
from app.modules.registrations.domain.registration import Registration

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/certificates",
    tags=["Admin - Certificates"],
)


class BulkUnlockRequest(BaseModel):
    """Request to unlock certificates for registrations"""
    registration_ids: list[int]


class UpdateCertificateUrlRequest(BaseModel):
    """Request to update or delete certificate URL"""
    certificate_url: str | None = None


class CSVUploadResponse(BaseModel):
    """Response from CSV upload"""
    message: str
    total_rows: int
    successful: int
    failed: int
    not_found: int
    already_has_certificate: int
    errors: list[str]


class RegistrationCertificateInfo(BaseModel):
    """Registration info for certificate management"""
    id: int
    registration_number: str
    participant_name: str
    user_email: str | None
    external_certificate_url: str | None
    external_certificate_unlocked: bool
    external_certificate_uploaded_at: str | None


@router.post("/events/{event_id}/upload-csv", response_model=CSVUploadResponse)
@limiter.limit(RateLimits.DEFAULT)
async def upload_certificate_csv(
    request: Request,
    response: Response,
    event_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload CSV or XLSX with certificate URLs from Autocrat

    Supports:
    - CSV files (.csv)
    - Excel files (.xlsx) with optional sheet_name parameter
    - Multiple sheets (will use first sheet if sheet_name not provided)
    - Flexible column names (e.g., "Merged Doc URL - Auto Certificate", "Link to merged Doc - Auto Certificate")

    Required columns (flexible matching):
    - email (exact match)
    - Certificate URL column (matches patterns: "merged doc url", "link to merged", "certificate url")

    Optional columns:
    - distance, sport/activity_type

    Admin only endpoint for bulk certificate distribution
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Validate file type (CSV or XLSX)
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )

    filename_lower = file.filename.lower()
    is_xlsx = filename_lower.endswith('.xlsx') or filename_lower.endswith('.xls')
    is_csv = filename_lower.endswith('.csv')

    if not (is_csv or is_xlsx):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be CSV (.csv) or Excel (.xlsx/.xls)"
        )

    # Validate file size (10MB max)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 10MB)"
        )

    # Read file content and convert to CSV
    service = CSVProcessorService(db)
    try:
        if is_xlsx:
            # Convert XLSX to CSV (uses first sheet by default)
            csv_content = service.convert_xlsx_to_csv(content)
        else:
            # Read CSV directly
            csv_content = content.decode('utf-8')

        # Process CSV
        stats = service.process_certificate_csv(
            csv_content=csv_content,
            event_id=event_id,
            uploaded_by_admin_id=current_user.id
        )

        return CSVUploadResponse(
            message=f"{'Excel' if is_xlsx else 'CSV'} file processed successfully",
            **stats
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )


@router.post("/events/{event_id}/unlock-certificates")
@limiter.limit(RateLimits.DEFAULT)
async def unlock_certificates(
    request: Request,
    response: Response,
    event_id: int,
    body: BulkUnlockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unlock certificates for users to download

    Admin must explicitly unlock after verifying certificate quality.
    Locked certificates cannot be downloaded by users.
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Update registrations
    updated_count = 0
    for reg_id in body.registration_ids:
        registration = db.query(Registration).filter(
            Registration.id == reg_id,
            Registration.event_id == event_id
        ).first()

        if registration and registration.external_certificate_url:
            registration.external_certificate_unlocked = True
            updated_count += 1

    db.commit()

    return {
        "message": f"Unlocked {updated_count} certificates",
        "unlocked_count": updated_count,
        "requested_count": len(body.registration_ids)
    }


@router.patch("/registrations/{registration_id}/toggle-unlock")
@limiter.limit(RateLimits.DEFAULT)
async def toggle_certificate_unlock(
    request: Request,
    response: Response,
    registration_id: int,
    unlock: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Toggle certificate unlock status for a single registration

    This endpoint is used for inline table actions in EventParticipantsWithProgress.
    Admins can click the lock icon to unlock (or relock) individual certificates.

    Args:
        registration_id: ID of the registration
        unlock: True to unlock, False to lock
        current_user: Authenticated user (must be admin)
        db: Database session

    Returns:
        {
            "success": True,
            "registration_id": int,
            "unlocked": bool,
            "certificate_url": str
        }

    Raises:
        403: If user is not admin
        404: If registration not found
        400: If no certificate uploaded for registration
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Get registration
    registration = db.query(Registration).filter(
        Registration.id == registration_id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )

    # Check if certificate exists
    if not registration.external_certificate_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No certificate uploaded for this registration"
        )

    # Update unlock status
    registration.external_certificate_unlocked = unlock
    db.commit()
    db.refresh(registration)

    logger.info(
        f"📝 Admin {current_user.email} {'unlocked' if unlock else 'locked'} certificate for registration {registration_id}"
    )

    return {
        "success": True,
        "registration_id": registration_id,
        "unlocked": unlock,
        "certificate_url": registration.external_certificate_url
    }


@router.patch("/registrations/{registration_id}/update-url")
@limiter.limit(RateLimits.DEFAULT)
async def update_certificate_url(
    request: Request,
    response: Response,
    registration_id: int,
    body: UpdateCertificateUrlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update or delete certificate URL for a single registration

    This endpoint allows admins to manually add/edit/remove certificate URLs
    inline in the EventParticipantsWithProgress table.

    Args:
        registration_id: ID of the registration
        body: Request body with certificate_url (or null to delete)
        current_user: Authenticated user (must be admin)
        db: Database session

    Returns:
        {
            "success": True,
            "registration_id": int,
            "certificate_url": str | None,
            "unlocked": bool,
            "uploaded_at": str | None
        }

    Raises:
        403: If user is not admin
        404: If registration not found
        400: If certificate URL format is invalid
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Get registration
    registration = db.query(Registration).filter(
        Registration.id == registration_id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )

    # Handle delete operation (null URL)
    if body.certificate_url is None:
        registration.external_certificate_url = None
        registration.external_certificate_unlocked = False
        registration.external_certificate_uploaded_at = None
        registration.external_certificate_uploaded_by = None
        registration.external_certificate_distance = None
        registration.external_certificate_activity_type = None

        db.commit()
        db.refresh(registration)

        logger.info(
            f"🗑️  Admin {current_user.email} deleted certificate for registration {registration_id}"
        )

        return {
            "success": True,
            "registration_id": registration_id,
            "certificate_url": None,
            "unlocked": False,
            "uploaded_at": None
        }

    # Validate Google Drive URL format
    drive_service = GoogleDriveService()
    file_id = drive_service.extract_file_id(body.certificate_url)

    if not file_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google Drive URL format. Please provide a valid Google Drive URL (https://drive.google.com/file/d/FILE_ID/view) or file ID."
        )

    # Update certificate URL
    from datetime import datetime
    registration.external_certificate_url = body.certificate_url
    registration.external_certificate_uploaded_at = datetime.utcnow()
    registration.external_certificate_uploaded_by = current_user.id
    # Keep external_certificate_unlocked unchanged - admin can unlock separately

    db.commit()
    db.refresh(registration)

    logger.info(
        f"📝 Admin {current_user.email} updated certificate URL for registration {registration_id}"
    )

    return {
        "success": True,
        "registration_id": registration_id,
        "certificate_url": registration.external_certificate_url,
        "unlocked": registration.external_certificate_unlocked,
        "uploaded_at": registration.external_certificate_uploaded_at.isoformat() if registration.external_certificate_uploaded_at else None
    }


@router.get("/events/{event_id}/registrations-with-certificates")
@limiter.limit(RateLimits.DEFAULT)
async def get_registrations_with_certificates(
    request: Request,
    response: Response,
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all registrations that have external certificates for an event

    Used in admin UI to show certificate unlock status
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    service = CSVProcessorService(db)
    registrations = service.get_registrations_with_certificates(event_id)

    return {
        "registrations": registrations,
        "total": len(registrations)
    }
