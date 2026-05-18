"""
Base service with common business logic patterns.

All entity-specific services should inherit from BaseService
to get common authorization and helper methods.
"""

from typing import Optional, Type, TypeVar, Generic, List, Dict, Any, Callable
from sqlalchemy.orm import Session
import logging

from app.core.exceptions import NotFoundException
from app.core.permissions import PermissionChecker
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

# Generic type for models
ModelType = TypeVar("ModelType")
RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)


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

    def check_admin_or_organizer(self, event, current_user) -> None:
        """
        Check if the current user is an admin or the event organizer.

        Args:
            event: Event model instance
            current_user: User model instance

        Raises:
            PermissionDeniedException: If the user is neither admin nor organizer
        """
        PermissionChecker.require_admin_or_organizer(current_user, event)

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


class CRUDService(Generic[ModelType, RepositoryType], BaseService):
    """
    Generic CRUD service with common create, read, update, delete operations

    This service provides standard CRUD operations that can be inherited
    by entity-specific services, reducing boilerplate code.

    Usage:
        class UserService(CRUDService[User, UserRepository]):
            def __init__(self, db: Session):
                super().__init__(db, UserRepository)

            # Override or add custom methods as needed
            def get_by_email(self, email: str):
                return self.repository.find_one_by(email=email)
    """

    def __init__(self, db: Session, repository_class: Type[RepositoryType]):
        """
        Initialize CRUD service with repository

        Args:
            db: Database session
            repository_class: Repository class to instantiate
        """
        super().__init__(db)
        self.repository: RepositoryType = repository_class(db)
        self.model_name = repository_class.__name__.replace('Repository', '')

    def create(self, data: Dict[str, Any], created_by: Optional[int] = None) -> ModelType:
        """
        Create a new resource

        Args:
            data: Resource data
            created_by: User ID who created the resource (if applicable)

        Returns:
            Created resource instance
        """
        if created_by is not None and 'user_id' in data:
            data['user_id'] = created_by

        logger.info(f"Creating {self.model_name}")
        resource = self.repository.create(data)
        logger.info(f"Created {self.model_name} with id={resource.id}")
        return resource

    def get_by_id(self, resource_id: int) -> Optional[ModelType]:
        """
        Get resource by ID

        Args:
            resource_id: Resource ID

        Returns:
            Resource instance or None
        """
        return self.repository.get_by_id(resource_id)

    def get_by_id_or_404(self, resource_id: int) -> ModelType:
        """
        Get resource by ID or raise 404

        Args:
            resource_id: Resource ID

        Returns:
            Resource instance

        Raises:
            NotFoundException: If resource not found
        """
        return self.get_or_404(self.repository, resource_id, self.model_name)

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        """
        Get all resources with optional filters

        Args:
            skip: Number of records to skip
            limit: Maximum number of records
            **filters: Additional filters

        Returns:
            List of resources
        """
        if filters:
            return self.repository.find_by(**filters)
        return self.repository.get_all(skip=skip, limit=limit)

    def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        **filters
    ) -> tuple[List[ModelType], int]:
        """
        Get paginated resources

        Args:
            page: Page number
            page_size: Items per page
            **filters: Additional filters

        Returns:
            Tuple of (items, total_count)
        """
        return self.repository.paginate(page, page_size, **filters)

    def update(
        self,
        resource_id: int,
        data: Dict[str, Any],
        updated_by: Optional[int] = None
    ) -> ModelType:
        """
        Update a resource

        Args:
            resource_id: Resource ID
            data: Update data
            updated_by: User ID who updated the resource

        Returns:
            Updated resource instance

        Raises:
            NotFoundException: If resource not found
        """
        resource = self.get_by_id_or_404(resource_id)

        logger.info(f"Updating {self.model_name} id={resource_id}")
        updated = self.repository.update(resource_id, data)
        logger.info(f"Updated {self.model_name} id={resource_id}")

        return updated

    def delete(self, resource_id: int) -> bool:
        """
        Delete a resource

        Args:
            resource_id: Resource ID

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting {self.model_name} id={resource_id}")
        result = self.repository.delete(resource_id)

        if result:
            logger.info(f"Deleted {self.model_name} id={resource_id}")
        else:
            logger.warning(f"{self.model_name} id={resource_id} not found for deletion")

        return result

    def exists(self, resource_id: int) -> bool:
        """
        Check if resource exists

        Args:
            resource_id: Resource ID

        Returns:
            True if exists, False otherwise
        """
        return self.repository.exists(resource_id)

    def count(self, **filters) -> int:
        """
        Count resources matching filters

        Args:
            **filters: Filter criteria

        Returns:
            Count of matching resources
        """
        return self.repository.count(**filters)

    def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple resources

        Args:
            data_list: List of resource data

        Returns:
            List of created resources
        """
        logger.info(f"Bulk creating {len(data_list)} {self.model_name} records")
        resources = self.repository.bulk_create(data_list)
        logger.info(f"Bulk created {len(resources)} {self.model_name} records")
        return resources


class OwnedResourceService(CRUDService[ModelType, RepositoryType]):
    """
    Service for resources that have user ownership

    Adds ownership validation to CRUD operations

    Usage:
        class RegistrationService(OwnedResourceService[Registration, RegistrationRepository]):
            def __init__(self, db: Session):
                super().__init__(db, RegistrationRepository, user_id_field='user_id')
    """

    def __init__(
        self,
        db: Session,
        repository_class: Type[RepositoryType],
        user_id_field: str = 'user_id'
    ):
        """
        Initialize owned resource service

        Args:
            db: Database session
            repository_class: Repository class
            user_id_field: Field name for user ownership (default: 'user_id')
        """
        super().__init__(db, repository_class)
        self.user_id_field = user_id_field

    def check_ownership_for_resource(
        self,
        resource: ModelType,
        current_user_id: int
    ) -> None:
        """
        Check if current user owns the resource

        Args:
            resource: Resource instance
            current_user_id: Current user ID

        Raises:
            PermissionDeniedException: If user doesn't own resource
        """
        resource_user_id = getattr(resource, self.user_id_field, None)
        if resource_user_id is None:
            raise ValueError(f"Resource does not have field '{self.user_id_field}'")

        self.check_ownership(resource_user_id, current_user_id, self.model_name)

    def update_owned(
        self,
        resource_id: int,
        data: Dict[str, Any],
        current_user_id: int
    ) -> ModelType:
        """
        Update resource with ownership check

        Args:
            resource_id: Resource ID
            data: Update data
            current_user_id: Current user ID

        Returns:
            Updated resource

        Raises:
            NotFoundException: If resource not found
            PermissionDeniedException: If user doesn't own resource
        """
        resource = self.get_by_id_or_404(resource_id)
        self.check_ownership_for_resource(resource, current_user_id)
        return self.update(resource_id, data)

    def delete_owned(self, resource_id: int, current_user_id: int) -> bool:
        """
        Delete resource with ownership check

        Args:
            resource_id: Resource ID
            current_user_id: Current user ID

        Returns:
            True if deleted

        Raises:
            NotFoundException: If resource not found
            PermissionDeniedException: If user doesn't own resource
        """
        resource = self.get_by_id_or_404(resource_id)
        self.check_ownership_for_resource(resource, current_user_id)
        return self.delete(resource_id)

    def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Get all resources for a specific user

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum records

        Returns:
            List of user's resources
        """
        filters = {self.user_id_field: user_id}
        return self.repository.find_by(**filters)
