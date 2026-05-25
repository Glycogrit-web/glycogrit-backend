"""
Advanced Middleware Utilities
Provides reusable middleware for common patterns
"""

import json
import logging
import time
from collections.abc import Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.interceptors import global_interceptor_chain

logger = logging.getLogger(__name__)


class InterceptorMiddleware(BaseHTTPMiddleware):
    """
    Middleware that processes requests through interceptor chain

    Usage:
        from app.core.interceptors import global_interceptor_chain, LoggingInterceptor

        global_interceptor_chain.add(LoggingInterceptor())

        app.add_middleware(InterceptorMiddleware)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through interceptor chain"""
        try:
            # Process request through interceptors
            short_circuit_response = await global_interceptor_chain.process_request(request)

            if short_circuit_response:
                return short_circuit_response

            # Call next middleware/endpoint
            response = await call_next(request)

            # Process response through interceptors
            response = await global_interceptor_chain.process_response(request, response)

            return response

        except Exception as error:
            # Try to handle error through interceptors
            error_response = await global_interceptor_chain.process_error(request, error)

            if error_response:
                return error_response

            # Re-raise if not handled
            raise


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware that monitors request performance

    Adds timing headers and logs slow requests
    """

    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold_ms: float = 1000.0,
        add_headers: bool = True
    ):
        """
        Initialize performance monitoring middleware

        Args:
            app: ASGI application
            slow_request_threshold_ms: Threshold for logging slow requests
            add_headers: Whether to add timing headers to response
        """
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms
        self.add_headers = add_headers

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor request performance"""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add timing headers if enabled
        if self.add_headers:
            response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
            response.headers["X-Process-Time"] = f"{duration_ms / 1000:.4f}"

        # Log slow requests
        if duration_ms > self.slow_request_threshold_ms:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {duration_ms:.2f}ms (threshold: {self.slow_request_threshold_ms}ms)"
            )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses

    Adds headers like X-Content-Type-Options, X-Frame-Options, etc.
    """

    def __init__(
        self,
        app: ASGIApp,
        custom_headers: dict[str, str] | None = None
    ):
        """
        Initialize security headers middleware

        Args:
            app: ASGI application
            custom_headers: Custom security headers to add
        """
        super().__init__(app)

        self.headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }

        if custom_headers:
            self.headers.update(custom_headers)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response"""
        response = await call_next(request)

        # Add all security headers
        for header, value in self.headers.items():
            response.headers[header] = value

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all requests with structured data

    Logs request details, response status, timing, and user info
    """

    def __init__(
        self,
        app: ASGIApp,
        log_body: bool = False,
        log_response: bool = False,
        exclude_paths: list[str] | None = None
    ):
        """
        Initialize request logging middleware

        Args:
            app: ASGI application
            log_body: Whether to log request bodies
            log_response: Whether to log response bodies
            exclude_paths: Paths to exclude from logging (e.g., health checks)
        """
        super().__init__(app)
        self.log_body = log_body
        self.log_response = log_response
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response"""
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        request_id = request.headers.get("X-Request-ID", "unknown")
        start_time = time.time()

        # Build request log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown")
        }

        # Log request body if enabled
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                log_data["body"] = body.decode()
            except:
                log_data["body"] = "[Could not decode body]"

        # Get user from request state if available
        if hasattr(request.state, "user"):
            log_data["user_id"] = getattr(request.state.user, "id", None)

        logger.info(f"Request started: {json.dumps(log_data)}")

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            response_log = {
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2)
            }

            if response.status_code >= 400:
                logger.error(f"Request failed: {json.dumps(response_log)}")
            else:
                logger.info(f"Request completed: {json.dumps(response_log)}")

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            logger.error(
                f"Request exception: {json.dumps({'request_id': request_id, 'error': str(e), 'duration_ms': round(duration_ms, 2)})}"
            )
            raise


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that compresses responses

    Compresses responses over a certain size threshold
    """

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 1024,
        compression_level: int = 6
    ):
        """
        Initialize compression middleware

        Args:
            app: ASGI application
            minimum_size: Minimum response size to compress (bytes)
            compression_level: Gzip compression level (1-9)
        """
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Compress response if appropriate"""
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return await call_next(request)

        response = await call_next(request)

        # Check if response should be compressed
        content_type = response.headers.get("content-type", "")
        if not any(ct in content_type.lower() for ct in ["application/json", "text/", "application/javascript"]):
            return response

        # Note: Actual compression implementation would go here
        # This is a simplified version showing the pattern
        # In production, use GZipMiddleware from starlette

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware

    Note: For production, use Redis-based rate limiting
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 100,
        window_seconds: int = 60,
        exempt_paths: list[str] | None = None
    ):
        """
        Initialize rate limit middleware

        Args:
            app: ASGI application
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            exempt_paths: Paths exempt from rate limiting
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exempt_paths = exempt_paths or []
        self.request_counts: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting"""
        # Skip exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Get client identifier (IP or user ID)
        client_id = request.client.host if request.client else "unknown"

        if hasattr(request.state, "user"):
            client_id = f"user_{request.state.user.id}"

        # Get current time
        current_time = time.time()

        # Initialize or clean up old requests
        if client_id not in self.request_counts:
            self.request_counts[client_id] = []

        # Remove requests outside the window
        self.request_counts[client_id] = [
            timestamp for timestamp in self.request_counts[client_id]
            if current_time - timestamp < self.window_seconds
        ]

        # Check if rate limit exceeded
        if len(self.request_counts[client_id]) >= self.max_requests:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "max_requests": self.max_requests,
                    "window_seconds": self.window_seconds
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0"
                }
            )

        # Add current request
        self.request_counts[client_id].append(current_time)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self.max_requests - len(self.request_counts[client_id])
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that provides centralized error handling

    Catches exceptions and returns formatted error responses
    """

    def __init__(
        self,
        app: ASGIApp,
        include_trace: bool = False,
        log_errors: bool = True
    ):
        """
        Initialize error handling middleware

        Args:
            app: ASGI application
            include_trace: Whether to include stack traces in error responses
            log_errors: Whether to log errors
        """
        super().__init__(app)
        self.include_trace = include_trace
        self.log_errors = log_errors

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle errors"""
        try:
            return await call_next(request)

        except Exception as error:
            if self.log_errors:
                logger.exception(f"Unhandled exception for {request.method} {request.url.path}")

            # Build error response
            from fastapi.responses import JSONResponse

            error_data = {
                "success": False,
                "error": str(error),
                "error_type": type(error).__name__,
                "timestamp": datetime.utcnow().isoformat()
            }

            if self.include_trace:
                import traceback
                error_data["trace"] = traceback.format_exc()

            return JSONResponse(
                status_code=500,
                content=error_data
            )
