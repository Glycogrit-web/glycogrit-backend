"""
Base API Router and Response Utilities
Reduces boilerplate in API endpoints
"""

from typing import Any, Optional, List, Dict, TypeVar, Generic
from pydantic import BaseModel
from fastapi import Query
from datetime import datetime


# ==================== Response Models ====================

class BaseResponse(BaseModel):
    """Base response model with success indicator"""
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


class DataResponse(BaseResponse, Generic[TypeVar("T")]):
    """Response with data payload"""
    data: Any


class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseResponse):
    """Paginated response with metadata"""
    data: List[Any]
    pagination: PaginationMeta


# ==================== Response Builders ====================

class ResponseBuilder:
    """
    Utility class for building standardized API responses

    Usage:
        return ResponseBuilder.success(data={"id": 1, "name": "John"})
        return ResponseBuilder.error("User not found", error_code="USER_NOT_FOUND")
        return ResponseBuilder.paginated(items, total=100, page=1, size=20)
    """

    @staticmethod
    def success(
        data: Any = None,
        message: Optional[str] = None,
        **extra_fields
    ) -> Dict[str, Any]:
        """
        Build success response

        Args:
            data: Response data
            message: Optional success message
            **extra_fields: Additional fields to include

        Returns:
            Response dictionary
        """
        response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if message:
            response["message"] = message

        if data is not None:
            response["data"] = data

        response.update(extra_fields)

        return response

    @staticmethod
    def error(
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **extra_fields
    ) -> Dict[str, Any]:
        """
        Build error response

        Args:
            message: Error message
            error_code: Optional error code
            details: Additional error details
            **extra_fields: Additional fields to include

        Returns:
            Error response dictionary
        """
        response = {
            "success": False,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if error_code:
            response["error_code"] = error_code

        if details:
            response["details"] = details

        response.update(extra_fields)

        return response

    @staticmethod
    def paginated(
        items: List[Any],
        total: int,
        page: int,
        page_size: int,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build paginated response

        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number (1-indexed)
            page_size: Number of items per page
            message: Optional message

        Returns:
            Paginated response dictionary
        """
        total_pages = (total + page_size - 1) // page_size  # Ceiling division

        response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }

        if message:
            response["message"] = message

        return response

    @staticmethod
    def created(
        data: Any,
        message: str = "Resource created successfully"
    ) -> Dict[str, Any]:
        """Build response for resource creation"""
        return ResponseBuilder.success(data=data, message=message)

    @staticmethod
    def updated(
        data: Any,
        message: str = "Resource updated successfully"
    ) -> Dict[str, Any]:
        """Build response for resource update"""
        return ResponseBuilder.success(data=data, message=message)

    @staticmethod
    def deleted(
        message: str = "Resource deleted successfully"
    ) -> Dict[str, Any]:
        """Build response for resource deletion"""
        return ResponseBuilder.success(message=message)

    @staticmethod
    def no_content() -> Dict[str, Any]:
        """Build response for no content"""
        return {"success": True}


# ==================== Pagination Utilities ====================

class PaginationParams:
    """
    Reusable pagination parameters for FastAPI endpoints

    Usage:
        @router.get("/users")
        async def list_users(pagination: PaginationParams = Depends()):
            skip = pagination.get_skip()
            limit = pagination.get_limit()
            return db.query(User).offset(skip).limit(limit).all()
    """

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page")
    ):
        self.page = page
        self.page_size = page_size

    def get_skip(self) -> int:
        """Get offset for database query"""
        return (self.page - 1) * self.page_size

    def get_limit(self) -> int:
        """Get limit for database query"""
        return self.page_size

    def build_response(
        self,
        items: List[Any],
        total: int,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build paginated response"""
        return ResponseBuilder.paginated(
            items=items,
            total=total,
            page=self.page,
            page_size=self.page_size,
            message=message
        )


# ==================== Common Query Parameters ====================

class SortParams:
    """
    Reusable sorting parameters

    Usage:
        @router.get("/users")
        async def list_users(sort: SortParams = Depends()):
            query = db.query(User)
            query = sort.apply(query, default_field="created_at")
            return query.all()
    """

    def __init__(
        self,
        sort_by: Optional[str] = Query(None, description="Field to sort by"),
        sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order (asc/desc)")
    ):
        self.sort_by = sort_by
        self.sort_order = sort_order

    def apply(self, query, default_field: str = "id"):
        """
        Apply sorting to SQLAlchemy query

        Args:
            query: SQLAlchemy query object
            default_field: Default field to sort by if sort_by is None

        Returns:
            Modified query with sorting applied
        """
        from sqlalchemy import asc, desc

        sort_field = self.sort_by or default_field

        # Get the model from the query
        model = query.column_descriptions[0]['entity']

        if hasattr(model, sort_field):
            field = getattr(model, sort_field)
            if self.sort_order == "asc":
                query = query.order_by(asc(field))
            else:
                query = query.order_by(desc(field))

        return query


class FilterParams:
    """
    Reusable filter parameters

    Usage:
        @router.get("/events")
        async def list_events(filters: FilterParams = Depends()):
            query = db.query(Event)
            if filters.is_active is not None:
                query = query.filter(Event.is_active == filters.is_active)
            return query.all()
    """

    def __init__(
        self,
        is_active: Optional[bool] = Query(None, description="Filter by active status"),
        search: Optional[str] = Query(None, description="Search term"),
        created_after: Optional[datetime] = Query(None, description="Filter by creation date (after)"),
        created_before: Optional[datetime] = Query(None, description="Filter by creation date (before)")
    ):
        self.is_active = is_active
        self.search = search
        self.created_after = created_after
        self.created_before = created_before


# ==================== List/Detail Response Helpers ====================

def list_response(
    items: List[Any],
    total: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick helper for list responses

    Usage:
        items = db.query(User).all()
        return list_response(items, total=len(items))
    """
    if total is None:
        total = len(items)

    return ResponseBuilder.paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        message=message
    )


def detail_response(
    item: Any,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick helper for detail responses

    Usage:
        user = db.query(User).filter(User.id == user_id).first()
        return detail_response(user)
    """
    return ResponseBuilder.success(data=item, message=message)
