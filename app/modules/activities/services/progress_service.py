"""
Progress Service - Business logic for progress tracking

Implements CQRS pattern with commands and queries.
Handles highest-wins logic for multi-source sync.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from app.models.activity_progress import ActivityProgress
from app.modules.activities.domain.value_objects import SyncSource
from app.modules.activities.repositories.progress_repository import ProgressRepository
from app.modules.activities.services.commands import (
    CreateProgressCommand,
    ResetProgressCommand,
    SyncProgressCommand,
    UpdateProgressCommand,
    UploadProofCommand,
)
from app.modules.activities.services.queries import (
    GetEventLeaderboardQuery,
    GetProgressByRegistrationQuery,
    GetProgressQuery,
    GetUserProgressListQuery,
    GetUserProgressQuery,
)
from app.services.base import BaseService


class ProgressService(BaseService):
    """Service for progress-related business logic using CQRS pattern."""

    def __init__(self, db: Session):
        """
        Initialize the ProgressService.

        Args:
            db: Database session
        """
        super().__init__(db)
        self.repository = ProgressRepository(db)

    # COMMAND HANDLERS (Write Operations)

    def handle_create_progress(self, command: CreateProgressCommand) -> ActivityProgress:
        """
        Handle CreateProgressCommand.

        Business Rules:
        1. One progress per registration
        2. Target distance must be positive
        3. Registration must exist

        Args:
            command: CreateProgressCommand

        Returns:
            Created ActivityProgress instance

        Raises:
            AlreadyExistsException: If progress already exists for registration
            ValidationException: If target distance is invalid
        """
        # Check for existing progress
        existing = self.repository.get_by_registration(command.registration_id)
        if existing:
            raise AlreadyExistsException(
                "Progress",
                "registration_id",
                str(command.registration_id)
            )

        # Validate target distance
        if command.target_distance <= 0:
            raise ValidationException("Target distance must be positive")

        # Create progress data
        progress_data = {
            "user_id": command.user_id,
            "registration_id": command.registration_id,
            "event_id": command.event_id,
            "activity_id": command.activity_id,
            "target_distance": command.target_distance,
            "distance_completed": Decimal("0.00"),
            "distance_by_source": {},
        }

        return self.repository.create(progress_data)

    def handle_update_progress(self, command: UpdateProgressCommand) -> ActivityProgress:
        """
        Handle UpdateProgressCommand.

        Business Rules:
        1. Only owner can update progress
        2. Manual entries are cumulative
        3. Auto-complete when target reached

        Args:
            command: UpdateProgressCommand

        Returns:
            Updated ActivityProgress instance

        Raises:
            NotFoundException: If progress not found
            PermissionDeniedException: If user doesn't own progress
        """
        # Get progress
        progress = self.get_or_404(self.repository, command.progress_id, "Progress")

        # Check ownership
        if progress.user_id != command.current_user_id:
            raise PermissionDeniedException("You can only update your own progress")

        # Calculate new distance
        new_distance = progress.distance_completed + command.distance_to_add

        # Build update data
        update_data = {
            "distance_completed": new_distance,
            "last_manual_entry": command.distance_to_add,
            "last_manual_entry_at": datetime.utcnow(),
            "sync_source": "manual",
            "last_sync_at": datetime.utcnow(),
        }

        # Auto-complete if target reached
        if new_distance >= progress.target_distance and not progress.completed_at:
            update_data["completed_at"] = datetime.utcnow()

        return self.repository.update(command.progress_id, update_data)

    def handle_sync_progress(self, command: SyncProgressCommand) -> dict[str, Any]:
        """
        Handle SyncProgressCommand with highest-wins logic.

        Business Rules:
        1. Each source maintains own distance
        2. Highest distance becomes active
        3. Store metadata per source
        4. Track sync timestamps

        Args:
            command: SyncProgressCommand

        Returns:
            Dict with sync result details

        Raises:
            NotFoundException: If progress not found
        """
        # Get progress
        progress = self.get_or_404(self.repository, command.progress_id, "Progress")

        # Validate distance
        if command.distance < 0:
            raise ValidationException("Distance cannot be negative")

        # Get current distance_by_source
        distance_by_source = progress.distance_by_source or {}
        source_key = command.source.value if isinstance(command.source, SyncSource) else command.source

        # Store distance and metadata for this source
        source_data = {
            'distance_km': float(command.distance),
            'last_updated': datetime.utcnow().isoformat(),
        }

        if command.metadata:
            source_data.update(command.metadata)

        distance_by_source[source_key] = source_data

        # Find highest distance across all sources
        highest_distance = Decimal("0.00")
        highest_source = None

        for src, data in distance_by_source.items():
            src_distance = Decimal(str(data.get('distance_km', 0)))
            if src_distance > highest_distance:
                highest_distance = src_distance
                highest_source = src

        # Build update data
        update_data = {
            "distance_by_source": distance_by_source,
            "last_sync_at": datetime.utcnow(),
            "sync_source": source_key,
        }

        # Update if this is new highest
        was_updated = False
        old_distance = progress.distance_completed

        if highest_source and (
            not progress.highest_distance_source or
            highest_distance > progress.distance_completed
        ):
            update_data["distance_completed"] = highest_distance
            update_data["highest_distance_source"] = highest_source
            update_data["highest_distance_set_at"] = datetime.utcnow()
            was_updated = True

            # Auto-complete if target reached
            if highest_distance >= progress.target_distance and not progress.completed_at:
                update_data["completed_at"] = datetime.utcnow()

        # Update progress
        updated_progress = self.repository.update(command.progress_id, update_data)

        return {
            'was_updated': was_updated,
            'source': source_key,
            'source_distance': float(command.distance),
            'old_active_distance': float(old_distance),
            'new_active_distance': float(updated_progress.distance_completed),
            'highest_source': updated_progress.highest_distance_source,
            'is_completed': updated_progress.is_completed,
            'progress_percentage': updated_progress.progress_percentage,
        }

    def handle_upload_proof(self, command: UploadProofCommand) -> ActivityProgress:
        """
        Handle UploadProofCommand.

        Business Rules:
        1. Only owner can upload proof
        2. One proof image per progress

        Args:
            command: UploadProofCommand

        Returns:
            Updated ActivityProgress instance

        Raises:
            NotFoundException: If progress not found
            PermissionDeniedException: If user doesn't own progress
        """
        # Get progress
        progress = self.get_or_404(self.repository, command.progress_id, "Progress")

        # Check ownership
        if progress.user_id != command.current_user_id:
            raise PermissionDeniedException("You can only upload proof for your own progress")

        # Update proof image
        update_data = {"proof_image_url": command.image_url}

        return self.repository.update(command.progress_id, update_data)

    def handle_reset_progress(self, command: ResetProgressCommand) -> ActivityProgress:
        """
        Handle ResetProgressCommand.

        Business Rules:
        1. Only owner can reset progress
        2. Clears all distances and completion

        Args:
            command: ResetProgressCommand

        Returns:
            Reset ActivityProgress instance

        Raises:
            NotFoundException: If progress not found
            PermissionDeniedException: If user doesn't own progress
        """
        # Get progress
        progress = self.get_or_404(self.repository, command.progress_id, "Progress")

        # Check ownership
        if progress.user_id != command.current_user_id:
            raise PermissionDeniedException("You can only reset your own progress")

        # Reset data
        update_data = {
            "distance_completed": Decimal("0.00"),
            "completed_at": None,
            "highest_distance_source": None,
            "highest_distance_set_at": None,
            "distance_by_source": {},
            "last_manual_entry": None,
            "last_manual_entry_at": None,
        }

        return self.repository.update(command.progress_id, update_data)

    # QUERY HANDLERS (Read Operations)

    def handle_get_progress(self, query: GetProgressQuery) -> ActivityProgress:
        """
        Handle GetProgressQuery.

        Args:
            query: GetProgressQuery

        Returns:
            ActivityProgress instance

        Raises:
            NotFoundException: If progress not found
        """
        return self.get_or_404(self.repository, query.progress_id, "Progress")

    def handle_get_progress_by_registration(
        self,
        query: GetProgressByRegistrationQuery
    ) -> ActivityProgress:
        """
        Handle GetProgressByRegistrationQuery.

        Args:
            query: GetProgressByRegistrationQuery

        Returns:
            ActivityProgress instance

        Raises:
            NotFoundException: If progress not found
        """
        progress = self.repository.get_by_registration(query.registration_id)
        if not progress:
            raise NotFoundException("Progress", str(query.registration_id))
        return progress

    def handle_get_user_progress(
        self,
        query: GetUserProgressQuery
    ) -> ActivityProgress | None:
        """
        Handle GetUserProgressQuery.

        Args:
            query: GetUserProgressQuery

        Returns:
            ActivityProgress instance or None
        """
        return self.repository.get_user_progress(query.user_id, query.event_id)

    def handle_get_user_progress_list(
        self,
        query: GetUserProgressListQuery
    ) -> list[ActivityProgress]:
        """
        Handle GetUserProgressListQuery.

        Args:
            query: GetUserProgressListQuery

        Returns:
            List of ActivityProgress instances
        """
        return self.repository.get_user_progress_list(
            query.user_id,
            query.skip,
            query.limit
        )

    def handle_get_event_leaderboard(
        self,
        query: GetEventLeaderboardQuery
    ) -> list[dict[str, Any]]:
        """
        Handle GetEventLeaderboardQuery.

        Args:
            query: GetEventLeaderboardQuery

        Returns:
            List of leaderboard entries with user info
        """
        progress_list = self.repository.get_event_leaderboard(
            query.event_id,
            query.limit
        )

        # Format leaderboard data
        leaderboard = []
        for rank, progress in enumerate(progress_list, start=1):
            entry = {
                "rank": rank,
                "user_id": progress.user_id,
                "distance_completed": float(progress.distance_completed),
                "target_distance": float(progress.target_distance),
                "progress_percentage": progress.progress_percentage,
                "is_completed": progress.is_completed,
                "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
                "activity_count": progress.get_total_activities(),
                "total_duration_minutes": progress.get_total_duration_minutes(),
            }
            leaderboard.append(entry)

        return leaderboard
