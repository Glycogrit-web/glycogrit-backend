"""
Retry Handler for Shiprocket API Calls
Implements exponential backoff and circuit breaker pattern
"""

import asyncio
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when Shiprocket rate limit is exceeded"""

    pass


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is OPEN or function fails
        """
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker: OPEN → HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("Circuit breaker: HALF_OPEN → CLOSED (service recovered)")

        self.failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(
                f"Circuit breaker: CLOSED → OPEN "
                f"(failures: {self.failure_count}/{self.failure_threshold})"
            )


class RetryHandler:
    """
    Handles retry logic with exponential backoff.

    Official Shiprocket Rate Limits:
    - 100 requests/minute
    - HTTP 429: Rate limit exceeded
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        """
        Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

        # Circuit breaker for Shiprocket API
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5, recovery_timeout=60, expected_exception=Exception
        )

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt using exponential backoff.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)
        return delay

    async def retry_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retries exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Check circuit breaker
                if self.circuit_breaker.state == "OPEN":
                    raise Exception("Service unavailable (circuit breaker OPEN)")

                # Execute function
                result = await func(*args, **kwargs)

                # Success - reset circuit breaker
                self.circuit_breaker._on_success()

                if attempt > 0:
                    logger.info(f"✅ Retry successful on attempt {attempt + 1}")

                return result

            except httpx.HTTPStatusError as e:
                last_exception = e

                # Handle specific HTTP status codes
                if e.response.status_code == 429:
                    # Rate limit exceeded
                    logger.warning(
                        f"⚠️ Rate limit exceeded (429), attempt {attempt + 1}/{self.max_retries + 1}"
                    )

                    if attempt < self.max_retries:
                        # Use Retry-After header if provided
                        retry_after = e.response.headers.get("Retry-After")
                        if retry_after:
                            delay = float(retry_after)
                        else:
                            delay = self.calculate_delay(attempt)

                        logger.info(f"   Retrying in {delay:.1f} seconds...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise RateLimitExceeded("Shiprocket rate limit exceeded") from e

                elif e.response.status_code in [500, 502, 503, 504]:
                    # Server errors - retry
                    logger.warning(
                        f"⚠️ Server error ({e.response.status_code}), attempt {attempt + 1}/{self.max_retries + 1}"
                    )

                    if attempt < self.max_retries:
                        delay = self.calculate_delay(attempt)
                        logger.info(f"   Retrying in {delay:.1f} seconds...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        self.circuit_breaker._on_failure()
                        raise

                elif e.response.status_code in [400, 401, 403, 404, 422]:
                    # Client errors - don't retry
                    logger.error(f"❌ Client error ({e.response.status_code}): {e.response.text}")
                    raise

                else:
                    # Unknown error - retry
                    if attempt < self.max_retries:
                        delay = self.calculate_delay(attempt)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise

            except httpx.RequestError as e:
                # Network errors - retry
                last_exception = e
                logger.warning(
                    f"⚠️ Network error: {str(e)}, attempt {attempt + 1}/{self.max_retries + 1}"
                )

                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.info(f"   Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    self.circuit_breaker._on_failure()
                    raise

            except Exception as e:
                # Unexpected errors
                last_exception = e
                logger.error(f"❌ Unexpected error: {str(e)}")
                self.circuit_breaker._on_failure()
                raise

        # All retries exhausted
        logger.error(f"❌ All {self.max_retries} retries exhausted")
        raise last_exception


def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for adding retry logic to async functions.

    Usage:
        @with_retry(max_retries=3, base_delay=1.0)
        async def create_order(...):
            ...

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            handler = RetryHandler(max_retries=max_retries, base_delay=base_delay)
            return await handler.retry_async(func, *args, **kwargs)

        return wrapper

    return decorator


# Rate limiter for Shiprocket API (100 requests/minute)
class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Shiprocket Rate Limit: 100 requests/minute
    """

    def __init__(self, max_tokens: int = 100, refill_rate: float = 100 / 60):
        """
        Initialize rate limiter.

        Args:
            max_tokens: Maximum number of tokens (requests)
            refill_rate: Tokens added per second (100/60 = 1.67/sec)
        """
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.refill_rate = refill_rate
        self.last_refill = time.time()

    async def acquire(self):
        """
        Acquire a token for making an API request.
        Waits if no tokens available.
        """
        while True:
            # Refill tokens
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            # Check if token available
            if self.tokens >= 1:
                self.tokens -= 1
                return

            # Wait for next token
            wait_time = (1 - self.tokens) / self.refill_rate
            logger.debug(f"Rate limit: waiting {wait_time:.2f}s for next token")
            await asyncio.sleep(wait_time)


# Global rate limiter instance
shiprocket_rate_limiter = RateLimiter(max_tokens=100, refill_rate=100 / 60)
