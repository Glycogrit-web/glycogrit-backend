"""
Event API Endpoints
"""
from typing import Optional, Dict, Any, List
import json
import httpx
from fastapi import APIRouter, Depends, status, Query, Request, Response, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.auth import get_current_active_user, get_optional_current_user
from app.core.rate_limit import limiter, RateLimits
from app.schemas.event import (
    EventResponse, EventListResponse, EventRegisterRequest, EventRegisterResponse,
    EventCreate, EventUpdate, ActivityResponse, ActivityCreate, ActivityUpdate
)
from app.schemas.registration import RegistrationCreate, RegistrationResponse
from app.models.user import User
from app.models.event import Event, EventActivity
from app.models.registration import Registration
from app.modules.events import EventService, ActivityService
from app.modules.registrations import RegistrationService
from app.services.storage_service import storage_service

router = APIRouter(prefix="/api/v1/events", tags=["Events"])


@router.get("", response_model=EventListResponse)
@limiter.limit(RateLimits.READ_LIST)
async def list_events(
    request: Request,
    response: Response,
    category: Optional[str] = Query(None, description="Filter by event type (running, cycling, walking, mixed, strength)"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (beginner, intermediate, advanced)"),
    status: Optional[str] = Query(None, description="Filter by status (draft, published, cancelled, completed)"),
    is_virtual: Optional[bool] = Query(None, description="Filter virtual events"),
    is_featured: Optional[bool] = Query(None, description="Filter featured events"),
    include_drafts: Optional[bool] = Query(False, description="Include draft events (admin only)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> EventListResponse:
    """
    Get list of events with optional filters and pagination.

    Returns a paginated list of published events with optional filtering capabilities.

    Args:
        request: FastAPI Request object (required for rate limiting)
        category: Filter by event type (running, cycling, walking, mixed, strength)
        difficulty: Filter by difficulty level (beginner, intermediate, advanced)
        status: Filter by event status (upcoming, ongoing, completed)
        is_virtual: Filter virtual events only
        is_featured: Filter featured events only
        page: Page number (default: 1)
        limit: Items per page (default: 20, max: 100)
        db: Database session dependency

    Returns:
        EventListResponse: Paginated list of events with total count

    Rate Limit:
        60 requests per minute
    """
    query = db.query(Event).options(
        joinedload(Event.activities)
    )

    # Apply filters
    # Note: event_type has been removed. Filter by activity types if needed
    if category and category != 'all':
        # Filter events that have activities of this type
        query = query.join(Event.activities).filter(EventActivity.activity_type == category)

    if difficulty and difficulty != 'all':
        query = query.filter(Event.difficulty_level == difficulty)

    if status and status != 'all':
        query = query.filter(Event.status == status)

    if is_virtual is not None:
        query = query.filter(Event.is_virtual == is_virtual)

    if is_featured is not None:
        query = query.filter(Event.is_featured == is_featured)

    # Only show published events (not draft) unless admin requests drafts
    is_admin = current_user and current_user.role in ['admin', 'super_admin']
    if not include_drafts or not is_admin:
        query = query.filter(Event.status != 'draft')

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * limit
    events = query.order_by(Event.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "events": events,
        "total": total,
        "page": page,
        "page_size": limit
    }


@router.get("/{event_id}", response_model=EventResponse)
@limiter.limit(RateLimits.READ_DETAIL)
async def get_event(
    request: Request,
    response: Response,
    event_id: int,
    db: Session = Depends(get_db)
) -> EventResponse:
    """
    Get event details by ID.

    Returns detailed information about a specific event including categories.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to retrieve
        db: Database session dependency

    Returns:
        EventResponse: Event details

    Raises:
        NotFoundException: If event not found

    Rate Limit:
        100 requests per minute
    """
    service: EventService = EventService(db)
    event: EventResponse = service.get_event_by_id(event_id)
    return event


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def create_event(
    request: Request,
    response: Response,
    event_data: EventCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> EventResponse:
    """
    Create a new event.

    Creates a new event with the authenticated user as the organizer.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_data: Event creation data
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        EventResponse: Created event details

    Raises:
        ValidationException: If event data is invalid

    Rate Limit:
        20 requests per minute

    Authorization:
        Only authenticated users can create events

    Requires:
        Bearer token in Authorization header
    """
    service: EventService = EventService(db)
    event_dict: Dict[str, Any] = event_data.model_dump()
    event: EventResponse = service.create_event(event_dict, current_user.id)
    return event


@router.put("/{event_id}", response_model=EventResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def update_event(
    request: Request,
    response: Response,
    event_id: int,
    event_data: EventUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> EventResponse:
    """
    Update an event.

    Updates an existing event. Event organizer or admin can update.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to update
        event_data: Updated event data
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        EventResponse: Updated event details

    Raises:
        NotFoundException: If event not found
        PermissionDeniedException: If user is not the event organizer or admin

    Rate Limit:
        30 requests per minute

    Authorization:
        Event organizer or admin can update the event

    Requires:
        Bearer token in Authorization header
    """
    service: EventService = EventService(db)
    update_dict: Dict[str, Any] = event_data.model_dump(exclude_unset=True)
    event: EventResponse = service.update_event(event_id, update_dict, current_user)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.WRITE_DELETE)
async def delete_event(
    request: Request,
    response: Response,
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete an event.

    Deletes an existing event. Event organizer or admin can delete.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to delete
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        Dict with success message

    Raises:
        NotFoundException: If event not found
        PermissionDeniedException: If user is not the event organizer or admin

    Rate Limit:
        10 requests per minute

    Authorization:
        Event organizer or admin can delete the event

    Requires:
        Bearer token in Authorization header
    """
    service: EventService = EventService(db)
    service.delete_event(event_id, current_user)
    return {"message": "Event deleted successfully"}


@router.post("/{event_id}/upload-banner", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def upload_event_banner(
    request: Request,
    response: Response,
    event_id: int,
    file: UploadFile = File(...),
    crop_data: Optional[str] = Query(None, description="JSON string of crop data (x, y, width, height, zoom, rotation)"),
    dominant_color: Optional[str] = Query(None, description="Dominant color extracted from image (hex format)"),
    accent_color: Optional[str] = Query(None, description="Accent color extracted from image (hex format)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Upload banner image for an event.

    Uploads and optimizes an event banner image to Cloudflare R2.
    Updates the event's banner_image_url field with the uploaded image URL.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to upload banner for
        file: Image file to upload (JPEG, PNG, WEBP)
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        Dict with image_url of the uploaded banner

    Raises:
        NotFoundException: If event not found
        PermissionDeniedException: If user is not the event organizer or admin
        ValidationException: If image validation fails

    Rate Limit:
        30 requests per minute

    Authorization:
        Event organizer or admin can upload banner

    Requires:
        Bearer token in Authorization header

    File Requirements:
        - Formats: JPEG, PNG, WEBP
        - Max size: 5MB
        - Min dimensions: 800x450px
    """
    # Check if event exists and user has permission
    service: EventService = EventService(db)
    event: Event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found"
        )

    # Check permission (organizer or admin)
    if event.organizer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the event organizer or admin can upload banner"
        )

    # Read file content
    file_content = await file.read()

    # Upload to R2
    try:
        image_url = await storage_service.upload_event_image(
            file_content=file_content,
            event_id=event_id,
            filename=file.filename
        )

        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image to storage"
            )

        # Delete old image if exists
        if event.banner_image_url:
            await storage_service.delete_event_image(event.banner_image_url)

        # Prepare update dict with image URL
        update_dict = {"banner_image_url": image_url}

        # Parse and add crop data if provided
        if crop_data:
            try:
                crop_dict = json.loads(crop_data)
                update_dict["banner_crop_data"] = crop_dict
            except json.JSONDecodeError:
                pass  # Ignore invalid JSON

        # Add color data if provided
        if dominant_color:
            update_dict["banner_dominant_color"] = dominant_color
        if accent_color:
            update_dict["banner_accent_color"] = accent_color

        # Update event with new data
        service.update_event(event_id, update_dict, current_user)

        return {
            "message": "Banner uploaded successfully",
            "image_url": image_url,
            "crop_data": update_dict.get("banner_crop_data"),
            "dominant_color": dominant_color,
            "accent_color": accent_color
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


@router.get("/{event_id}/banner-proxy")
@limiter.limit(RateLimits.READ_DETAIL)
async def proxy_event_banner(
    request: Request,
    response: Response,
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Proxy endpoint to fetch event banner image with CORS headers.

    This endpoint fetches the banner image from R2 and returns it with proper CORS headers,
    allowing the frontend to use it with the image cropper without CORS issues.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to fetch banner for
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        StreamingResponse: Image binary data with proper CORS headers

    Raises:
        NotFoundException: If event not found or no banner image
        HTTPException: If failed to fetch image from R2

    Rate Limit:
        60 requests per minute

    Authorization:
        Authenticated users can access this endpoint

    Requires:
        Bearer token in Authorization header
    """
    # Get event
    event: Event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found"
        )

    if not event.banner_image_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event has no banner image"
        )

    # Fetch image from R2
    try:
        async with httpx.AsyncClient() as client:
            r2_response = await client.get(event.banner_image_url)
            r2_response.raise_for_status()

            # Return image with CORS headers
            return StreamingResponse(
                iter([r2_response.content]),
                media_type=r2_response.headers.get("content-type", "image/png"),
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                    "Access-Control-Allow-Headers": "*",
                }
            )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch image from storage: {str(e)}"
        )


@router.get("/{event_id}/activities", response_model=List[ActivityResponse])
@limiter.limit(RateLimits.READ_DETAIL)
async def get_event_activities(
    request: Request,
    response: Response,
    event_id: int,
    db: Session = Depends(get_db)
) -> List[ActivityResponse]:
    """
    Get all activities for an event.

    Returns all selectable activities available for a specific event (e.g., 5K Run, 10K Cycle).

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID
        db: Database session dependency

    Returns:
        List of ActivityResponse objects

    Raises:
        NotFoundException: If event not found

    Rate Limit:
        100 requests per minute
    """
    service: ActivityService = ActivityService(db)
    activities: List[ActivityResponse] = service.get_activities_by_event(event_id)
    return activities


@router.post("/{event_id}/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def create_event_activity(
    request: Request,
    response: Response,
    event_id: int,
    activity_data: ActivityCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ActivityResponse:
    """
    Create a new activity for an event.

    Creates a selectable activity for an event (e.g., 5K Run, 10K Cycle, Half Marathon).

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to add activity to
        activity_data: Activity creation data (name, activity_type, distance, etc.)
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        ActivityResponse: Created activity details

    Raises:
        NotFoundException: If event not found
        PermissionDeniedException: If user is not the event organizer

    Rate Limit:
        20 requests per minute

    Authorization:
        Only the event organizer can create activities

    Requires:
        Bearer token in Authorization header
    """
    service: ActivityService = ActivityService(db)
    activity_dict: Dict[str, Any] = activity_data.model_dump()
    activity: ActivityResponse = service.create_activity(event_id, activity_dict, current_user.id)
    return activity


@router.put("/activities/{activity_id}", response_model=ActivityResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def update_event_activity(
    request: Request,
    response: Response,
    activity_id: int,
    activity_data: ActivityUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ActivityResponse:
    """
    Update an event activity.

    Updates an existing event activity. Only the event organizer can update.

    Args:
        request: FastAPI Request object (required for rate limiting)
        activity_id: Activity ID to update
        activity_data: Updated activity data
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        ActivityResponse: Updated activity details

    Raises:
        NotFoundException: If activity not found
        PermissionDeniedException: If user is not the event organizer

    Rate Limit:
        30 requests per minute

    Authorization:
        Only the event organizer can update activities

    Requires:
        Bearer token in Authorization header
    """
    service: ActivityService = ActivityService(db)
    update_dict: Dict[str, Any] = activity_data.model_dump(exclude_unset=True)
    activity: ActivityResponse = service.update_activity(activity_id, update_dict, current_user.id)
    return activity


@router.delete("/activities/{activity_id}", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.WRITE_DELETE)
async def delete_event_activity(
    request: Request,
    response: Response,
    activity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete an event activity.

    Deletes an existing event activity. Only the event organizer can delete.

    Args:
        request: Request object (required for rate limiting)
        activity_id: Activity ID to delete
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        Dict with success message

    Raises:
        NotFoundException: If activity not found
        PermissionDeniedException: If user is not the event organizer

    Rate Limit:
        10 requests per minute

    Authorization:
        Only the event organizer can delete activities

    Requires:
        Bearer token in Authorization header
    """
    service: ActivityService = ActivityService(db)
    service.delete_activity(activity_id, current_user.id)
    return {"message": "Activity deleted successfully"}


@router.post("/{event_id}/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.WRITE_CREATE)
async def register_for_event(
    request: Request,
    response: Response,
    event_id: int,
    registration_data: RegistrationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> RegistrationResponse:
    """
    Register current user for an event.

    Creates a new registration for the authenticated user for a specific event.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID to register for
        registration_data: Registration data (category, participant name, etc.)
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        RegistrationResponse: Created registration details

    Raises:
        NotFoundException: If event or category not found
        AlreadyExistsException: If user already registered for this event
        ValidationException: If registration data is invalid

    Rate Limit:
        20 requests per minute

    Requires:
        Bearer token in Authorization header
    """
    service: RegistrationService = RegistrationService(db)
    registration: RegistrationResponse = service.register_for_event(
        event_id=event_id,
        user_id=current_user.id,
        category_id=registration_data.category_id,
        participant_name=registration_data.participant_name,
        age=registration_data.age,
        gender=registration_data.gender,
        t_shirt_size=registration_data.t_shirt_size
    )
    return registration


@router.delete("/registrations/{registration_id}", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.WRITE_DELETE)
async def cancel_registration(
    request: Request,
    response: Response,
    registration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Cancel event registration.

    Cancels an existing registration. Users can only cancel their own registrations.

    Args:
        request: FastAPI Request object (required for rate limiting)
        registration_id: Registration ID to cancel
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        Dict with success message

    Raises:
        NotFoundException: If registration not found
        PermissionDeniedException: If user is not the registration owner

    Rate Limit:
        10 requests per minute

    Authorization:
        Users can only cancel their own registrations

    Requires:
        Bearer token in Authorization header
    """
    service: RegistrationService = RegistrationService(db)
    service.cancel_registration(registration_id, current_user.id)
    return {"message": "Registration cancelled successfully"}


@router.post("/{event_id}/recalculate-participants", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def recalculate_event_participants(
    request: Request,
    response: Response,
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Recalculate and update event participant count based on confirmed registrations.

    Admin-only endpoint to fix participant counts.

    Args:
        request: FastAPI Request object (required for rate limiting)
        event_id: Event ID
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        Dict with updated participant count

    Raises:
        NotFoundException: If event not found
        PermissionDeniedException: If user is not an admin

    Rate Limit:
        30 requests per minute

    Authorization:
        Admin access required

    Requires:
        Bearer token in Authorization header
    """
    from app.core.permissions import PermissionChecker
    from app.repositories.event_repository import EventRepository
    from sqlalchemy import func

    # Require admin access
    PermissionChecker.require_admin(current_user)

    # Get event service and verify event exists
    event_service: EventService = EventService(db)
    event = event_service.get_event_by_id(event_id)

    # Count confirmed registrations
    confirmed_count = db.query(func.count(Registration.id)).filter(
        Registration.event_id == event_id,
        Registration.status == 'confirmed'
    ).scalar()

    # Update event
    event_repository = EventRepository(db)
    event_repository.update(event_id, {"current_participants": confirmed_count})

    return {
        "message": "Participant count recalculated successfully",
        "event_id": event_id,
        "participant_count": confirmed_count
    }


@router.get("/users/{user_id}/events", response_model=EventListResponse)
@limiter.limit(RateLimits.READ_LIST)
async def get_user_events(
    request: Request,
    response: Response,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
) -> EventListResponse:
    """
    Get events that a user is registered for.

    Returns paginated list of events the user has registered for.

    Args:
        request: FastAPI Request object (required for rate limiting)
        user_id: User ID
        current_user: Current authenticated user from JWT token
        page: Page number (default: 1)
        limit: Items per page (default: 20, max: 100)
        db: Database session dependency

    Returns:
        EventListResponse: Paginated list of registered events

    Raises:
        PermissionDeniedException: If user tries to view another user's registrations

    Rate Limit:
        60 requests per minute

    Authorization:
        Users can only view their own registrations

    Requires:
        Bearer token in Authorization header
    """
    # Check if user is accessing their own data
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own registrations"
        )

    # Get user's registrations
    registrations_query = db.query(Registration).filter(
        Registration.user_id == user_id,
        Registration.status == 'confirmed'
    )

    total: int = registrations_query.count()

    # Get events through registrations
    offset: int = (page - 1) * limit
    registrations: List[Registration] = registrations_query.offset(offset).limit(limit).all()

    # Get event IDs
    event_ids: List[int] = [reg.event_id for reg in registrations]

    # Get events with activities
    events: List[Event] = db.query(Event).options(
        joinedload(Event.activities)
    ).filter(Event.id.in_(event_ids)).all() if event_ids else []

    return {
        "events": events,
        "total": total,
        "page": page,
        "page_size": limit
    }
