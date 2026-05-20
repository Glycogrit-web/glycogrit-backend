"""
Rate Limiting Configuration

Provides rate limiting functionality to prevent API abuse and ensure fair usage.
Uses slowapi library for in-memory rate limiting.

Rate Limit Strategy:
- Authentication endpoints: Stricter limits (5-10 requests/minute)
- Read operations: Moderate limits (30-60 requests/minute)
- Write operations: Balanced limits (20 requests/minute)
- Admin operations: Very strict limits (10 requests/hour)
"""
from typing import Callable, Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
import logging

logger = logging.getLogger(__name__)


def get_client_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.

    Priority:
    1. User ID from authenticated request (if available)
    2. Client IP address

    Args:
        request: FastAPI Request object

    Returns:
        str: Unique identifier for the client
    """
    # Try to get user ID from request state (set by auth middleware)
    user_id: Optional[int] = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    # Fall back to IP address
    ip_address: str = get_remote_address(request)
    return f"ip:{ip_address}"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.

    Provides detailed error messages and includes request ID for debugging.

    Args:
        request: FastAPI Request object
        exc: RateLimitExceeded exception

    Returns:
        Response: JSON response with rate limit error details
    """
    from fastapi.responses import JSONResponse

    # Get request ID from request state (set by RequestIDMiddleware)
    request_id: Optional[str] = getattr(request.state, "request_id", None)

    logger.warning(
        f"[{request_id}] Rate limit exceeded for {request.url.path} "
        f"- Client: {get_client_identifier(request)}"
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "RateLimitExceeded",
            "message": "Too many requests. Please try again later.",
            "detail": str(exc.detail) if hasattr(exc, 'detail') else "Rate limit exceeded",
            "status_code": 429,
            "request_id": request_id
        },
        headers={
            "X-Request-ID": request_id if request_id else "",
            "Retry-After": "60"  # Suggest retry after 60 seconds
        }
    )


# Initialize limiter with custom key function
limiter: Limiter = Limiter(
    key_func=get_client_identifier,
    default_limits=["100/minute"],  # Global default limit
    storage_uri="memory://",  # Use in-memory storage (can be Redis in production)
    strategy="fixed-window",  # Fixed window strategy
    headers_enabled=True,  # Add rate limit headers to responses
)


# Rate limit presets for different endpoint types
class RateLimits:
    """
    Predefined rate limit configurations for different types of endpoints.

    Usage:
        from app.core.rate_limit import limiter, RateLimits

        @router.post("/login")
        @limiter.limit(RateLimits.AUTH)
        async def login(...):
            pass
    """

    # Default rate limit
    DEFAULT: str = "60/minute"  # Default for most endpoints

    # Authentication endpoints (stricter limits)
    AUTH: str = "5/minute"  # Login, register, password reset
    AUTH_VERIFY: str = "10/minute"  # Email verification, token refresh

    # Read operations (moderate limits)
    READ_LIST: str = "60/minute"  # List endpoints (events, activities)
    READ_DETAIL: str = "100/minute"  # Detail endpoints (single resource)
    READ_SEARCH: str = "30/minute"  # Search endpoints

    # Write operations (balanced limits)
    WRITE_CREATE: str = "20/minute"  # Create operations
    WRITE_UPDATE: str = "30/minute"  # Update operations
    WRITE_DELETE: str = "10/minute"  # Delete operations

    # Admin operations (very strict)
    ADMIN: str = "10/hour"  # Admin-only operations

    # Public endpoints (lenient limits)
    PUBLIC: str = "100/minute"  # Health checks, public info

    # File uploads (very strict)
    FILE_UPLOAD: str = "5/minute"  # File upload endpoints
    UPLOAD: str = "5/minute"  # Alias for FILE_UPLOAD


def apply_rate_limit(limit: str) -> Callable:
    """
    Decorator to apply rate limiting to endpoints.

    This is a convenience wrapper around limiter.limit() for better type hints.

    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour")

    Returns:
        Callable: Decorated function with rate limiting

    Example:
        @router.post("/events")
        @apply_rate_limit(RateLimits.WRITE_CREATE)
        async def create_event(...):
            pass
    """
    return limiter.limit(limit)


# Export commonly used components
__all__ = [
    "limiter",
    "RateLimits",
    "apply_rate_limit",
    "rate_limit_exceeded_handler",
    "get_client_identifier",
]
