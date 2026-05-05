"""
Certificate API Endpoints

Handles e-certificate generation and retrieval for completed race participants.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.certificate_service import CertificateService
from app.modules.registrations.domain.registration import Registration
from app.models.user_reward import UserReward, RewardType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/certificates", tags=["certificates"])


@router.get("/registration/{registration_id}")
async def get_certificate(
    registration_id: int,
    force_regenerate: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get or generate certificate for a registration.

    NOTE: This endpoint does NOT track downloads. Use /download endpoint for tracking.
    This is useful for previewing certificate without consuming download count.

    Args:
        registration_id: ID of the registration
        force_regenerate: Force regenerate even if certificate exists (default: False)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with certificate_url, certificate_number, and generation status

    Raises:
        404: Registration not found
        403: User not authorized
        400: Registration not completed yet
    """
    logger.info(f"Certificate preview request for registration_id={registration_id} by user_id={current_user.id}")

    # Verify registration exists
    registration = db.query(Registration).filter(
        Registration.id == registration_id
    ).first()

    if not registration:
        logger.warning(f"Registration {registration_id} not found")
        raise HTTPException(status_code=404, detail="Registration not found")

    # Verify user owns this registration or is admin
    if registration.user_id != current_user.id and not current_user.is_admin:
        logger.warning(
            f"User {current_user.id} attempted to access certificate for registration {registration_id} "
            f"owned by user {registration.user_id}"
        )
        raise HTTPException(status_code=403, detail="Not authorized to access this certificate")

    # Generate or retrieve certificate
    certificate_service = CertificateService()

    try:
        certificate_url = certificate_service.generate_certificate(
            registration_id=registration_id,
            force_regenerate=force_regenerate,
            db=db
        )

        # Get certificate info from reward record
        reward = db.query(UserReward).filter(
            UserReward.registration_id == registration_id,
            UserReward.reward_type == RewardType.CERTIFICATE
        ).first()

        logger.info(f"Certificate preview delivered for registration_id={registration_id}")

        return {
            'certificate_url': certificate_url,
            'certificate_number': reward.certificate_number if reward else None,
            'registration_id': registration_id,
            'generated': True,
            'cached': not force_regenerate,
            'download_count': reward.download_count if reward else 0,
            'download_limit': reward.download_limit if reward else 10,
            'remaining_downloads': (reward.download_limit - reward.download_count) if reward and reward.download_limit > 0 else -1,
            'preview_mode': True,
            'message': 'Preview mode - use /download endpoint to track downloads'
        }

    except ValueError as e:
        logger.error(f"Certificate generation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during certificate generation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate certificate")


