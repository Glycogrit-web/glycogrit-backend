"""
Global Exception Handlers for FastAPI Application

Provides centralized exception handling with consistent error responses,
logging, and monitoring integration.
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import DatabaseError, IntegrityError, OperationalError

from app.core.exceptions import (
    AppException,
    ConcurrencyException,
    ExternalServiceException,
    PaymentException,
    PaymentGatewayException,
)

logger = logging.getLogger(__name__)


def create_error_response(
    status_code: int,
    message: str,
    error_code: str = "ERROR",
    details: dict[str, Any] = None,
    request_id: str = None,
) -> JSONResponse:
    """
    Create standardized error response.

    Args:
        status_code: HTTP status code
        message: Human-readable error message
        error_code: Machine-readable error code
        details: Additional error details
        request_id: Request ID for tracing

    Returns:
        JSONResponse with standardized error format
    """
    error_data = {
        "success": False,
        "error": {
            "message": message,
            "code": error_code,
            "timestamp": datetime.utcnow().isoformat(),
        },
    }

    if details:
        error_data["error"]["details"] = details

    if request_id:
        error_data["error"]["request_id"] = request_id

    return JSONResponse(status_code=status_code, content=error_data)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom application exceptions.

    All custom exceptions inherit from AppException and include:
    - Appropriate HTTP status code
    - Error code for client-side handling
    - Detailed context information
    """
    request_id = request.headers.get("X-Request-ID", "unknown")

    # Log based on severity
    if exc.status_code >= 500:
        logger.error(
            f"Application error: {exc.error_code} - {exc.message}",
            extra={
                "request_id": request_id,
                "path": str(request.url.path),
                "method": request.method,
                "error_code": exc.error_code,
                "details": exc.details,
                "status_code": exc.status_code,
            },
            exc_info=True,
        )
    elif exc.status_code >= 400:
        logger.warning(
            f"Client error: {exc.error_code} - {exc.message}",
            extra={
                "request_id": request_id,
                "path": str(request.url.path),
                "error_code": exc.error_code,
                "details": exc.details,
            },
        )

    return create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        request_id=request_id,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError | ValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Converts Pydantic validation errors into user-friendly format.
    """
    request_id = request.headers.get("X-Request-ID", "unknown")

    # Extract validation errors
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({"field": field_path, "message": error["msg"], "type": error["type"]})

    logger.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={"request_id": request_id, "validation_errors": errors},
    )

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Request validation failed",
        error_code="VALIDATION_ERROR",
        details={"validation_errors": errors},
        request_id=request_id,
    )


async def database_exception_handler(
    request: Request, exc: IntegrityError | OperationalError | DatabaseError
) -> JSONResponse:
    """
    Handle SQLAlchemy database exceptions.

    Catches database errors and provides appropriate responses:
    - IntegrityError: Constraint violations (409 Conflict)
    - OperationalError: Connection/timeout issues (503 Service Unavailable)
    - DatabaseError: General database errors (500 Internal Server Error)
    """
    request_id = request.headers.get("X-Request-ID", "unknown")

    # Determine appropriate status code and message
    if isinstance(exc, IntegrityError):
        status_code = status.HTTP_409_CONFLICT
        error_code = "DATABASE_CONSTRAINT_VIOLATION"

        # Extract constraint name if available
        constraint_name = _extract_constraint_name(str(exc))
        message = _get_user_friendly_constraint_message(constraint_name)

        details = {"constraint": constraint_name} if constraint_name else {}

        logger.warning(
            f"Database integrity error: {message}",
            extra={
                "request_id": request_id,
                "constraint": constraint_name,
                "original_error": str(exc.orig) if hasattr(exc, "orig") else str(exc),
            },
        )

    elif isinstance(exc, OperationalError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        error_code = "DATABASE_UNAVAILABLE"
        message = "Database service temporarily unavailable. Please try again later."
        details = {"is_retryable": True}

        logger.error(
            f"Database operational error: {str(exc)}",
            extra={"request_id": request_id, "path": str(request.url.path)},
            exc_info=True,
        )

    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "DATABASE_ERROR"
        message = "A database error occurred. Please try again or contact support."
        details = {}

        logger.error(
            f"Database error: {str(exc)}",
            extra={"request_id": request_id, "path": str(request.url.path)},
            exc_info=True,
        )

    return create_error_response(
        status_code=status_code,
        message=message,
        error_code=error_code,
        details=details,
        request_id=request_id,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Catches all unhandled exceptions to prevent exposing sensitive information
    while ensuring proper logging for debugging.
    """
    request_id = request.headers.get("X-Request-ID", "unknown")

    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "method": request.method,
            "exception_type": type(exc).__name__,
        },
        exc_info=True,
    )

    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred. Please try again or contact support.",
        error_code="INTERNAL_SERVER_ERROR",
        details={"type": type(exc).__name__},
        request_id=request_id,
    )


def _extract_constraint_name(error_message: str) -> str:
    """Extract constraint name from database error message."""
    import re

    # PostgreSQL constraint pattern
    match = re.search(r'constraint "([^"]+)"', error_message)
    if match:
        return match.group(1)

    # MySQL constraint pattern
    match = re.search(r"Duplicate entry .+ for key '([^']+)'", error_message)
    if match:
        return match.group(1)

    return "unknown"


