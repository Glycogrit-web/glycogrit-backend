"""
Progress API Endpoints

RESTful endpoints for progress tracking using CQRS pattern.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.modules.activities.services.progress_service import ProgressService
from app.modules.activities.services.commands import (
    CreateProgressCommand,
    UpdateProgressCommand,
    SyncProgressCommand,
    UploadProofCommand,
    ResetProgressCommand,
)
from app.modules.activities.services.queries import (
    GetProgressQuery,
    GetProgressByRegistrationQuery,
    GetUserProgressQuery,
    GetUserProgressListQuery,
    GetEventLeaderboardQuery,
)
from app.modules.activities.schemas.progress import (
    ProgressCreate,
    ProgressUpdate,
    ProgressSyncRequest,
    ProgressSyncResponse,
    ProgressResponse,
    LeaderboardResponse,
    LeaderboardEntry,
    ProofUploadResponse,
)
from app.modules.activities.domain.value_objects import SyncSource
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    PermissionDeniedException,
    ValidationException,
)
from app.utils.rate_limiter import limiter, RateLimits

router = APIRouter(
    prefix="/api/v1/progress",
    tags=["Progress"],
)


@router.post("", response_model=ProgressResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.DEFAULT)
async def create_progress(
    request: Request,
    response: Response,
    progress_data: ProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's progress for specific event."""
    service = ProgressService(db)

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


@router.get("/user/me", response_model=List[ProgressResponse])
@limiter.limit(RateLimits.DEFAULT)
async def get_my_progress_list(
    request: Request,
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
):
    """
    Upload proof image for progress.

    Business Rules:
    - Only owner can upload proof
    - One proof image per progress
    """
    # TODO: Implement file upload to Cloudflare R2
    # For now, return placeholder URL
    image_url = f"https://r2.example.com/proof/{progress_id}_{file.filename}"

    service = ProgressService(db)

    command = UploadProofCommand(
        progress_id=progress_id,
        current_user_id=current_user.id,
        image_url=image_url,
    )

    try:
        progress = service.handle_upload_proof(command)
        return ProofUploadResponse(
            progress_id=progress.id,
            proof_image_url=progress.proof_image_url,
            uploaded_at=progress.updated_at,
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
    current_user: User = Depends(get_current_user)
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


@router.get("/event/{event_id}/leaderboard", response_model=LeaderboardResponse)
@limiter.limit(RateLimits.DEFAULT)
async def get_event_leaderboard(
    request: Request,
    response: Response,
    event_id: int,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