@router.get("/registration/{registration_id}/download")
async def download_certificate(
    registration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download certificate with tracking and limit enforcement.

    This endpoint:
    - Tracks download count
    - Enforces download limits
    - Returns download statistics
    - Admins bypass download limits

    Args:
        registration_id: ID of the registration
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with certificate_url and download statistics

    Raises:
        404: Registration not found
        403: User not authorized
        429: Download limit exceeded
    """
    logger.info(f"Certificate download request for registration_id={registration_id} by user_id={current_user.id}")

    # Verify registration exists and ownership
    registration = db.query(Registration).filter(
        Registration.id == registration_id
    ).first()

    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")

    if registration.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    certificate_service = CertificateService()

    try:
        # Admins bypass download tracking
        if current_user.is_admin:
            logger.info(f"Admin download - bypassing limit for registration_id={registration_id}")
            certificate_url = certificate_service.generate_certificate(
                registration_id=registration_id,
                force_regenerate=False,
                db=db
            )
            return {
                'certificate_url': certificate_url,
                'admin_download': True,
                'message': 'Admin download - limits not applied'
            }

        # Track download for regular users
        result = certificate_service.track_certificate_download(
            registration_id=registration_id,
            user_id=current_user.id,
            db=db
        )

        remaining_msg = f"You have {result['remaining_downloads']} downloads remaining" if result['remaining_downloads'] >= 0 else "Unlimited downloads"

        logger.info(
            f"Certificate downloaded: registration_id={registration_id}, "
            f"downloads={result['download_count']}/{result['download_limit']}"
        )

        return {
            **result,
            'message': remaining_msg
        }

    except ValueError as e:
        error_msg = str(e)
        if "limit exceeded" in error_msg.lower():
            logger.warning(f"Download limit exceeded for registration_id={registration_id}")
            raise HTTPException(status_code=429, detail=error_msg)
        else:
            logger.error(f"Certificate download failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"Unexpected error during certificate download: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download certificate")


@router.post("/registration/{registration_id}/regenerate")
async def regenerate_certificate(
    registration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Force regenerate certificate (e.g., after template update).

    - Requires user to own the registration or be admin
    - Always generates a new certificate regardless of cache

    Args:
        registration_id: ID of the registration
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with certificate_url and regeneration status

    Raises:
        404: Registration not found
        403: User not authorized
        400: Registration not completed yet
    """
    logger.info(f"Certificate regeneration request for registration_id={registration_id} by user_id={current_user.id}")

    # Verify registration exists
    registration = db.query(Registration).filter(
        Registration.id == registration_id
    ).first()

    if not registration:
        logger.warning(f"Registration {registration_id} not found")
        raise HTTPException(status_code=404, detail="Registration not found")

    # Verify user owns this registration or is admin
    if registration.user_id != current_user.id and not current_user.is_admin:
        logger.warning(
            f"User {current_user.id} attempted to regenerate certificate for registration {registration_id}"
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    # Force regenerate certificate
    certificate_service = CertificateService()

    try:
        certificate_url = certificate_service.generate_certificate(
            registration_id=registration_id,
            force_regenerate=True,
            db=db
        )

        logger.info(f"Certificate regenerated successfully for registration_id={registration_id}")

        return {
            'certificate_url': certificate_url,
            'registration_id': registration_id,
            'regenerated': True
        }

    except ValueError as e:
        logger.error(f"Certificate regeneration failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during certificate regeneration: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to regenerate certificate")


@router.get("/my-certificates")
async def get_my_certificates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all certificates for the current user.

    - Returns list of all certificates earned by the user
    - Includes certificate URL, event details, and certificate number

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with list of certificates
    """
    logger.info(f"Fetching all certificates for user_id={current_user.id}")

    # Query all certificate rewards for user
    rewards = db.query(UserReward).filter(
        UserReward.user_id == current_user.id,
        UserReward.reward_type == RewardType.CERTIFICATE,
        UserReward.certificate_url.isnot(None)
    ).all()

    certificates = []
    for reward in rewards:
        certificates.append({
            'id': reward.id,
            'event_name': reward.event.name if reward.event else "Unknown Event",
            'event_id': reward.event_id,
            'certificate_url': reward.certificate_url,
            'certificate_number': reward.certificate_number,
            'awarded_at': reward.awarded_at.isoformat() if reward.awarded_at else None,
            'delivered_at': reward.delivered_at.isoformat() if reward.delivered_at else None,
            'registration_id': reward.registration_id,
            'download_count': reward.download_count or 0,
            'download_limit': reward.download_limit or 10,
            'remaining_downloads': (reward.download_limit - reward.download_count) if reward.download_limit > 0 else -1
        })

    logger.info(f"Found {len(certificates)} certificates for user_id={current_user.id}")

    return {
        'certificates': certificates,
        'total': len(certificates)
    }


@router.post("/events/{event_id}/bulk-generate")
async def bulk_generate_certificates(
    event_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Generate certificates for all completed participants.

    - Requires admin privileges
    - Processes synchronously in Phase 1 (will be async in Phase 3)
    - Returns generation statistics

    Args:
        event_id: ID of the event
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user (must be admin)
        db: Database session

    Returns:
        Dict with generation statistics

    Raises:
        403: User not admin
        404: Event not found
    """
    logger.info(f"Bulk certificate generation request for event_id={event_id} by user_id={current_user.id}")

    # Verify user is admin
    if not current_user.is_admin:
        logger.warning(f"Non-admin user {current_user.id} attempted bulk certificate generation")
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Verify event exists
    from app.models.event import Event
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        logger.warning(f"Event {event_id} not found")
        raise HTTPException(status_code=404, detail="Event not found")

    # Generate certificates (synchronous in Phase 1)
    certificate_service = CertificateService()

    try:
        result = certificate_service.bulk_generate_certificates(event_id, db)

        logger.info(
            f"Bulk generation completed for event_id={event_id}: "
            f"{result['successful']}/{result['total_certificates']} successful"
        )

        return {
            'message': 'Bulk certificate generation completed',
            'event_id': event_id,
            'event_name': event.name,
            **result
        }

    except Exception as e:
        logger.error(f"Bulk certificate generation failed for event_id={event_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Bulk generation failed")


@router.get("/event/{event_id}/statistics")
async def get_certificate_statistics(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get certificate generation statistics for an event.

    - Requires admin or event organizer
    - Shows how many certificates generated vs eligible

    Args:
        event_id: ID of the event
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with certificate statistics

    Raises:
        403: User not authorized
        404: Event not found
    """
    logger.info(f"Certificate statistics request for event_id={event_id} by user_id={current_user.id}")

    # Verify event exists
    from app.models.event import Event
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        logger.warning(f"Event {event_id} not found")
        raise HTTPException(status_code=404, detail="Event not found")

    # Verify user is admin or event organizer
    if not current_user.is_admin and event.organizer_id != current_user.id:
        logger.warning(
            f"User {current_user.id} attempted to view statistics for event {event_id} "
            f"organized by user {event.organizer_id}"
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    # Count completed registrations
    from app.models.activity_progress import ActivityProgress
    completed_count = db.query(Registration).join(
        ActivityProgress
    ).filter(
        Registration.event_id == event_id,
        ActivityProgress.is_completed == True
    ).count()

    # Count generated certificates
    generated_count = db.query(UserReward).filter(
        UserReward.event_id == event_id,
        UserReward.reward_type == RewardType.CERTIFICATE,
        UserReward.certificate_url.isnot(None)
    ).count()

    # Count total registrations
    total_registrations = db.query(Registration).filter(
        Registration.event_id == event_id
    ).count()

    statistics = {
        'event_id': event_id,
        'event_name': event.name,
        'total_registrations': total_registrations,
        'completed_participants': completed_count,
        'certificates_generated': generated_count,
        'pending_generation': completed_count - generated_count,
        'completion_rate': f"{(completed_count / total_registrations * 100):.1f}%" if total_registrations > 0 else "0%",
        'certificate_claim_rate': f"{(generated_count / completed_count * 100):.1f}%" if completed_count > 0 else "0%"
    }

    logger.info(f"Certificate statistics for event_id={event_id}: {generated_count}/{completed_count} generated")

    return statistics


# ============================================================================
# ADMIN ENDPOINTS - Download Limit Management
# ============================================================================

@router.patch("/registration/{registration_id}/download-limit")
async def update_download_limit(
    registration_id: int,
    new_limit: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Update download limit for a specific certificate.

    Set limit to 0 for unlimited downloads.

    Args:
        registration_id: ID of the registration
        new_limit: New download limit (0 = unlimited)
        current_user: Current authenticated user (must be admin)
        db: Database session

    Returns:
        Dict with updated limit information

    Raises:
        403: User not admin
        404: Certificate not found
    """
    if not current_user.is_admin:
        logger.warning(f"Non-admin user {current_user.id} attempted to update download limit")
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Get reward record
    reward = db.query(UserReward).filter(
        UserReward.registration_id == registration_id,
        UserReward.reward_type == RewardType.CERTIFICATE
    ).first()

    if not reward:
        raise HTTPException(status_code=404, detail="Certificate not found")

    old_limit = reward.download_limit
    reward.download_limit = new_limit
    db.commit()

    logger.info(
        f"Admin {current_user.id} updated download limit for registration {registration_id}: "
        f"{old_limit} → {new_limit}"
    )

    remaining = new_limit - reward.download_count if new_limit > 0 else -1

    return {
        'registration_id': registration_id,
        'certificate_number': reward.certificate_number,
        'old_limit': old_limit,
        'new_limit': new_limit,
        'download_count': reward.download_count,
        'remaining_downloads': remaining,
        'message': f'Download limit updated from {old_limit} to {new_limit}'
    }


@router.post("/registration/{registration_id}/reset-downloads")
async def reset_download_count(
    registration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Reset download count for a certificate.

    Useful when user reports issues or genuinely needs extra downloads.

    Args:
        registration_id: ID of the registration
        current_user: Current authenticated user (must be admin)
        db: Database session

    Returns:
        Dict with reset confirmation

    Raises:
        403: User not admin
        404: Certificate not found
    """
    if not current_user.is_admin:
        logger.warning(f"Non-admin user {current_user.id} attempted to reset download count")
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Get reward record
    reward = db.query(UserReward).filter(
        UserReward.registration_id == registration_id,
        UserReward.reward_type == RewardType.CERTIFICATE
    ).first()

    if not reward:
        raise HTTPException(status_code=404, detail="Certificate not found")

    old_count = reward.download_count
    reward.download_count = 0
    reward.last_downloaded_at = None
    db.commit()

    logger.info(
        f"Admin {current_user.id} reset download count for registration {registration_id}: "
        f"{old_count} → 0"
    )

    return {
        'registration_id': registration_id,
        'certificate_number': reward.certificate_number,
        'old_count': old_count,
        'new_count': 0,
        'download_limit': reward.download_limit,
        'remaining_downloads': reward.download_limit,
        'message': f'Download count reset from {old_count} to 0'
    }


@router.patch("/events/{event_id}/default-download-limit")
async def set_event_download_limit(
    event_id: int,
    default_limit: int,
    apply_to_existing: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Set default download limit for all certificates in an event.

    Args:
        event_id: ID of the event
        default_limit: New default download limit (0 = unlimited)
        apply_to_existing: If True, update existing certificates (default: False)
        current_user: Current authenticated user (must be admin)
        db: Database session

    Returns:
        Dict with update summary

    Raises:
        403: User not admin
        404: Event not found
    """
    if not current_user.is_admin:
        logger.warning(f"Non-admin user {current_user.id} attempted to set event download limit")
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Verify event exists
    from app.models.event import Event
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    updated_count = 0

    if apply_to_existing:
        # Update all existing certificates for this event
        updated_count = db.query(UserReward).filter(
            UserReward.event_id == event_id,
            UserReward.reward_type == RewardType.CERTIFICATE
        ).update({'download_limit': default_limit})
        db.commit()

    logger.info(
        f"Admin {current_user.id} set download limit for event {event_id} to {default_limit}. "
        f"Updated {updated_count} existing certificates."
    )

    return {
        'event_id': event_id,
        'event_name': event.name,
        'default_download_limit': default_limit,
        'certificates_updated': updated_count,
        'applied_to_existing': apply_to_existing,
        'message': f'Set default limit to {default_limit}' + (f', updated {updated_count} existing certificates' if apply_to_existing else ' (will apply to new certificates only)')
    }


@router.get("/download-analytics")
async def get_download_analytics(
    event_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Get download analytics across all certificates or for specific event.

    Args:
        event_id: Optional event ID to filter by
        current_user: Current authenticated user (must be admin)
        db: Database session

    Returns:
        Dict with download analytics

    Raises:
        403: User not admin
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Build base query
    query = db.query(UserReward).filter(
        UserReward.reward_type == RewardType.CERTIFICATE,
        UserReward.certificate_url.isnot(None)
    )

    if event_id:
        query = query.filter(UserReward.event_id == event_id)

    rewards = query.all()

    if not rewards:
        return {
            'total_certificates': 0,
            'analytics': {}
        }

    # Calculate analytics
    total_downloads = sum(r.download_count or 0 for r in rewards)
    avg_downloads = total_downloads / len(rewards) if rewards else 0

    # Download distribution
    download_buckets = {
        '0': 0,
        '1-5': 0,
        '6-10': 0,
        '11-20': 0,
        '21+': 0
    }

    limits_exceeded = 0

    for reward in rewards:
        count = reward.download_count or 0
        limit = reward.download_limit or 10

        # Bucket
        if count == 0:
            download_buckets['0'] += 1
        elif count <= 5:
            download_buckets['1-5'] += 1
        elif count <= 10:
            download_buckets['6-10'] += 1
        elif count <= 20:
            download_buckets['11-20'] += 1
        else:
            download_buckets['21+'] += 1

        # Check if limit exceeded
        if limit > 0 and count >= limit:
            limits_exceeded += 1

    analytics = {
        'total_certificates': len(rewards),
        'total_downloads': total_downloads,
        'average_downloads_per_certificate': round(avg_downloads, 2),
        'download_distribution': download_buckets,
        'certificates_at_limit': limits_exceeded,
        'limit_exceeded_rate': f"{(limits_exceeded / len(rewards) * 100):.1f}%"
    }

    if event_id:
        from app.models.event import Event
        event = db.query(Event).filter(Event.id == event_id).first()
        analytics['event_name'] = event.name if event else "Unknown"

    logger.info(f"Admin {current_user.id} viewed download analytics" + (f" for event {event_id}" if event_id else ""))

    return analytics
