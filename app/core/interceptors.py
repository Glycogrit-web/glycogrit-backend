"""
Interceptors for Request/Response Processing
Provides hooks to intercept and modify requests/responses
"""

import json
import logging
import time
from typing import Any

from fastapi import Request, Response

logger = logging.getLogger(__name__)


class RequestInterceptor:
    """
    Base class for request interceptors

    Interceptors can modify requests before they reach the endpoint
    and responses before they're returned to the client

    Usage:
        class AuthInterceptor(RequestInterceptor):
            async def before_request(self, request: Request):
                # Add custom headers
                request.state.start_time = time.time()

            async def after_request(self, request: Request, response: Response):
                # Add timing header
                duration = time.time() - request.state.start_time
                response.headers["X-Process-Time"] = str(duration)
                return response
    """

    async def before_request(self, request: Request) -> Response | None:
        """
        Called before request is processed

        Args:
            request: FastAPI Request object

        Returns:
            None to continue processing, or Response to short-circuit
        """
        pass

    async def after_request(self, request: Request, response: Response) -> Response:
        """
        Called after request is processed

        Args:
            request: FastAPI Request object
            response: FastAPI Response object

        Returns:
            Modified or original response
        """
        return response

    async def on_error(self, request: Request, error: Exception) -> Response | None:
        """
        Called when an error occurs

        Args:
            request: FastAPI Request object
            error: Exception that occurred

        Returns:
            None to re-raise error, or Response to handle it
        """
        pass


class LoggingInterceptor(RequestInterceptor):
    """
    Interceptor that logs all requests and responses

    Logs request details, response status, and timing information
    """

    def __init__(self, log_body: bool = False, log_headers: bool = False):
        """
        Initialize logging interceptor

        Args:
            log_body: Whether to log request/response bodies
            log_headers: Whether to log headers
        """
        self.log_body = log_body
        self.log_headers = log_headers

    async def before_request(self, request: Request) -> None:
        """Log incoming request"""
        request.state.start_time = time.time()
        request.state.request_id = request.headers.get("X-Request-ID", "unknown")

        log_data = {
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else "unknown",
            "request_id": request.state.request_id
        }

        if self.log_headers:
            log_data["headers"] = dict(request.headers)

        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                log_data["body"] = body.decode()
            except:
                log_data["body"] = "[Could not decode body]"

        logger.info(f"Incoming request: {json.dumps(log_data)}")

    async def after_request(self, request: Request, response: Response) -> Response:
        """Log outgoing response"""
        duration = time.time() - request.state.start_time

        log_data = {
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "request_id": request.state.request_id
        }

        if self.log_headers:
            log_data["headers"] = dict(response.headers)

        logger.info(f"Outgoing response: {json.dumps(log_data)}")

        # Add timing header
        response.headers["X-Process-Time"] = str(duration)

        return response

    async def on_error(self, request: Request, error: Exception) -> None:
        """Log errors"""
        duration = time.time() - request.state.start_time

        logger.error(
            f"Request failed: request_id={request.state.request_id}, "
            f"error={str(error)}, duration_ms={round(duration * 1000, 2)}"
        )


class MetricsInterceptor(RequestInterceptor):
    """
    Interceptor that collects metrics

    Tracks request counts, response times, error rates
    """

    def __init__(self):
        self.metrics = {
            "requests": 0,
            "errors": 0,
            "total_duration": 0.0,
            "by_endpoint": {},
            "by_status": {}
        }

    async def before_request(self, request: Request) -> None:
        """Track request start"""
        request.state.metrics_start = time.time()
        self.metrics["requests"] += 1

    async def after_request(self, request: Request, response: Response) -> Response:
        """Track response metrics"""
        duration = time.time() - request.state.metrics_start
        self.metrics["total_duration"] += duration

        # Track by endpoint
        endpoint = f"{request.method} {request.url.path}"
        if endpoint not in self.metrics["by_endpoint"]:
            self.metrics["by_endpoint"][endpoint] = {
                "count": 0,
                "total_duration": 0.0
            }

        self.metrics["by_endpoint"][endpoint]["count"] += 1
        self.metrics["by_endpoint"][endpoint]["total_duration"] += duration

        # Track by status code
        status = str(response.status_code)
        self.metrics["by_status"][status] = self.metrics["by_status"].get(status, 0) + 1

        return response

    async def on_error(self, request: Request, error: Exception) -> None:
        """Track errors"""
        self.metrics["errors"] += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get collected metrics"""
        return self.metrics.copy()

    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary"""
        total_requests = self.metrics["requests"]
        total_duration = self.metrics["total_duration"]

        return {
            "total_requests": total_requests,
            "total_errors": self.metrics["errors"],
            "error_rate": (self.metrics["errors"] / total_requests * 100) if total_requests > 0 else 0,
            "avg_response_time_ms": (total_duration / total_requests * 1000) if total_requests > 0 else 0,
            "by_status": self.metrics["by_status"]
        }


