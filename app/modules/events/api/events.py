"""
Events API Endpoints
"""

import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_optional_current_user as get_optional_user
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.modules.events.domain.event import Event

# EventActivityService was removed in refactoring - use EventService directly
from app.modules.events.schemas.event import (
    ActivityCreate,
    ActivityResponse,
    ActivityUpdate,
    EventCreate,
    EventResponse,
    EventUpdate,
)
from app.modules.events.services.event_service import ActivityService, EventService
from app.modules.registrations.schemas.tier import (
    TierCreate,
    TierResponse,
    TierUpdate,
)

logger = logging.getLogger(__name__)


class RegisterTierRequest(BaseModel):
    tier_id: int
    activity_id: int | None = None
    participant_name: str
    age: int | None = None
    gender: str | None = None
    t_shirt_size: str | None = None


router = APIRouter(prefix="/events", tags=["events"])


def resolve_event_identifier(event_identifier: str, db: Session) -> int:
    """
    Resolve event slug or numeric ID to numeric event_id.

    Args:
        event_identifier: Event slug (e.g., 'june') or numeric ID (e.g., '31')
        db: Database session

    Returns:
        int: Numeric event ID

    Raises:
        HTTPException 404: If event not found
    """
    service = EventService(db)

    # Try slug lookup first (preferred for clean URLs)
    if not event_identifier.isdigit():
        event = service.get_event_by_slug(event_identifier)
        if event:
            return event.id

    # Try numeric ID lookup (backward compatibility)
    if event_identifier.isdigit():
        event = service.get_event_by_id(int(event_identifier))
        if event:
            return event.id

    # Not found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Event not found: {event_identifier}"
    )