def _get_user_friendly_constraint_message(constraint_name: str) -> str:
    """
    Convert database constraint names to user-friendly messages.

    Maps common constraint violations to readable error messages.
    """
    constraint_messages = {
        # User constraints
        "users_email_key": "An account with this email already exists",
        "users_phone_key": "An account with this phone number already exists",
        # Registration constraints
        "registrations_user_event_unique": "You are already registered for this event",
        "registrations_registration_number_key": "Registration number conflict. Please try again.",
        # Payment constraints
        "payments_transaction_id_key": "Payment transaction already processed",
        "payments_order_id_unique": "Payment order already exists",
        # Tier constraints
        "registration_tier_unique": "Tier registration already exists",
        "tier_capacity_check": "Tier capacity exceeded",
        # Foreign key constraints
        "fk_registration_user": "User does not exist",
        "fk_registration_event": "Event does not exist",
        "fk_payment_registration": "Registration does not exist",
        "fk_tier_event": "Event does not exist",
    }

    return constraint_messages.get(
        constraint_name,
        "A database constraint was violated. Please check your input and try again.",
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI application.

    Usage:
        from app.core.exception_handlers import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
    """
    # Custom application exceptions
    app.add_exception_handler(AppException, app_exception_handler)

    # Validation exceptions
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)

    # Database exceptions
    app.add_exception_handler(IntegrityError, database_exception_handler)
    app.add_exception_handler(OperationalError, database_exception_handler)
    app.add_exception_handler(DatabaseError, database_exception_handler)

    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered successfully")


# ==================== Context Managers for Better Error Handling ====================


@contextmanager
def handle_payment_errors(
    operation: str, payment_id: int | None = None, order_id: str | None = None
):
    """
    Context manager for payment operations with enhanced error handling.

    Usage:
        with handle_payment_errors("payment verification", order_id=order_id):
            # Payment processing logic
            gateway.verify_payment(...)
    """
    try:
        yield
    except PaymentGatewayException:
        # Re-raise gateway exceptions as-is
        raise
    except PaymentException:
        # Re-raise payment exceptions as-is
        raise
    except IntegrityError as e:
        logger.error(f"Payment {operation} integrity error: {str(e)}")
        raise PaymentException(
            f"Payment {operation} failed due to data conflict",
            payment_id=payment_id,
            order_id=order_id,
        )
    except OperationalError as e:
        logger.error(f"Payment {operation} operational error: {str(e)}")
        raise PaymentGatewayException(
            f"Payment {operation} failed. Please try again.", gateway="database", is_retryable=True
        )
    except Exception as e:
        logger.error(f"Unexpected error during payment {operation}: {str(e)}", exc_info=True)
        raise PaymentException(
            f"An unexpected error occurred during payment {operation}",
            payment_id=payment_id,
            order_id=order_id,
        )


@contextmanager
def handle_external_service_errors(service_name: str, operation: str):
    """
    Context manager for external service calls with retry indication.

    Usage:
        with handle_external_service_errors("Razorpay", "create order"):
            response = razorpay_client.order.create(...)
    """
    try:
        yield
    except ExternalServiceException:
        # Re-raise external service exceptions as-is
        raise
    except requests.exceptions.Timeout:
        logger.error(f"{service_name} {operation} timeout")
        raise ExternalServiceException(
            f"{service_name} request timed out. Please try again.",
            service_name=service_name,
            is_retryable=True,
        )
    except requests.exceptions.ConnectionError:
        logger.error(f"{service_name} {operation} connection error")
        raise ExternalServiceException(
            f"Could not connect to {service_name}. Please try again later.",
            service_name=service_name,
            is_retryable=True,
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"{service_name} {operation} request error: {str(e)}")
        raise ExternalServiceException(
            f"{service_name} request failed: {str(e)}", service_name=service_name, is_retryable=True
        )
    except Exception as e:
        logger.error(
            f"Unexpected error calling {service_name} for {operation}: {str(e)}", exc_info=True
        )
        raise ExternalServiceException(
            f"An unexpected error occurred while calling {service_name}",
            service_name=service_name,
            is_retryable=False,
        )


@contextmanager
def handle_concurrency_errors(resource: str, resource_id: int | None = None):
    """
    Context manager for operations prone to race conditions.

    Usage:
        with handle_concurrency_errors("tier", tier_id=tier_id):
            # Check capacity and register
            tier_service.check_capacity(tier_id)
            registration_service.create(...)
    """
    try:
        yield
    except ConcurrencyException:
        # Re-raise concurrency exceptions as-is
        raise
    except IntegrityError as e:
        error_msg = str(e)
        if "capacity" in error_msg.lower() or "sold_out" in error_msg.lower():
            logger.warning(f"{resource} capacity exceeded due to concurrent operations")
            from app.core.exceptions import CapacityRaceConditionException

            raise CapacityRaceConditionException(resource, resource_id)
        else:
            logger.error(f"Integrity error in {resource} operation: {error_msg}")
            raise ConcurrencyException(
                f"Concurrent modification detected for {resource}",
                resource=resource,
                resource_id=resource_id,
            )
    except Exception as e:
        logger.error(f"Unexpected error in {resource} operation: {str(e)}", exc_info=True)
        raise


# Import requests for external service error handling
try:
    import requests
except ImportError:
    # If requests is not installed, create dummy exception classes
    class requests:
        class exceptions:
            class RequestException(Exception):
                pass

            class Timeout(RequestException):
                pass

            class ConnectionError(RequestException):
                pass
