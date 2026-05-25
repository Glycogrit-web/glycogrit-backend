"""
Response Builder Utility

Provides standardized response formatting across all API endpoints.
"""

import uuid
from datetime import datetime
from typing import Any


class ResponseBuilder:
    """
    Builder class for standardized API responses.

    Ensures consistent response structure across all endpoints.
    """

    @staticmethod
    def success(
        data: Any = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Build a success response

        Args:
            data: Response data
            message: Optional success message
            metadata: Optional metadata

        Returns:
            Standardized success response dictionary
        """
        response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat()
        }

        if data is not None:
            response["data"] = data

        if message:
            response["message"] = message

        if metadata:
            response["metadata"] = metadata

        return response

    @staticmethod
    def error(
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Build an error response

        Args:
            message: Error message
            error_code: Optional error code
            details: Optional error details

        Returns:
            Standardized error response dictionary
        """
        response = {
            "success": False,
            "error": {
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        if error_code:
            response["error"]["code"] = error_code

        if details:
            response["error"]["details"] = details

        return response

    @staticmethod
    def paginated(
        items: list[Any],
        total: int,
        page: int,
        page_size: int,
        message: str | None = None
    ) -> dict[str, Any]:
        """
        Build a paginated response

        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            page_size: Items per page
            message: Optional message

        Returns:
            Standardized paginated response
        """
        total_pages = (total + page_size - 1) // page_size

        response = {
            "success": True,
            "data": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        if message:
            response["message"] = message

        return response

    @staticmethod
    def created(
        data: Any,
        message: str | None = None,
        resource_id: int | None = None
    ) -> dict[str, Any]:
        """
        Build a resource created response

        Args:
            data: Created resource data
            message: Optional success message
            resource_id: Optional resource ID

        Returns:
            Standardized creation response
        """
        response = ResponseBuilder.success(data, message)
        response["created"] = True

        if resource_id:
            response["resource_id"] = resource_id

        return response

    @staticmethod
    def updated(
        data: Any,
        message: str | None = None
    ) -> dict[str, Any]:
        """
        Build a resource updated response

        Args:
            data: Updated resource data
            message: Optional success message

        Returns:
            Standardized update response
        """
        response = ResponseBuilder.success(data, message or "Resource updated successfully")
        response["updated"] = True
        return response

    @staticmethod
    def deleted(
        message: str | None = None,
        resource_id: int | None = None
    ) -> dict[str, Any]:
        """
        Build a resource deleted response

        Args:
            message: Optional success message
            resource_id: Optional resource ID

        Returns:
            Standardized deletion response
        """
        response = ResponseBuilder.success(
            message=message or "Resource deleted successfully"
        )
        response["deleted"] = True

        if resource_id:
            response["resource_id"] = resource_id

        return response

    @staticmethod
    def validation_error(
        errors: dict[str, list[str]],
        message: str | None = None
    ) -> dict[str, Any]:
        """
        Build a validation error response

        Args:
            errors: Dictionary mapping field names to error messages
            message: Optional general message

        Returns:
            Standardized validation error response
        """
        return ResponseBuilder.error(
            message=message or "Validation failed",
            error_code="VALIDATION_ERROR",
            details={"field_errors": errors}
        )

    @staticmethod
    def not_found(
        resource: str = "Resource",
        resource_id: int | None = None
    ) -> dict[str, Any]:
        """
        Build a not found error response

        Args:
            resource: Resource name
            resource_id: Optional resource ID

        Returns:
            Standardized not found response
        """
        message = f"{resource} not found"
        if resource_id:
            message += f" (ID: {resource_id})"

        return ResponseBuilder.error(
            message=message,
            error_code="NOT_FOUND"
        )

    @staticmethod
    def unauthorized(
        message: str | None = None
    ) -> dict[str, Any]:
        """
        Build an unauthorized error response

        Args:
            message: Optional custom message

        Returns:
            Standardized unauthorized response
        """
        return ResponseBuilder.error(
            message=message or "Unauthorized access",
            error_code="UNAUTHORIZED"
        )

    @staticmethod
    def forbidden(
        message: str | None = None
    ) -> dict[str, Any]:
        """
        Build a forbidden error response

        Args:
            message: Optional custom message

        Returns:
            Standardized forbidden response
        """
        return ResponseBuilder.error(
            message=message or "Access forbidden",
            error_code="FORBIDDEN"
        )

    @staticmethod
    def conflict(
        message: str,
        details: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Build a conflict error response

        Args:
            message: Error message
            details: Optional conflict details

        Returns:
            Standardized conflict response
        """
        return ResponseBuilder.error(
            message=message,
            error_code="CONFLICT",
            details=details
        )

    @staticmethod
    def with_request_id(
        response: dict[str, Any],
        request_id: str | None = None
    ) -> dict[str, Any]:
        """
        Add request ID to response

        Args:
            response: Response dictionary
            request_id: Optional request ID (generates one if not provided)

        Returns:
            Response with request_id added
        """
        response["request_id"] = request_id or str(uuid.uuid4())
        return response