activities_router = APIRouter(prefix="/activities", tags=["activities"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new event (Admin/Organizer only)

    Creates event with:
    - Basic details (name, description, dates)
    - Registration configuration
    - Pricing tiers
    - Activities
    """
    service = EventService(db)
    event = service.create_event(event_data=event_data.model_dump(), organizer_id=current_user.id)
    return EventResponse.model_validate(event)


@router.get("")
def get_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    search: str | None = None,
    is_featured: bool | None = None,
    db: Session = Depends(get_db),
):
    """
    Get all events with pagination metadata

    Returns paginated response with:
    - events: List of events
    - total: Total count of events
    - page: Current page number
    - page_size: Number of items per page

    Optional parameters:
    - search: Filter by name/description
    - is_featured: Filter featured events only
    """
    service = EventService(db)

    # Get events based on filters
    if search:
        events = service.search_events(search_term=search, skip=skip, limit=limit)
        # For search, count all matching results
        all_results = service.search_events(search_term=search, skip=0, limit=99999)
        total = len(all_results)
    elif is_featured is not None:
        # Filter by is_featured flag with eager loading
        from sqlalchemy.orm import joinedload
        query = service.db.query(Event).filter(Event.is_featured == is_featured)
        total = query.count()
        events = query.options(
            joinedload(Event.registration_tiers)
        ).offset(skip).limit(limit).all()
    else:
        events = service.get_all_events(skip=skip, limit=limit)
        total = service.db.query(Event).count()

    return {
        "events": [EventResponse.model_validate(event) for event in events],
        "total": total,
        "page": (skip // limit) + 1 if limit > 0 else 1,
        "page_size": limit,
    }


@router.get("/{event_identifier}", response_model=EventResponse)
def get_event(
    event_identifier: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user)
):
    """
    Get event details by slug or ID with user registration status.

    Accepts both human-readable slug (e.g., 'mumbai-marathon-2024')
    or numeric ID (e.g., '31') for backward compatibility.

    Returns complete event information including:
    - Basic details
    - Activities
    - Tiers with registration counts
    - User's registration status (if authenticated)

    User Registration Status includes:
    - registration_id: ID of user's registration
    - tier_id: Current tier ID
    - tier_name: Current tier name
    - status: 'pending' (payment not completed) or 'confirmed' (paid/free tier)
    - total_amount_paid: Amount user has paid
    - tier_price: Price of current tier
    - payment_complete: Boolean - true if amount paid matches tier price
    - can_register: Boolean - true if user can register for tiers
    - can_upgrade: Boolean - true if user can upgrade to higher tier
    - available_tiers: List of tiers user can register for (excluding current tier)
    """
    service = EventService(db)

    # Try slug first (preferred for clean URLs)
    event = service.get_event_by_slug(event_identifier) if not event_identifier.isdigit() else None

    # Fallback to numeric ID for backward compatibility
    if not event and event_identifier.isdigit():
        event = service.get_event_by_id(int(event_identifier))

    # If still not found, raise 404
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    event_id = event.id
    event_dict = EventResponse.model_validate(event).model_dump()

    # Add user registration status if authenticated
    if current_user:
        from app.modules.registrations.domain.registration import Registration
        from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier as Tier

        # Get user's confirmed registration for this event
        user_registration = db.query(Registration).filter(
            Registration.user_id == current_user.id,
            Registration.event_id == event_id,
            Registration.status == 'confirmed'  # Only confirmed registrations
        ).first()

        if user_registration and user_registration.current_tier_id:
            # User has a confirmed registration
            current_tier = db.query(Tier).filter(
                Tier.id == user_registration.current_tier_id
            ).first()

            if current_tier:
                # Check if payment is complete
                payment_complete = (
                    float(user_registration.total_amount_paid) >= float(current_tier.price)
                )

                # Get available tiers for upgrade (higher tier_order)
                available_upgrades = db.query(Tier).filter(
                    Tier.event_id == event_id,
                    Tier.tier_order > current_tier.tier_order,
                    Tier.is_active == True
                ).order_by(Tier.tier_order).all()

                # Get all active tiers for the event
                all_tiers = db.query(Tier).filter(
                    Tier.event_id == event_id,
                    Tier.is_active == True
                ).order_by(Tier.tier_order).all()

                event_dict["user_registration"] = {
                    "registration_id": user_registration.id,
                    "registration_number": user_registration.registration_number,
                    "tier_id": current_tier.id,
                    "tier_name": current_tier.tier_name,
                    "tier_price": float(current_tier.price),
                    "tier_order": current_tier.tier_order,
                    "tier_rewards": current_tier.rewards or [],
                    "tier_benefits": [],  # benefits field doesn't exist in EventRegistrationTier
                    "status": user_registration.status,
                    "total_amount_paid": float(user_registration.total_amount_paid),
                    "payment_complete": payment_complete,
                    "can_register": False,  # Already registered
                    "can_upgrade": len(available_upgrades) > 0,
                    "available_upgrades": [
                        {
                            "tier_id": tier.id,
                            "tier_name": tier.tier_name,
                            "tier_price": float(tier.price),
                            "tier_rewards": tier.rewards or [],
                            "tier_benefits": [],  # benefits field doesn't exist
                            "upgrade_price": float(tier.price - current_tier.price),
                            "capacity_remaining": tier.max_registrations - tier.current_registrations if tier.max_registrations else None,
                            "is_sold_out": tier.max_registrations is not None and tier.current_registrations >= tier.max_registrations
                        }
                        for tier in available_upgrades
                    ]
                }
        else:
            # User is NOT registered - show all available tiers
            all_tiers = db.query(Tier).filter(
                Tier.event_id == event_id,
                Tier.is_active == True
            ).order_by(Tier.tier_order).all()

            event_dict["user_registration"] = {
                "registration_id": None,
                "tier_id": None,
                "tier_name": None,
                "status": None,
                "total_amount_paid": 0.0,
                "payment_complete": False,
                "can_register": True,  # Can register for any tier
                "can_upgrade": False,  # Not registered yet
                "available_tiers": [
                    {
                        "tier_id": tier.id,
                        "tier_name": tier.tier_name,
                        "tier_price": float(tier.price),
                        "tier_rewards": tier.rewards or [],
                        "tier_benefits": [],  # benefits field doesn't exist
                        "capacity_remaining": tier.max_registrations - tier.current_registrations if tier.max_registrations else None,
                        "is_sold_out": tier.max_registrations is not None and tier.current_registrations >= tier.max_registrations
                    }
                    for tier in all_tiers
                ]
            }
    else:
        # User not authenticated - no registration status
        event_dict["user_registration"] = None

    return EventResponse.model_validate(event_dict)


@router.get("/slug/{slug}", response_model=EventResponse)
def get_event_by_slug(slug: str, db: Session = Depends(get_db)):
    """
    Get event details by slug (URL-friendly identifier)
    """
    service = EventService(db)
    event = service.get_event_by_slug(slug)
    return EventResponse.model_validate(event)


@router.patch("/{event_identifier}", response_model=EventResponse)
def update_event(
    event_identifier: str,
    event_data: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update event details (Admin/Organizer only)
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    service = EventService(db)
    event = service.update_event(
        event_id=event_id,
        update_data=event_data.model_dump(exclude_unset=True),
        current_user=current_user,
    )
    return EventResponse.model_validate(event)


@router.post("/{event_identifier}/upload-banner")
async def upload_event_banner(
    event_identifier: str,
    file: UploadFile = File(...),
    crop_data: str | None = Query(None),
    dominant_color: str | None = Query(None),
    accent_color: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload or replace the banner image for an event."""
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    from app.modules.gallery.services.storage_service import StorageService

    service = EventService(db)
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Event", event_id)

    file_content = await file.read()
    storage = StorageService()
    image_url = await storage.upload_event_image(file_content, event_id, file.filename or "banner.jpg")

    update_data: dict = {}
    if image_url:
        # Update all image fields to keep them in sync
        update_data["banner_image_url"] = image_url
        update_data["medal_image_url"] = image_url
    if crop_data:
        update_data["banner_crop_data"] = json.loads(crop_data)
    if dominant_color:
        update_data["banner_dominant_color"] = dominant_color
    if accent_color:
        update_data["banner_accent_color"] = accent_color

    if update_data:
        service.update_event(event_id=event_id, update_data=update_data, current_user=current_user)

    return {
        "image_url": image_url,
        "message": "Banner uploaded successfully",
        "crop_data": json.loads(crop_data) if crop_data else None,
        "dominant_color": dominant_color,
        "accent_color": accent_color,
    }


@router.post("/{event_identifier}/upload-certificate-template")
async def upload_certificate_template(
    event_identifier: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload certificate template image with embedded tags for OCR detection.

    The system will:
    1. Validate image (PNG/JPG, minimum 1920x1080)
    2. Upload to R2 storage
    3. Perform OCR to detect {{tag}} positions
    4. Store configuration in certificate_template_config

    Supported tags:
    - {{name}} / {{full_name}} - Participant name
    - {{challenge_name}} / {{event_name}} - Event name
    - {{distance}} - Distance completed
    - {{date}} - Completion date
    - {{activity_name}} / {{sport}} - Activity type
    - {{certificate_number}} - Unique certificate number
    - {{digital_signature}} - Organization signature
    - {{registration_number}} - Registration ID
    - {{bib_number}} - Race bib number

    Business Rules:
    - Only admins can upload templates
    - Image must contain visible {{tag}} markers
    - Minimum resolution: 1920x1080px
    - Maximum size: 15MB
    - Supported formats: PNG, JPG
    """
    # Admin check
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can upload certificate templates"
        )

    # Resolve event identifier
    event_id = resolve_event_identifier(event_identifier, db)
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise NotFoundException("Event", event_id)

    # Read file
    file_content = await file.read()

    # Import service
    from app.modules.certificates.services.template_service import TemplateService

    template_service = TemplateService(db)

    try:
        # Upload and process template
        result = await template_service.upload_and_process_template(
            event_id=event_id,
            file_content=file_content,
            filename=file.filename or "template.png"
        )

        # Invalidate existing certificates so they'll be regenerated with new template
        from app.models.user_reward import UserReward, RewardType
        from sqlalchemy import and_

        affected_certs = db.query(UserReward).filter(
            and_(
                UserReward.event_id == event_id,
                UserReward.reward_type == RewardType.CERTIFICATE
            )
        ).all()

        if affected_certs:
            logger.info(f"Invalidating {len(affected_certs)} existing certificates for event {event_id} due to template change")
            for cert in affected_certs:
                # Mark for regeneration by clearing the certificate URL
                # This forces regeneration on next download
                cert.certificate_url = None
                cert.updated_at = datetime.utcnow()

            db.commit()

        return {
            "template_url": result["template_url"],
            "detected_tags": result["detected_tags"],
            "template_config": result["template_config"],
            "message": f"Template uploaded successfully. Detected {len(result['detected_tags'])} tags. {len(affected_certs)} existing certificates will be regenerated on next download."
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to upload certificate template: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process certificate template: {str(e)}"
        )


@router.delete("/{event_identifier}/certificate-template")
async def delete_certificate_template(
    event_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete certificate template and revert to default HTML generation.

    Only admins can delete templates. This will:
    - Remove the template URL
    - Clear the OCR configuration
    - Disable custom template usage
    - Revert to HTML-based certificate generation

    Business Rules:
    - Only admins can delete templates
    - Template file remains in R2 storage (for audit/backup)
    - Future certificates will use HTML format
    """
    # Admin check
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete certificate templates"
        )

    # Resolve event identifier
    event_id = resolve_event_identifier(event_identifier, db)
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise NotFoundException("Event", event_id)

    # Check if template exists
    if not event.uses_custom_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No certificate template configured for this event"
        )

    # Remove template configuration
    event.certificate_template_url = None
    event.certificate_template_config = None
    event.uses_custom_template = False
    db.commit()

    logger.info(f"✅ Certificate template deleted for event {event_id} by admin {current_user.id}")

    return {
        "message": "Certificate template deleted successfully. Certificates will use default HTML format.",
        "event_id": event_id
    }


@router.get("/tesseract-health")
async def tesseract_health_check():
    """
    Health check endpoint to verify Tesseract OCR is installed and working.

    Returns:
        Dict with Tesseract version and status
    """
    import subprocess
    try:
        import pytesseract
        import cv2

        # Check Tesseract version
        version = pytesseract.get_tesseract_version()

        # Try a simple OCR test
        test_result = subprocess.run(
            ['tesseract', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )

        return {
            "status": "healthy",
            "tesseract_installed": True,
            "tesseract_version": str(version),
            "pytesseract_version": "0.3.10",
            "opencv_installed": True,
            "tesseract_output": test_result.stdout[:200]
        }
    except Exception as e:
        logger.error(f"Tesseract health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "tesseract_installed": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@router.get("/{event_identifier}/banner-proxy")
def proxy_event_banner(
    event_identifier: str,
    db: Session = Depends(get_db)
):
    """
    Proxy event banner image for CORS-free access.

    Allows frontend to fetch banner images without CORS issues
    for color extraction and other client-side processing.
    """
    from fastapi.responses import RedirectResponse

    # Try slug first (preferred for clean URLs)
    event = service.get_event_by_slug(event_identifier) if not event_identifier.isdigit() else None

    # Fallback to numeric ID for backward compatibility
    if not event and event_identifier.isdigit():
        event = service.get_event_by_id(int(event_identifier))

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not event.banner_image_url:
        raise HTTPException(status_code=404, detail="Banner not found for this event")

    # Return redirect to actual image URL
    return RedirectResponse(url=event.banner_image_url)


@router.delete("/{event_identifier}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_identifier: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Delete event (Admin/Organizer only)

    Soft deletes the event
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    service = EventService(db)
    service.delete_event(event_id=event_id, current_user=current_user)
    return None


@router.get("/organizer/my", response_model=list[EventResponse])
def get_my_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get events created by current user (Organizer view)
    """
    service = EventService(db)
    events = service.get_events_by_organizer(organizer_id=current_user.id, skip=skip, limit=limit)
    return [EventResponse.model_validate(event) for event in events]


@router.get("/users/{user_id}/events")
def get_user_events(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    """
    Get all events a user has registered for

    Returns paginated response with:
    - events: List of events the user has registered for
    - total: Total count of user's events
    - page: Current page number
    - page_size: Number of items per page
    """
    service = EventService(db)
    events = service.get_events_by_user(user_id=user_id, skip=skip, limit=limit)

    # Get total count
    from app.modules.registrations.domain.registration import Registration

    total = (
        db.query(Event)
        .join(Registration, Event.id == Registration.event_id)
        .filter(Registration.user_id == user_id)
        .count()
    )

    return {
        "events": [EventResponse.model_validate(event) for event in events],
        "total": total,
        "page": (skip // limit) + 1 if limit > 0 else 1,
        "page_size": limit,
    }


# Event Activities Endpoints


@router.post(
    "/{event_identifier}/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED
)
def create_activity(
    event_identifier: str,
    activity_data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create activity for event (Admin/Organizer only)

    Activities are selectable options like "5K Run", "10K Cycle"
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    service = ActivityService(db)
    activity = service.create_activity(
        event_id=event_id, activity_data=activity_data.model_dump(), current_user_id=current_user.id
    )
    return ActivityResponse.model_validate(activity)


@router.get("/{event_identifier}/activities", response_model=list[ActivityResponse])
def get_event_activities(event_identifier: str, db: Session = Depends(get_db)):
    """
    Get all global activity templates.

    NOTE: Activities are now global templates available to all events.
    The event_id parameter is kept for backwards compatibility but ignored.
    Use GET /activities endpoint instead for cleaner API calls.

    Returns list of all selectable activities (running, cycling, etc.)
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    service = ActivityService(db)
    activities = service.get_activities_by_event(event_id)
    return [ActivityResponse.model_validate(activity) for activity in activities]


@router.patch("/activities/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: int,
    activity_data: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update activity details (Admin/Organizer only)
    """
    service = ActivityService(db)
    activity = service.update_activity(
        activity_id=activity_id,
        update_data=activity_data.model_dump(exclude_unset=True),
        current_user_id=current_user.id,
    )
    return ActivityResponse.model_validate(activity)


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Delete activity (Admin/Organizer only)
    """
    service = ActivityService(db)
    service.delete_activity(activity_id=activity_id, current_user_id=current_user.id)
    return None


@router.post("/{event_identifier}/register-tier", status_code=status.HTTP_201_CREATED)
@router.post("/{event_identifier}/register", status_code=status.HTTP_201_CREATED)  # Alias for frontend compatibility
def register_for_event_tier(
    event_identifier: str,
    request: RegisterTierRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Register for an event with a specific tier.

    Returns registration details and payment order if payment is required.
    Available at both /register-tier and /register endpoints for compatibility.
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    from app.modules.registrations.services.registration_service import RegistrationService

    service = RegistrationService(db)
    return service.register_for_event_tier(
        event_id=event_id,
        tier_id=request.tier_id,
        user_id=current_user.id,
        participant_name=request.participant_name,
        age=request.age,
        gender=request.gender,
        t_shirt_size=request.t_shirt_size,
        activity_id=request.activity_id,
    )


# ==================== Tier Management Endpoints ====================


@router.get("/{event_identifier}/tiers", response_model=list[TierResponse])
def get_event_tiers(
    event_identifier: str,
    include_inactive: bool = Query(default=False, description="Include inactive tiers"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[TierResponse]:
    """
    Get all tiers for an event.

    Organizers can see inactive tiers if include_inactive=true.
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    from app.modules.registrations.services.tier_service import TierService

    service = TierService(db)
    tiers = service.get_event_tiers(event_id=event_id, include_inactive=include_inactive)

    return [TierResponse.from_orm_with_computed(tier) for tier in tiers]


@router.post("/{event_identifier}/tiers", response_model=TierResponse, status_code=status.HTTP_201_CREATED)
def create_event_tier(
    event_identifier: str,
    tier_data: TierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TierResponse:
    """
    Create a new tier for an event.

    Only event organizers and admins can create tiers.
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    from app.modules.registrations.services.tier_service import TierService

    service = TierService(db)
    tier = service.create_tier(
        event_id=event_id, tier_data=tier_data, user_id=current_user.id
    )

    return TierResponse.from_orm_with_computed(tier)


@router.put("/{event_identifier}/tiers/{tier_id}", response_model=TierResponse)
def update_event_tier(
    event_identifier: str,
    tier_id: int,
    tier_data: TierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TierResponse:
    """
    Update an existing tier.

    Only event organizers and admins can update tiers.
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    from app.modules.registrations.services.tier_service import TierService

    service = TierService(db)
    tier = service.update_tier(
        tier_id=tier_id, tier_data=tier_data, user_id=current_user.id
    )

    return TierResponse.from_orm_with_computed(tier)


@router.delete("/{event_identifier}/tiers/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_tier(
    event_identifier: str,
    tier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a tier (soft delete - marks as inactive).

    Only event organizers and admins can delete tiers.
    """
    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    from app.modules.registrations.services.tier_service import TierService

    service = TierService(db)
    service.delete_tier(tier_id=tier_id, user_id=current_user.id)

    return None


@router.post("/{event_identifier}/recalculate-participants")
def recalculate_event_participants(
    event_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """
    Recalculate event participant count from actual registrations.

    Admin/Organizer only. Fixes count discrepancies from failed transactions,
    race conditions, or direct database modifications.
    """
    from app.modules.registrations.domain.registration import Registration

    # Resolve slug to numeric event_id
    event_id = resolve_event_identifier(event_identifier, db)

    service = EventService(db)
    event = service.get_event_by_id(event_id)

    # Check permission (admin or organizer)
    service.check_admin_or_organizer(event, current_user)

    # Count confirmed registrations
    confirmed_count = (
        db.query(Registration)
        .filter(
            Registration.event_id == event_id,
            Registration.status.in_(["confirmed", "payment_completed"]),
        )
        .count()
    )

    # Update event participant count
    service.update_event(
        event_id=event_id,
        update_data={"current_participants": confirmed_count},
        current_user=current_user,
    )

    return {"participant_count": confirmed_count}


# Global Activities Endpoints
@activities_router.get("", response_model=list[ActivityResponse])
def get_all_activities(db: Session = Depends(get_db)):
    """
    Get all global activity templates.

    Activities are now global templates available to all events.
    Returns list of all selectable activities (running, cycling, etc.)

    Examples:
    - 3 km, 5 Km, 10 Km, 21 Km (Half Marathon) for running/walking
    - 5 Km, 10 Km, 25 Km, 50 Km, 100 Km for cycling
    """
    service = ActivityService(db)
    activities = service.repository.get_all_activities()
    return [ActivityResponse.model_validate(activity) for activity in activities]
