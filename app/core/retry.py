"""
Retry Mechanism for External API Calls

This module provides reusable retry decorators and utilities for handling
transient failures in external API calls (payment gateways, shipping providers, etc.).

Uses the tenacity library for robust retry logic with exponential backoff,
jitter, and customizable retry strategies.

Installation:
    pip install tenacity

Usage:
    from app.core.retry import with_retry, with_payment_gateway_retry

    @with_retry(max_attempts=3)
    def call_external_api():
        # Your API call here
        pass

    @with_payment_gateway_retry
    def create_razorpay_order():
        # Razorpay API call with retry
        pass
"""
import functools
import logging
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

# Import standard library and third-party exceptions
from requests.exceptions import ConnectionError, HTTPError, RequestException, Timeout
from sqlalchemy.exc import DBAPIError, OperationalError
from tenacity import (
    RetryError,
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Import application exceptions
from app.core.exceptions import (
    ExternalServiceException,
    PaymentGatewayException,
    ShippingServiceException,
)

logger = logging.getLogger(__name__)


# ========================================
# Retry Condition Functions
# ========================================

def is_transient_http_error(exception: Exception) -> bool:
    """
    Check if exception is a transient HTTP error that should be retried.

    Retryable errors:
    - Network timeouts
    - Connection errors
    - 429 Too Many Requests (rate limiting)
    - 500 Internal Server Error
    - 502 Bad Gateway
    - 503 Service Unavailable
    - 504 Gateway Timeout

    Non-retryable errors:
    - 400 Bad Request (client error)
    - 401 Unauthorized (auth issue)
    - 403 Forbidden (auth issue)
    - 404 Not Found (resource doesn't exist)
    - 409 Conflict (business logic issue)
    """
    # Network-level errors (always retry)
    if isinstance(exception, (Timeout, ConnectionError)):
        return True

    # HTTP errors (check status code)
    if isinstance(exception, HTTPError):
        response = getattr(exception, 'response', None)
        if response is not None:
            status_code = response.status_code
            # Retry on rate limiting and server errors
            retryable_codes = {429, 500, 502, 503, 504}
            return status_code in retryable_codes

    return False


def is_transient_database_error(exception: Exception) -> bool:
    """
    Check if exception is a transient database error that should be retried.

    Retryable errors:
    - Connection timeouts
    - Connection pool exhausted
    - Server gone away
    - Deadlock detected (database will retry)

    Non-retryable errors:
    - Constraint violations
    - Syntax errors
    - Permission errors
    """
    if isinstance(exception, (OperationalError, DBAPIError)):
        error_msg = str(exception).lower()

        # Retryable patterns
        retryable_patterns = [
            'connection',
            'timeout',
            'gone away',
            'deadlock',
            'lock wait timeout',
            'too many connections'
        ]

        return any(pattern in error_msg for pattern in retryable_patterns)

    return False


def is_transient_payment_error(exception: Exception) -> bool:
    """
    Check if exception is a transient payment gateway error that should be retried.

    Retryable payment errors:
    - Gateway timeout
    - Gateway unavailable
    - Network issues

    Non-retryable payment errors:
    - Invalid credentials
    - Invalid payment details
    - Payment already captured
    - Business logic errors
    """
    if isinstance(exception, PaymentGatewayException):
        error_msg = str(exception).lower()

        # Retryable patterns
        retryable_patterns = [
            'timeout',
            'unavailable',
            'connection',
            'network',
            'gateway error',
            'server error'
        ]

        # Non-retryable patterns (explicit checks)
        non_retryable_patterns = [
            'invalid',
            'already captured',
            'unauthorized',
            'authentication',
            'bad request'
        ]

        # If explicitly non-retryable, don't retry
        if any(pattern in error_msg for pattern in non_retryable_patterns):
            return False

        # Check if retryable
        return any(pattern in error_msg for pattern in retryable_patterns)

    # Also retry on base network errors
    return isinstance(exception, (Timeout, ConnectionError))


def is_transient_shipping_error(exception: Exception) -> bool:
    """
    Check if exception is a transient shipping service error that should be retried.

    Similar logic to payment errors.
    """
    if isinstance(exception, ShippingServiceException):
        error_msg = str(exception).lower()

        retryable_patterns = [
            'timeout',
            'unavailable',
            'connection',
            'network',
            'server error'
        ]

        non_retryable_patterns = [
            'invalid',
            'not found',
            'unauthorized'
        ]

        if any(pattern in error_msg for pattern in non_retryable_patterns):
            return False

        return any(pattern in error_msg for pattern in retryable_patterns)

    return isinstance(exception, (Timeout, ConnectionError))


# ========================================
# Retry Decorators
# ========================================

def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exception_types: tuple[type[Exception], ...] | None = None,
    retry_condition: Callable[[Exception], bool] | None = None
):
    """
    Generic retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        min_wait: Minimum wait time between retries in seconds (default: 1.0)
        max_wait: Maximum wait time between retries in seconds (default: 10.0)
        exception_types: Tuple of exception types to retry (default: all)
        retry_condition: Custom function to determine if exception should be retried

    Example:
        @with_retry(max_attempts=5, min_wait=2.0)
        def fetch_data_from_api():
            response = requests.get("https://api.example.com/data")
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        # Determine retry condition
        if retry_condition is not None:
            retry_predicate = retry_if_exception(retry_condition)
        elif exception_types is not None:
            retry_predicate = retry_if_exception_type(exception_types)
        else:
            # Default: retry on any RequestException or ExternalServiceException
            retry_predicate = retry_if_exception_type((RequestException, ExternalServiceException))

        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_predicate,
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.DEBUG)
        )
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except RetryError as e:
                # Max retries exceeded, log and re-raise original exception
                logger.error(
                    f"Max retries ({max_attempts}) exceeded for {func.__name__}: "
                    f"{e.last_attempt.exception()}"
                )
                raise e.last_attempt.exception()

        return wrapper

    return decorator


def with_payment_gateway_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 8.0
):
    """
    Retry decorator specifically for payment gateway API calls.

    Uses exponential backoff with jitter to avoid thundering herd.
    Only retries transient errors (network, timeout, server errors).

    Args:
        max_attempts: Maximum retry attempts (default: 3)
        min_wait: Minimum wait time in seconds (default: 1.0)
        max_wait: Maximum wait time in seconds (default: 8.0)

    Example:
        @with_payment_gateway_retry
        def create_razorpay_order(amount):
            return razorpay_client.order.create({"amount": amount})
    """
    return with_retry(
        max_attempts=max_attempts,
        min_wait=min_wait,
        max_wait=max_wait,
        retry_condition=is_transient_payment_error
    )


def with_shipping_service_retry(
    max_attempts: int = 3,
    min_wait: float = 2.0,
    max_wait: float = 10.0
):
    """
    Retry decorator specifically for shipping service API calls.

    Uses exponential backoff with slightly longer waits than payment gateways
    (shipping APIs tend to be slower).

    Args:
        max_attempts: Maximum retry attempts (default: 3)
        min_wait: Minimum wait time in seconds (default: 2.0)
        max_wait: Maximum wait time in seconds (default: 10.0)

    Example:
        @with_shipping_service_retry
        def create_shiprocket_order(order_data):
            return shiprocket_client.create_order(order_data)
    """
    return with_retry(
        max_attempts=max_attempts,
        min_wait=min_wait,
        max_wait=max_wait,
        retry_condition=is_transient_shipping_error
    )


def with_database_retry(
    max_attempts: int = 3,
    min_wait: float = 0.5,
    max_wait: float = 5.0
):
    """
    Retry decorator for database operations (deadlocks, connection issues).

    Uses shorter wait times since database issues typically resolve quickly.

    Args:
        max_attempts: Maximum retry attempts (default: 3)
        min_wait: Minimum wait time in seconds (default: 0.5)
        max_wait: Maximum wait time in seconds (default: 5.0)

    Example:
        @with_database_retry
        def execute_query():
            return db.execute(complex_query)
    """
    return with_retry(
        max_attempts=max_attempts,
        min_wait=min_wait,
        max_wait=max_wait,
        retry_condition=is_transient_database_error
    )


# ========================================
# Context Managers
# ========================================

@contextmanager
def retry_context(
    operation_name: str,
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_condition: Callable[[Exception], bool] | None = None
):
    """
    Context manager for retry logic without decorator.

    Useful when you can't use decorators or need retry for a code block.

    Args:
        operation_name: Name of operation for logging
        max_attempts: Maximum retry attempts
        min_wait: Minimum wait time between retries
        max_wait: Maximum wait time between retries
        retry_condition: Custom retry condition function

    Example:
        with retry_context("fetch_payment_details", max_attempts=3):
            payment = razorpay_client.payment.fetch(payment_id)
    """
    from tenacity import Retrying

    retry_predicate = (
        retry_if_exception(retry_condition) if retry_condition
        else retry_if_exception_type((RequestException, ExternalServiceException))
    )

    retrying = Retrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_predicate,
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.DEBUG)
    )

    try:
        with retrying:
            yield
    except RetryError as e:
        logger.error(
            f"Max retries ({max_attempts}) exceeded for {operation_name}: "
            f"{e.last_attempt.exception()}"
        )
        raise e.last_attempt.exception()


# ========================================
# Async Retry Support
# ========================================

def with_async_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exception_types: tuple[type[Exception], ...] | None = None,
    retry_condition: Callable[[Exception], bool] | None = None
):
    """
    Async retry decorator for async functions.

    Same as with_retry but for async/await functions.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries in seconds
        max_wait: Maximum wait time between retries in seconds
        exception_types: Tuple of exception types to retry
        retry_condition: Custom function to determine if exception should be retried

    Example:
        @with_async_retry(max_attempts=3)
        async def fetch_data():
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.example.com") as resp:
                    return await resp.json()
    """
    def decorator(func: Callable) -> Callable:
        # Determine retry condition
        if retry_condition is not None:
            retry_predicate = retry_if_exception(retry_condition)
        elif exception_types is not None:
            retry_predicate = retry_if_exception_type(exception_types)
        else:
            retry_predicate = retry_if_exception_type((RequestException, ExternalServiceException))

        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_predicate,
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.DEBUG)
        )
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except RetryError as e:
                logger.error(
                    f"Max retries ({max_attempts}) exceeded for {func.__name__}: "
                    f"{e.last_attempt.exception()}"
                )
                raise e.last_attempt.exception()

        return wrapper

    return decorator


# ========================================
# Utility Functions
# ========================================

def should_retry_http_status(status_code: int) -> bool:
    """
    Determine if an HTTP status code should trigger a retry.

    Args:
        status_code: HTTP status code

    Returns:
        bool: True if should retry, False otherwise
    """
    # Retry on:
    # - 429 Too Many Requests (rate limiting)
    # - 500 Internal Server Error
    # - 502 Bad Gateway
    # - 503 Service Unavailable
    # - 504 Gateway Timeout
    retryable_codes = {429, 500, 502, 503, 504}
    return status_code in retryable_codes


def get_retry_after_seconds(response: Any, default: float = 5.0) -> float:
    """
    Extract Retry-After header value from HTTP response.

    Args:
        response: HTTP response object (requests.Response or similar)
        default: Default wait time if header not present

    Returns:
        float: Seconds to wait before retry
    """
    try:
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            # Retry-After can be in seconds (integer) or HTTP-date
            try:
                return float(retry_after)
            except ValueError:
                # HTTP-date format - return default
                return default
    except (AttributeError, KeyError):
        pass

    return default


# ========================================
# Metrics and Monitoring
# ========================================

class RetryMetrics:
    """
    Track retry metrics for monitoring and alerting.

    Usage:
        metrics = RetryMetrics()

        @metrics.track("payment_gateway")
        @with_payment_gateway_retry
        def create_order():
            ...

        print(metrics.get_stats("payment_gateway"))
    """

    def __init__(self):
        self._stats = {}

    def track(self, operation: str):
        """Decorator to track retry metrics for an operation"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if operation not in self._stats:
                    self._stats[operation] = {
                        'total_calls': 0,
                        'successful': 0,
                        'failed': 0,
                        'retries': 0
                    }

                self._stats[operation]['total_calls'] += 1

                try:
                    result = func(*args, **kwargs)
                    self._stats[operation]['successful'] += 1
                    return result
                except RetryError:
                    self._stats[operation]['failed'] += 1
                    self._stats[operation]['retries'] += 1
                    raise
                except Exception:
                    self._stats[operation]['failed'] += 1
                    raise

            return wrapper
        return decorator

    def get_stats(self, operation: str) -> dict:
        """Get retry statistics for an operation"""
        return self._stats.get(operation, {})

    def reset_stats(self, operation: str | None = None):
        """Reset statistics for one or all operations"""
        if operation:
            self._stats.pop(operation, None)
        else:
            self._stats.clear()


# Global metrics instance (optional)
retry_metrics = RetryMetrics()