class CacheInterceptor(RequestInterceptor):
    """
    Interceptor that caches GET responses

    Caches responses for GET requests to improve performance
    """

    def __init__(self, ttl_seconds: int = 60):
        """
        Initialize cache interceptor

        Args:
            ttl_seconds: Time to live for cache entries
        """
        self.ttl_seconds = ttl_seconds
        self.cache: dict[str, tuple[Response, float]] = {}

    async def before_request(self, request: Request) -> Response | None:
        """Check cache for GET requests"""
        if request.method != "GET":
            return None

        cache_key = str(request.url)

        if cache_key in self.cache:
            response, cached_at = self.cache[cache_key]

            # Check if cache is still valid
            if time.time() - cached_at < self.ttl_seconds:
                logger.debug(f"Cache hit for {cache_key}")
                response.headers["X-Cache"] = "HIT"
                return response
            else:
                # Remove expired entry
                del self.cache[cache_key]

        return None

    async def after_request(self, request: Request, response: Response) -> Response:
        """Cache successful GET responses"""
        if request.method == "GET" and response.status_code == 200:
            cache_key = str(request.url)
            self.cache[cache_key] = (response, time.time())
            response.headers["X-Cache"] = "MISS"
            logger.debug(f"Cached response for {cache_key}")

        return response

    def clear_cache(self):
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("Cache cleared")


class ValidationInterceptor(RequestInterceptor):
    """
    Interceptor that validates requests

    Performs additional validation before request processing
    """

    def __init__(self, max_body_size: int = 10 * 1024 * 1024):  # 10MB default
        """
        Initialize validation interceptor

        Args:
            max_body_size: Maximum request body size in bytes
        """
        self.max_body_size = max_body_size

    async def before_request(self, request: Request) -> Response | None:
        """Validate request"""
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request body too large",
                    "max_size_bytes": self.max_body_size
                }
            )

        # Check content type for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not content_type:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=415,
                    content={"error": "Content-Type header required"}
                )

        return None


class InterceptorChain:
    """
    Manages a chain of interceptors

    Usage:
        chain = InterceptorChain()
        chain.add(LoggingInterceptor())
        chain.add(MetricsInterceptor())

        # In middleware
        await chain.process_request(request)
        response = await call_next(request)
        response = await chain.process_response(request, response)
    """

    def __init__(self):
        self.interceptors: list[RequestInterceptor] = []

    def add(self, interceptor: RequestInterceptor) -> 'InterceptorChain':
        """
        Add interceptor to chain

        Args:
            interceptor: Interceptor instance

        Returns:
            Self for chaining
        """
        self.interceptors.append(interceptor)
        return self

    async def process_request(self, request: Request) -> Response | None:
        """
        Process request through all interceptors

        Args:
            request: FastAPI Request

        Returns:
            Response if any interceptor short-circuits, None otherwise
        """
        for interceptor in self.interceptors:
            result = await interceptor.before_request(request)
            if result is not None:
                return result

        return None

    async def process_response(
        self,
        request: Request,
        response: Response
    ) -> Response:
        """
        Process response through all interceptors

        Args:
            request: FastAPI Request
            response: FastAPI Response

        Returns:
            Modified response
        """
        for interceptor in reversed(self.interceptors):
            response = await interceptor.after_request(request, response)

        return response

    async def process_error(
        self,
        request: Request,
        error: Exception
    ) -> Response | None:
        """
        Process error through all interceptors

        Args:
            request: FastAPI Request
            error: Exception that occurred

        Returns:
            Response if handled, None to re-raise
        """
        for interceptor in self.interceptors:
            result = await interceptor.on_error(request, error)
            if result is not None:
                return result

        return None


# Global interceptor chain
global_interceptor_chain = InterceptorChain()
