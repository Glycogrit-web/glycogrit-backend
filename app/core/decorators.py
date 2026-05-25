"""
Reusable Decorators for Reducing Boilerplate Code
Includes: Authorization, Transactions, Retry Logic, Logging, Caching, Validation
"""

import functools
import logging
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLTimeoutError
from sqlalchemy.orm import Session
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.exceptions import DatabaseException, PermissionDeniedException
from app.core.permissions import PermissionChecker
from app.models.user import User

logger = logging.getLogger(__name__)


# ==================== Authorization Decorators ====================

def require_role(*allowed_roles: str):
    """
    Decorator to require specific user roles

    Usage:
        @require_role("admin", "super_admin")
        async def delete_user(user_id: int, current_user: User = Depends(get_current_user)):
            # Only admins and super_admins can access
            pass

    Args:
        *allowed_roles: Roles that are allowed to access the function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Find current_user in kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                # Try to find it in args (positional)
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            if current_user.role not in allowed_roles:
                raise PermissionDeniedException(
                    f"Access denied. Required roles: {', '.join(allowed_roles)}"
                )

            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Find current_user in kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                # Try to find it in args (positional)
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            if current_user.role not in allowed_roles:
                raise PermissionDeniedException(
                    f"Access denied. Required roles: {', '.join(allowed_roles)}"
                )

            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require admin role

    Usage:
        @require_admin
        async def admin_only_endpoint(current_user: User = Depends(get_current_user)):
            pass
    """
    return require_role("admin", "super_admin")(func)


def require_ownership(resource_param: str = "resource", user_id_attr: str = "user_id"):
    """
    Decorator to require resource ownership

    Usage:
        @require_ownership(resource_param="event", user_id_attr="organizer_id")
        async def update_event(event_id: int, event: Event, current_user: User):
            # Checks that event.organizer_id == current_user.id
            pass

    Args:
        resource_param: Name of the parameter containing the resource
        user_id_attr: Attribute name on the resource containing the user ID
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            resource = kwargs.get(resource_param)

            if not current_user or not resource:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required parameters for ownership check"
                )

            resource_user_id = getattr(resource, user_id_attr, None)
            if resource_user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Resource does not have attribute '{user_id_attr}'"
                )

            if resource_user_id != current_user.id:
                raise PermissionDeniedException(
                    f"You can only modify your own {resource_param}"
                )

            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            resource = kwargs.get(resource_param)

            if not current_user or not resource:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required parameters for ownership check"
                )

            resource_user_id = getattr(resource, user_id_attr, None)
            if resource_user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Resource does not have attribute '{user_id_attr}'"
                )

            if resource_user_id != current_user.id:
                raise PermissionDeniedException(
                    f"You can only modify your own {resource_param}"
                )

            return func(*args, **kwargs)

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def require_admin_or_owner(resource_param: str = "resource", user_id_attr: str = "user_id"):
    """
    Decorator to require admin role OR resource ownership

    Usage:
        @require_admin_or_owner(resource_param="registration", user_id_attr="user_id")
        async def cancel_registration(registration: Registration, current_user: User):
            # Admins can cancel any registration, users can cancel their own
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            resource = kwargs.get(resource_param)

            if not current_user or not resource:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required parameters"
                )

            # Allow if admin
            if PermissionChecker.is_admin(current_user):
                return await func(*args, **kwargs)

            # Check ownership
            resource_user_id = getattr(resource, user_id_attr, None)
            if resource_user_id == current_user.id:
                return await func(*args, **kwargs)

            raise PermissionDeniedException(
                "Admin access or ownership required"
            )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            resource = kwargs.get(resource_param)

            if not current_user or not resource:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required parameters"
                )

            # Allow if admin
            if PermissionChecker.is_admin(current_user):
                return func(*args, **kwargs)

            # Check ownership
            resource_user_id = getattr(resource, user_id_attr, None)
            if resource_user_id == current_user.id:
                return func(*args, **kwargs)

            raise PermissionDeniedException(
                "Admin access or ownership required"
            )

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ==================== Transaction Decorators ====================

