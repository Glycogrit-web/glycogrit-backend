"""
Progress API Endpoints

RESTful endpoints for progress tracking using CQRS pattern.
"""

from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin
from app.core.database import get_db
from app.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from app.core.rate_limit import RateLimits, limiter
from app.models.user import User
from app.modules.activities.domain.value_objects import SyncSource
from app.modules.activities.schemas.progress import (
    LeaderboardEntry,
    LeaderboardResponse,
    ProgressCreate,
    ProgressResponse,
    ProgressSyncRequest,
    ProgressSyncResponse,
    ProgressUpdate,
    ProofUploadResponse,
)
from app.modules.activities.services.commands import (
    CreateProgressCommand,
    ResetProgressCommand,
    SyncProgressCommand,
    UpdateProgressCommand,
    UploadProofCommand,
)
from app.modules.activities.services.progress_service import ProgressService
from app.modules.activities.services.queries import (
    GetEventLeaderboardQuery,
    GetProgressByRegistrationQuery,
    GetProgressQuery,
    GetUserProgressListQuery,
    GetUserProgressQuery,
)

router = APIRouter(
    prefix="/progress",
    tags=["Progress"],
)


@router.post("", response_model=ProgressResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.DEFAULT)
async def create_progress(
    request: Request,
    response: Response,
    progress_data: ProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create progress for a registration.

    Business Rules:
    - One progress per registration
    - Target distance must be positive
    """
    service = ProgressService(db)

    command = CreateProgressCommand(
        user_id=current_user.id,
        registration_id=progress_data.registration_id,
        event_id=progress_data.event_id,
        activity_id=progress_data.activity_id,
        target_distance=progress_data.target_distance,
    )

    try:
        progress = service.handle_create_progress(command)
        return ProgressResponse.model_validate(progress)
    except AlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{progress_id}", response_model=ProgressResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_progress(
    request: Request,
    response: Response,
    progress_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get progress by ID."""
    service = ProgressService(db)

    query = GetProgressQuery(progress_id=progress_id)

    try:
        progress = service.handle_get_progress(query)
        return ProgressResponse.model_validate(progress)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/registration/{registration_id}", response_model=ProgressResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_progress_by_registration(
    request: Request,
    response: Response,
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get progress by registration ID."""
    service = ProgressService(db)

    query = GetProgressByRegistrationQuery(registration_id=registration_id)

    try:
        progress = service.handle_get_progress_by_registration(query)
        return ProgressResponse.model_validate(progress)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/event/{event_id}/me", response_model=ProgressResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_my_progress_for_event(
    request: Request,
    response: Response,
    event_id: int,
    registration_id: int | None = Query(None, description="Optional: Specific registration ID to get progress for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's progress for specific event.

    If registration_id is provided, returns progress for that specific registration.
    Otherwise, returns progress for the first confirmed registration found.

    This supports users having multiple registrations for the same event (different tiers).
    """
    service = ProgressService(db)

    # If registration_id provided, get progress for that specific registration
    if registration_id:
        from app.modules.activities.commands.progress_commands import GetProgressByRegistrationQuery

        query = GetProgressByRegistrationQuery(registration_id=registration_id)
        progress = service.handle_get_progress_by_registration(query)

        # Verify the registration belongs to this user and event
        if progress.user_id != current_user.id or progress.event_id != event_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this progress"
            )
    else:
        # Default behavior: get first confirmed registration's progress
        query = GetUserProgressQuery(
            user_id=current_user.id,
            event_id=event_id,
        )
        progress = service.handle_get_user_progress(query)

        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Progress not found for this event"
            )

    return ProgressResponse.model_validate(progress)


