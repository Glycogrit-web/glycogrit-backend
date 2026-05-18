"""
Reusable Decorators for Reducing Boilerplate Code
Includes: Authorization, Transactions, Retry Logic, Logging, Caching, Validation
"""

import functools
import logging
import time
from typing import Callable, Any, Optional, List
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError

from app.core.exceptions import PermissionDeniedException, DatabaseException
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
            db: Optional[Session] = kwargs.get('db')
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


def cache_result(ttl_seconds: Optional[int] = 300, key_func: Optional[Callable] = None):
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


# ==================== Combined Decorator ====================

def api_endpoint(
    require_roles: Optional[List[str]] = None,
    log_execution_enabled: bool = True,
    cache_ttl: Optional[int] = None
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
