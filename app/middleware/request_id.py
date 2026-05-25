"""
Request ID Middleware

Adds a unique request ID to every incoming request for tracing and debugging.
The request ID can be:
1. Provided by the client via X-Request-ID header (for client-side tracing)
2. Auto-generated as a UUID if not provided

The request ID is:
- Stored in request.state.request_id for use throughout the request lifecycle
- Returned in the response X-Request-ID header for client correlation
- Available for logging and error tracking
"""
import logging
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.constants import HTTPHeaders

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to every request.

    Features:
    - Accepts client-provided request IDs via X-Request-ID header
    - Auto-generates UUID if no request ID provided
    - Stores request ID in request.state for access in routes
    - Returns request ID in response headers
    - Logs request ID for debugging

    Usage in routes:
        @app.get("/example")
        async def example(request: Request):
            request_id = request.state.request_id
            return {"request_id": request_id}
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process incoming request and add request ID.

        Args:
            request: FastAPI Request object
            call_next: Next middleware/route handler

        Returns:
            Response with X-Request-ID header
        """
        # Try to get request ID from headers (client-provided)
        request_id = request.headers.get(HTTPHeaders.X_REQUEST_ID)

        # If not provided, generate a new UUID
        if not request_id:
            request_id = str(uuid.uuid4())
            logger.debug(f"Generated new request ID: {request_id}")
        else:
            logger.debug(f"Using client-provided request ID: {request_id}")

        # Store request ID in request state for access throughout request lifecycle
        request.state.request_id = request_id

        # Log request details with request ID (DEBUG level to reduce noise)
        logger.debug(
            f"[{request_id}] {request.method} {request.url.path} "
            f"- Client: {request.client.host if request.client else 'unknown'}"
        )

        # Process the request
        try:
            response: Response = await call_next(request)

            # Add request ID to response headers for client correlation
            response.headers[HTTPHeaders.X_REQUEST_ID] = request_id

            # Only log errors and warnings, not successful requests (reduces log noise)
            if response.status_code >= 400:
                logger.warning(f"[{request_id}] Response status: {response.status_code}")
            else:
                logger.debug(f"[{request_id}] Response status: {response.status_code}")

            return response

        except Exception as e:
            # Log errors with request ID for debugging
            logger.error(f"[{request_id}] Request failed with error: {str(e)}", exc_info=True)
            raise