@router.get("/user/me", response_model=list[ProgressResponse])
@limiter.limit(RateLimits.DEFAULT)
async def get_my_progress_list(
    request: Request,
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all progress records for current user."""
    service = ProgressService(db)

    query = GetUserProgressListQuery(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    progress_list = service.handle_get_user_progress_list(query)

    return [ProgressResponse.model_validate(p) for p in progress_list]


@router.patch("/{progress_id}", response_model=ProgressResponse)
@limiter.limit(RateLimits.DEFAULT)
async def update_progress(
    request: Request,
    response: Response,
    progress_id: int,
    progress_data: ProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update progress with manual entry.

    Business Rules:
    - Only owner can update
    - Manual entries are cumulative
    """
    service = ProgressService(db)

    command = UpdateProgressCommand(
        progress_id=progress_id,
        current_user_id=current_user.id,
        distance_to_add=progress_data.distance_to_add,
    )

    try:
        progress = service.handle_update_progress(command)
        return ProgressResponse.model_validate(progress)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionDeniedException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{progress_id}/sync", response_model=ProgressSyncResponse)
@limiter.limit(RateLimits.DEFAULT)
async def sync_progress(
    request: Request,
    response: Response,
    progress_id: int,
    sync_data: ProgressSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sync progress from external source using highest-wins logic.

    Business Rules:
    - Each source maintains own distance
    - Highest distance becomes active
    - Store metadata per source
    """
    service = ProgressService(db)

    # Convert string enum to domain enum
    sync_source = SyncSource(sync_data.source.value)

    command = SyncProgressCommand(
        progress_id=progress_id,
        source=sync_source,
        distance=sync_data.distance,
        metadata=sync_data.metadata,
    )

    try:
        sync_result = service.handle_sync_progress(command)
        return ProgressSyncResponse(**sync_result)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{progress_id}/proof", response_model=ProofUploadResponse)
@limiter.limit(RateLimits.UPLOAD)
async def upload_proof(
    request: Request,
    response: Response,
    progress_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload proof image for progress.

    Business Rules:
    - Only owner can upload proof
    - One proof image per progress
    """
    from app.modules.gallery.services.storage_service import StorageService

    service = ProgressService(db)

    # Get progress to verify ownership and get event_id
    query = GetProgressQuery(progress_id=progress_id)
    try:
        progress = service.handle_get_progress(query)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Verify ownership
    if progress.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only upload proof for your own progress"
        )

    # Upload file to R2
    try:
        file_content = await file.read()
        storage_service = StorageService()
        image_url = await storage_service.upload_proof_image(
            file_content=file_content,
            user_id=current_user.id,
            event_id=progress.event_id,
            filename=file.filename or "proof.jpg"
        )

        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image to storage"
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )

    # Update progress with image URL
    command = UploadProofCommand(
        progress_id=progress_id,
        current_user_id=current_user.id,
        image_url=image_url,
    )

    try:
        updated_progress = service.handle_upload_proof(command)
        return ProofUploadResponse(
            progress_id=updated_progress.id,
            proof_image_url=updated_progress.proof_image_url,
            uploaded_at=updated_progress.updated_at,
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionDeniedException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{progress_id}/reset", response_model=ProgressResponse)
@limiter.limit(RateLimits.DEFAULT)
async def reset_progress(
    request: Request,
    response: Response,
    progress_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reset progress to zero.

    Business Rules:
    - Only owner can reset
    - Clears all distances and completion
    """
    service = ProgressService(db)

    command = ResetProgressCommand(
        progress_id=progress_id,
        current_user_id=current_user.id,
    )

    try:
        progress = service.handle_reset_progress(command)
        return ProgressResponse.model_validate(progress)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionDeniedException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{event_id}/admin-update", response_model=ProgressResponse)
@limiter.limit(RateLimits.DEFAULT)
async def admin_update_progress(
    request: Request,
    response: Response,
    event_id: int,
    user_id: int = Query(..., description="User ID to update progress for"),
    total_distance_km: float = Query(..., description="New total distance in km"),
    notes: str | None = Query(None, description="Optional admin notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Admin: Manually set user's total progress distance.

    This endpoint allows admins to directly set a user's total distance
    (not add to it) for a specific event.

    Requires admin role.
    """
    from app.modules.registrations.repositories.registration_repository import RegistrationRepository

    service = ProgressService(db)
    reg_repo = RegistrationRepository(db)

    # Find the user's registrations for this event (returns list since users can have multiple)
    registrations = reg_repo.get_by_user_and_event(user_id, event_id)

    if not registrations or len(registrations) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registration found for user {user_id} in event {event_id}"
        )

    # Use the first confirmed registration (or just the first one)
    # For admin updates, we typically want the most recent or primary registration
    registration = registrations[0] if isinstance(registrations, list) else registrations

    # Get progress by registration
    query = GetProgressByRegistrationQuery(registration_id=registration.id)

    try:
        progress = service.handle_get_progress_by_registration(query)
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No progress found for registration {registration.id}"
        )

    # Use highest-wins logic with admin_manual source
    if notes:
        admin_metadata = {
            "admin_notes": notes,
            "last_admin_update": {
                "admin_id": current_user.id,
                "admin_email": current_user.email,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
    else:
        admin_metadata = None

    # Use model's built-in highest-wins update method
    # This stores admin notes in distance_by_source['admin_manual']
    result = progress.update_progress_highest_wins(
        new_distance_km=float(total_distance_km),
        source="admin_manual",
        metadata=admin_metadata
    )

    # Commit changes
    db.commit()
    db.refresh(progress)

    return ProgressResponse.model_validate(progress)


@router.get("/event/{event_id}/leaderboard", response_model=LeaderboardResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_event_leaderboard(
    request: Request,
    response: Response,
    event_id: int,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get leaderboard for event."""
    service = ProgressService(db)

    query = GetEventLeaderboardQuery(
        event_id=event_id,
        limit=limit,
    )

    leaderboard_data = service.handle_get_event_leaderboard(query)

    return LeaderboardResponse(
        event_id=event_id,
        leaderboard=[LeaderboardEntry(**entry) for entry in leaderboard_data],
        total_participants=len(leaderboard_data),
    )
