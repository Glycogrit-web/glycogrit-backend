"""
Dependency Injection Helpers
Reusable FastAPI dependencies for common patterns
"""

from typing import Optional, Type, TypeVar, Callable, Any
from fastapi import Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.core.exceptions import NotFoundException
from app.core.repository.base import BaseRepository

# Type variables
ModelType = TypeVar("ModelType")
RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)


# ==================== Common Dependencies ====================

def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Reusable pagination parameters

    Usage:
        @router.get("/users")
        async def list_users(pagination=Depends(get_pagination_params)):
            skip = (pagination["page"] - 1) * pagination["page_size"]
            limit = pagination["page_size"]
    """
    return {
        "page": page,
        "page_size": page_size,
        "skip": (page - 1) * page_size,
        "limit": page_size
    }


def get_sort_params(
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    """
    Reusable sorting parameters

    Usage:
        @router.get("/users")
        async def list_users(sort=Depends(get_sort_params)):
            # sort["sort_by"], sort["sort_order"]
    """
    return {
        "sort_by": sort_by,
        "sort_order": sort_order
    }


def get_filter_params(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search term")
):
    """
    Reusable filter parameters

    Usage:
        @router.get("/users")
        async def list_users(filters=Depends(get_filter_params)):
            if filters["is_active"] is not None:
                query = query.filter(User.is_active == filters["is_active"])
    """
    return {
        "is_active": is_active,
        "search": search
    }


# ==================== Resource Dependencies ====================

class ResourceDependency:
    """
    Factory for creating resource dependencies

    Automatically fetches resources and raises 404 if not found

    Usage:
        get_event = ResourceDependency(Event, EventRepository)

        @router.get("/events/{event_id}")
        async def get_event_detail(event: Event = Depends(get_event)):
            return event
    """

    def __init__(
        self,
        model: Type[ModelType],
        repository_class: Type[RepositoryType],
        id_param_name: str = "id",
        resource_name: Optional[str] = None
    ):
        """
        Initialize resource dependency

        Args:
            model: SQLAlchemy model class
            repository_class: Repository class
            id_param_name: Name of the ID parameter in path
            resource_name: Human-readable resource name for errors
        """
        self.model = model
        self.repository_class = repository_class
        self.id_param_name = id_param_name
        self.resource_name = resource_name or model.__name__

    def __call__(
        self,
        resource_id: int = Path(..., alias=None),
        db: Session = Depends(get_db)
    ) -> ModelType:
        """Fetch resource or raise 404"""
        repository = self.repository_class(self.model, db)
        resource = repository.get_by_id(resource_id)

        if not resource:
            raise NotFoundException(self.resource_name, resource_id)

        return resource


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get current active user

    Usage:
        @router.get("/me")
        async def get_profile(user: User = Depends(get_current_active_user)):
            return user
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to require admin user

    Usage:
        @router.post("/admin/settings")
        async def update_settings(admin: User = Depends(get_current_admin_user)):
            pass
    """
    if current_user.role not in ('admin', 'super_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ==================== Service Dependencies ====================

class ServiceDependency:
    """
    Factory for creating service dependencies

    Automatically instantiates services with database session

    Usage:
        get_user_service = ServiceDependency(UserService)

        @router.post("/users")
        async def create_user(
            data: UserCreate,
            service: UserService = Depends(get_user_service)
        ):
            return service.create(data.dict())
    """

    def __init__(self, service_class: Type):
        """
        Initialize service dependency

        Args:
            service_class: Service class to instantiate
        """
        self.service_class = service_class

    def __call__(self, db: Session = Depends(get_db)):
        """Instantiate service with database session"""
        return self.service_class(db)


# ==================== Validation Dependencies ====================

class ValidateResourceOwnership:
    """
    Dependency to validate resource ownership

    Usage:
        validate_event_ownership = ValidateResourceOwnership(
            Event, EventRepository, user_field="organizer_id"
        )

        @router.put("/events/{event_id}")
        async def update_event(
            event_id: int,
            _: None = Depends(validate_event_ownership)
        ):
            # Ownership already validated
            pass
    """

    def __init__(
        self,
        model: Type[ModelType],
        repository_class: Type[RepositoryType],
        user_field: str = "user_id",
        resource_name: Optional[str] = None
    ):
        """
        Initialize ownership validation

        Args:
            model: SQLAlchemy model class
            repository_class: Repository class
            user_field: Field name for user ownership
            resource_name: Human-readable resource name
        """
        self.model = model
        self.repository_class = repository_class
        self.user_field = user_field
        self.resource_name = resource_name or model.__name__

    def __call__(
        self,
        resource_id: int = Path(...),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> None:
        """Validate ownership"""
        repository = self.repository_class(self.model, db)
        resource = repository.get_by_id(resource_id)

        if not resource:
            raise NotFoundException(self.resource_name, resource_id)

        resource_user_id = getattr(resource, self.user_field, None)
        if resource_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to access this {self.resource_name}"
            )


# ==================== Combined Dependencies ====================

def get_resource_with_ownership_check(
    model: Type[ModelType],
    repository_class: Type[RepositoryType],
    user_field: str = "user_id"
):
    """
    Create dependency that fetches resource AND validates ownership

    Usage:
        get_owned_event = get_resource_with_ownership_check(
            Event, EventRepository, user_field="organizer_id"
        )

        @router.put("/events/{event_id}")
        async def update_event(
            event: Event = Depends(get_owned_event)
        ):
            # Event fetched and ownership validated
            return event
    """
    def dependency(
        resource_id: int = Path(...),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> ModelType:
        repository = repository_class(model, db)
        resource = repository.get_by_id(resource_id)

        if not resource:
            raise NotFoundException(model.__name__, resource_id)

        resource_user_id = getattr(resource, user_field, None)
        if resource_user_id != current_user.id:
            # Allow admins
            if current_user.role not in ('admin', 'super_admin'):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You don't have permission to access this {model.__name__}"
                )

        return resource

    return dependency


def get_paginated_query_params():
    """
    Combined pagination, sorting, and filtering

    Usage:
        @router.get("/users")
        async def list_users(params=Depends(get_paginated_query_params)):
            # params contains: page, page_size, skip, limit, sort_by, sort_order, filters
            pass
    """
    def dependency(
        pagination=Depends(get_pagination_params),
        sort=Depends(get_sort_params),
        filters=Depends(get_filter_params)
    ):
        return {
            **pagination,
            **sort,
            "filters": filters
        }

    return dependency


# ==================== Custom Dependency Builder ====================

class DependencyBuilder:
    """
    Builder for creating custom dependencies

    Usage:
        get_user = DependencyBuilder() \\
            .with_model(User, UserRepository) \\
            .with_ownership_check(user_field="id") \\
            .with_active_check() \\
            .build()

        @router.get("/users/{user_id}")
        async def get_user(user: User = Depends(get_user)):
            return user
    """

    def __init__(self):
        self._model = None
        self._repository_class = None
        self._check_ownership = False
        self._user_field = "user_id"
        self._check_active = False
        self._require_admin = False

    def with_model(
        self,
        model: Type[ModelType],
        repository_class: Type[RepositoryType]
    ) -> 'DependencyBuilder':
        """Set model and repository"""
        self._model = model
        self._repository_class = repository_class
        return self

    def with_ownership_check(self, user_field: str = "user_id") -> 'DependencyBuilder':
        """Add ownership validation"""
        self._check_ownership = True
        self._user_field = user_field
        return self

    def with_active_check(self) -> 'DependencyBuilder':
        """Add active status check"""
        self._check_active = True
        return self

    def require_admin(self) -> 'DependencyBuilder':
        """Require admin access"""
        self._require_admin = True
        return self

    def build(self) -> Callable:
        """Build the dependency function"""
        model = self._model
        repository_class = self._repository_class
        check_ownership = self._check_ownership
        user_field = self._user_field
        check_active = self._check_active
        require_admin = self._require_admin

        def dependency(
            resource_id: int = Path(...),
            current_user: User = Depends(get_current_user),
            db: Session = Depends(get_db)
        ) -> ModelType:
            # Check admin requirement
            if require_admin and current_user.role not in ('admin', 'super_admin'):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )

            # Fetch resource
            repository = repository_class(model, db)
            resource = repository.get_by_id(resource_id)

            if not resource:
                raise NotFoundException(model.__name__, resource_id)

            # Check ownership
            if check_ownership:
                resource_user_id = getattr(resource, user_field, None)
                if resource_user_id != current_user.id and current_user.role not in ('admin', 'super_admin'):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"You don't have permission to access this {model.__name__}"
                    )

            # Check active status
            if check_active and hasattr(resource, 'is_active'):
                if not resource.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"{model.__name__} is not active"
                    )

            return resource

        return dependency