def transactional(auto_commit: bool = True):
    """
    Decorator to handle database transactions automatically

    Usage:
        @transactional()
        def create_user(db: Session, user_data: dict):
            user = User(**user_data)
            db.add(user)
            # Auto-commit on success, auto-rollback on exception

    Args:
        auto_commit: Whether to auto-commit on success (default: True)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Find db Session in kwargs or args
            db: Session | None = kwargs.get('db')
            if not db:
                for arg in args:
                    if isinstance(arg, Session):
                        db = arg
                        break

            if not db:
                # No database session found, just execute function
                return func(*args, **kwargs)

            try:
                result = func(*args, **kwargs)
                if auto_commit:
                    db.commit()
                    logger.debug(f"Transaction committed for {func.__name__}")
                return result
            except Exception as e:
                db.rollback()
                logger.error(f"Transaction rolled back for {func.__name__}: {str(e)}")
                raise DatabaseException(f"Database operation failed: {str(e)}")

        return wrapper

    return decorator


# ==================== Retry Decorators ====================

def retry_on_db_error(max_attempts: int = 3, wait_multiplier: int = 1):
    """
    Decorator to retry database operations on transient failures

    Usage:
        @retry_on_db_error(max_attempts=3)
        def fetch_user(db: Session, user_id: int):
            return db.query(User).filter(User.id == user_id).first()

    Args:
        max_attempts: Maximum number of retry attempts
        wait_multiplier: Multiplier for exponential backoff (seconds)
    """
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=wait_multiplier, min=1, max=10),
            retry=retry_if_exception_type((OperationalError, SQLTimeoutError)),
            reraise=True
        )
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


# ==================== Logging Decorators ====================

def log_execution(level: int = logging.INFO, include_args: bool = False):
    """
    Decorator to log function execution with timing

    Usage:
        @log_execution(level=logging.INFO, include_args=True)
        async def process_payment(payment_id: int):
            # Logs: "Executing process_payment with args: payment_id=123"
            # Logs: "Completed process_payment in 1.23s"
            pass

    Args:
        level: Logging level (default: INFO)
        include_args: Whether to include function arguments in log
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__

            # Log start
            if include_args:
                args_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
                logger.log(level, f"Executing {func_name} with args: {args_str}")
            else:
                logger.log(level, f"Executing {func_name}")

            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.log(level, f"Completed {func_name} in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"Failed {func_name} after {elapsed:.2f}s: {str(e)}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__name__

            # Log start
            if include_args:
                args_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
                logger.log(level, f"Executing {func_name} with args: {args_str}")
            else:
                logger.log(level, f"Executing {func_name}")

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.log(level, f"Completed {func_name} in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"Failed {func_name} after {elapsed:.2f}s: {str(e)}")
                raise

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ==================== Validation Decorators ====================

def validate_not_none(*param_names: str):
    """
    Decorator to validate that specified parameters are not None

    Usage:
        @validate_not_none("user_id", "event_id")
        def register_user(user_id: int, event_id: int):
            # Raises ValueError if user_id or event_id is None
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for param_name in param_names:
                if param_name in kwargs and kwargs[param_name] is None:
                    raise ValueError(f"Parameter '{param_name}' cannot be None")

            return func(*args, **kwargs)

        return wrapper

    return decorator


# ==================== Caching Decorator ====================

_cache = {}


def cache_result(ttl_seconds: int | None = 300, key_func: Callable | None = None):
    """
    Decorator to cache function results

    Usage:
        @cache_result(ttl_seconds=60)
        def get_event_statistics(event_id: int):
            # Result cached for 60 seconds
            return expensive_calculation()

    Args:
        ttl_seconds: Time to live for cache entry (None = no expiration)
        key_func: Custom function to generate cache key from args/kwargs
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

            # Check cache
            if cache_key in _cache:
                cached_value, cached_time = _cache[cache_key]
                if ttl_seconds is None or (time.time() - cached_time) < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            _cache[cache_key] = (result, time.time())
            logger.debug(f"Cached result for {func.__name__}")

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

            # Check cache
            if cache_key in _cache:
                cached_value, cached_time = _cache[cache_key]
                if ttl_seconds is None or (time.time() - cached_time) < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            _cache[cache_key] = (result, time.time())
            logger.debug(f"Cached result for {func.__name__}")

            return result

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def clear_cache():
    """Clear all cached results"""
    _cache.clear()
    logger.info("Cache cleared")


# ==================== Advanced Decorators ====================

_metrics = {}


def track_metrics(metric_name: str | None = None):
    """
    Decorator to track function execution metrics

    Usage:
        @track_metrics("user_creation")
        def create_user(db: Session, user_data: dict):
            pass

    Access metrics with: get_metrics()
    """
    def decorator(func: Callable) -> Callable:
        name = metric_name or func.__name__

        if name not in _metrics:
            _metrics[name] = {
                "count": 0,
                "total_time": 0.0,
                "errors": 0,
                "last_called": None
            }

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            _metrics[name]["count"] += 1
            _metrics[name]["last_called"] = datetime.now().isoformat()

            try:
                result = await func(*args, **kwargs)
                _metrics[name]["total_time"] += time.time() - start_time
                return result
            except Exception:
                _metrics[name]["errors"] += 1
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            _metrics[name]["count"] += 1
            _metrics[name]["last_called"] = datetime.now().isoformat()

            try:
                result = func(*args, **kwargs)
                _metrics[name]["total_time"] += time.time() - start_time
                return result
            except Exception:
                _metrics[name]["errors"] += 1
                raise

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def get_metrics(metric_name: str | None = None) -> dict[str, Any]:
    """Get tracked metrics"""
    if metric_name:
        metric = _metrics.get(metric_name, {})
        if metric.get("count", 0) > 0:
            metric["avg_time"] = metric["total_time"] / metric["count"]
        return metric

    # Return all metrics with averages
    result = {}
    for name, metric in _metrics.items():
        result[name] = metric.copy()
        if metric["count"] > 0:
            result[name]["avg_time"] = metric["total_time"] / metric["count"]

    return result


def clear_metrics():
    """Clear all metrics"""
    _metrics.clear()


def async_background_task(func: Callable) -> Callable:
    """
    Decorator to run function as background task

    Usage:
        @async_background_task
        async def send_email(to: str, subject: str):
            # This will run in background
            pass

        # Call normally
        await send_email("user@example.com", "Welcome")
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        import asyncio

        # Create background task
        task = asyncio.create_task(func(*args, **kwargs))

        # Log task creation
        logger.debug(f"Created background task for {func.__name__}")

        return task

    return wrapper


def deprecate(message: str, version: str | None = None):
    """
    Decorator to mark functions as deprecated

    Usage:
        @deprecate("Use new_function() instead", version="2.0")
        def old_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warning_msg = f"{func.__name__} is deprecated."
            if version:
                warning_msg += f" (Will be removed in version {version})"
            if message:
                warning_msg += f" {message}"

            import warnings
            warnings.warn(warning_msg, DeprecationWarning, stacklevel=2)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def memoize_method(max_cache_size: int = 128):
    """
    Decorator to memoize class methods

    Usage:
        class UserService:
            @memoize_method(max_cache_size=100)
            def get_user_permissions(self, user_id: int):
                # Expensive operation
                return permissions
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_keys = []

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Create cache key from arguments
            key = (args, tuple(sorted(kwargs.items())))

            if key in cache:
                logger.debug(f"Cache hit for {func.__name__}")
                return cache[key]

            # Call function
            result = func(self, *args, **kwargs)

            # Store in cache
            cache[key] = result
            cache_keys.append(key)

            # Limit cache size
            if len(cache_keys) > max_cache_size:
                oldest_key = cache_keys.pop(0)
                del cache[oldest_key]

            return result

        return wrapper

    return decorator


def rate_limit_decorator(max_calls: int = 10, period_seconds: int = 60):
    """
    Decorator to rate limit function calls

    Usage:
        @rate_limit_decorator(max_calls=5, period_seconds=60)
        async def send_sms(phone: str, message: str):
            # Limited to 5 calls per minute
            pass
    """
    call_times = []

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_time = time.time()

            # Remove old calls outside the window
            nonlocal call_times
            call_times = [t for t in call_times if current_time - t < period_seconds]

            # Check if rate limit exceeded
            if len(call_times) >= max_calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {max_calls} calls per {period_seconds} seconds"
                )

            # Add current call
            call_times.append(current_time)

            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_time = time.time()

            # Remove old calls outside the window
            nonlocal call_times
            call_times = [t for t in call_times if current_time - t < period_seconds]

            # Check if rate limit exceeded
            if len(call_times) >= max_calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {max_calls} calls per {period_seconds} seconds"
                )

            # Add current call
            call_times.append(current_time)

            return func(*args, **kwargs)

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
):
    """
    Circuit breaker pattern decorator

    Prevents calling a function if it has failed too many times

    Usage:
        @circuit_breaker(failure_threshold=3, recovery_timeout=30)
        async def call_external_api():
            # Will stop calling if fails 3 times
            # Waits 30 seconds before trying again
            pass
    """
    def decorator(func: Callable) -> Callable:
        func._circuit_breaker_failures = 0
        func._circuit_breaker_last_failure_time = None
        func._circuit_breaker_state = "closed"  # closed, open, half_open

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Check circuit state
            if func._circuit_breaker_state == "open":
                # Check if recovery timeout has passed
                if time.time() - func._circuit_breaker_last_failure_time > recovery_timeout:
                    func._circuit_breaker_state = "half_open"
                    logger.info(f"Circuit breaker half-open for {func.__name__}")
                else:
                    raise Exception(f"Circuit breaker open for {func.__name__}")

            try:
                result = await func(*args, **kwargs)

                # Reset on success
                if func._circuit_breaker_state == "half_open":
                    func._circuit_breaker_state = "closed"
                    func._circuit_breaker_failures = 0
                    logger.info(f"Circuit breaker closed for {func.__name__}")

                return result

            except expected_exception:
                func._circuit_breaker_failures += 1
                func._circuit_breaker_last_failure_time = time.time()

                if func._circuit_breaker_failures >= failure_threshold:
                    func._circuit_breaker_state = "open"
                    logger.error(f"Circuit breaker opened for {func.__name__}")

                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Check circuit state
            if func._circuit_breaker_state == "open":
                # Check if recovery timeout has passed
                if time.time() - func._circuit_breaker_last_failure_time > recovery_timeout:
                    func._circuit_breaker_state = "half_open"
                    logger.info(f"Circuit breaker half-open for {func.__name__}")
                else:
                    raise Exception(f"Circuit breaker open for {func.__name__}")

            try:
                result = func(*args, **kwargs)

                # Reset on success
                if func._circuit_breaker_state == "half_open":
                    func._circuit_breaker_state = "closed"
                    func._circuit_breaker_failures = 0
                    logger.info(f"Circuit breaker closed for {func.__name__}")

                return result

            except expected_exception:
                func._circuit_breaker_failures += 1
                func._circuit_breaker_last_failure_time = time.time()

                if func._circuit_breaker_failures >= failure_threshold:
                    func._circuit_breaker_state = "open"
                    logger.error(f"Circuit breaker opened for {func.__name__}")

                raise

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ==================== Combined Decorator ====================

def api_endpoint(
    require_roles: list[str] | None = None,
    log_execution_enabled: bool = True,
    cache_ttl: int | None = None
):
    """
    Combined decorator for common API endpoint patterns

    Usage:
        @api_endpoint(require_roles=["admin"], log_execution_enabled=True)
        async def admin_endpoint(current_user: User = Depends(get_current_user)):
            pass

    Args:
        require_roles: List of allowed roles (None = no role check)
        log_execution_enabled: Whether to log execution
        cache_ttl: Cache TTL in seconds (None = no caching)
    """
    def decorator(func: Callable) -> Callable:
        # Apply decorators in reverse order (bottom-up)
        decorated_func = func

        if cache_ttl is not None:
            decorated_func = cache_result(ttl_seconds=cache_ttl)(decorated_func)

        if log_execution_enabled:
            decorated_func = log_execution()(decorated_func)

        if require_roles:
            decorated_func = require_role(*require_roles)(decorated_func)

        return decorated_func

    return decorator
