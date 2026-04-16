"""
Base service with common business logic patterns.

All entity-specific services should inherit from BaseService
to get common authorization and helper methods.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.core.permissions import PermissionChecker


class BaseService:
    """
    Base service class providing common business logic patterns.

    This class provides helper methods for authorization checks,
    error handling, and common service patterns.
    """

    def __init__(self, db: Session):
        """
        Initialize the service.

        Args:
            db: Database session
        """
        self.db = db

    def get_or_404(self, repository, resource_id: int, resource_name: str):
        """
        Get a resource by ID or raise NotFoundException.

        Args:
            repository: Repository instance to query
            resource_id: ID of the resource
            resource_name: Human-readable resource name for error messages

        Returns:
            The resource instance

        Raises:
            NotFoundException: If the resource is not found
        """
        resource = repository.get_by_id(resource_id)
        if not resource:
            raise NotFoundException(resource_name, resource_id)
        return resource

    def check_ownership(self, resource_user_id: int, current_user_id: int, resource_name: str = "resource") -> None:
        """
        Check if the current user owns the resource.

        Args:
            resource_user_id: User ID that owns the resource
            current_user_id: Current user's ID
            resource_name: Human-readable resource name for error messages

        Raises:
            PermissionDeniedException: If the user doesn't own the resource
        """
        PermissionChecker.require_owner(resource_user_id, current_user_id, resource_name)

    def check_event_organizer(self, event, current_user_id: int) -> None:
        """
        Check if the current user is the event organizer.

        Args:
            event: Event model instance
            current_user_id: Current user's ID

        Raises:
            PermissionDeniedException: If the user is not the organizer
        """
        PermissionChecker.require_event_organizer(event, current_user_id)

    def commit_or_rollback(self, operation_name: str = "operation") -> None:
        """
        Commit the current transaction or rollback on error.

        Args:
            operation_name: Name of the operation for error messages

        Raises:
            DatabaseException: If the commit fails
        """
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            from app.core.exceptions import DatabaseException
            raise DatabaseException(f"Failed to complete {operation_name}: {str(e)}")

    def validate_unique(self, repository, field: str, value, resource_name: str, exclude_id: Optional[int] = None) -> None:
        """
        Validate that a field value is unique for the resource.

        Args:
            repository: Repository instance to query
            field: Field name to check
            value: Value to check for uniqueness
            resource_name: Human-readable resource name for error messages
            exclude_id: Optional ID to exclude from uniqueness check (for updates)

        Raises:
            AlreadyExistsException: If the value is not unique
        """
        filters = {field: value}
        existing = repository.find_one_by(**filters)

        if existing and (exclude_id is None or existing.id != exclude_id):
            from app.core.exceptions import AlreadyExistsException
            raise AlreadyExistsException(resource_name, field, value)
