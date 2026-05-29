"""
Redis caching infrastructure for performance optimization.

This module provides a caching layer using Redis to reduce database queries
and improve API response times.
"""

import json
import logging
import pickle
from functools import wraps
from typing import Any, Callable, Optional

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis caching operations with fallback to no-cache on errors."""

    def __init__(self, redis_url: str):
        """
        Initialize cache manager with Redis connection.

        Args:
            redis_url: Redis connection URL (empty string to disable caching)
        """
        # Skip Redis initialization if URL is empty
        if not redis_url or redis_url.strip() == "":
            logger.info("ℹ️  Redis URL not configured. Caching disabled.")
            self.redis = None
            self._enabled = False
            return

        try:
            self.redis = Redis.from_url(
                redis_url,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            # Test connection
            self.redis.ping()
            self._enabled = True
            logger.info("✅ Redis cache initialized successfully")
        except (RedisError, ConnectionError) as e:
            logger.warning(f"⚠️  Redis connection failed: {e}. Caching disabled.")
            self.redis = None
            self._enabled = False

    @property
    def enabled(self) -> bool:
        """Check if caching is enabled and Redis is available."""
        return self._enabled and self.redis is not None

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or error
        """
        if not self.enabled:
            return None

        try:
            cached = self.redis.get(key)
            if cached:
                return pickle.loads(cached)
        except (RedisError, pickle.PickleError) as e:
            logger.warning(f"Cache get error for key {key}: {e}")
        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default: 5 minutes)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            serialized = pickle.dumps(value)
            self.redis.setex(key, ttl, serialized)
            return True
        except (RedisError, pickle.PickleError) as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            self.redis.delete(key)
            return True
        except RedisError as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., "event:*")

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            keys = list(self.redis.scan_iter(match=pattern))
            if keys:
                return self.redis.delete(*keys)
            return 0
        except RedisError as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    def clear_all(self) -> bool:
        """
        Clear all cache entries (use with caution!).

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            self.redis.flushdb()
            logger.info("🗑️  Cache cleared successfully")
            return True
        except RedisError as e:
            logger.error(f"Cache clear error: {e}")
            return False

    def cache_result(
        self,
        key_prefix: str = "",
        ttl: int = 300,
        key_builder: Optional[Callable] = None,
    ):
        """
        Decorator to cache function results.

        Args:
            key_prefix: Prefix for cache key (default: function name)
            ttl: Time-to-live in seconds (default: 5 minutes)
            key_builder: Optional custom function to build cache key from args/kwargs

        Returns:
            Decorated function with caching

        Example:
            @cache.cache_result(key_prefix="user", ttl=900)
            def get_user(user_id: int):
                return db.query(User).get(user_id)
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # If caching is disabled, just call the function
                if not self.enabled:
                    return func(*args, **kwargs)

                # Build cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # Default key: prefix:func_name:args_hash
                    prefix = key_prefix or func.__name__
                    args_str = f"{args}:{kwargs}"
                    cache_key = f"{prefix}:{func.__name__}:{hash(args_str)}"

                # Try to get from cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached_result

                # Cache miss - call function
                logger.debug(f"Cache MISS: {cache_key}")
                result = func(*args, **kwargs)

                # Store in cache
                self.set(cache_key, result, ttl)
                return result

            return wrapper

        return decorator


# Global cache instance
# Initialize with settings, fallback to disabled if Redis not configured
_cache_manager: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """
    Get global cache manager instance (singleton pattern).

    Returns:
        CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        redis_url = getattr(settings, "REDIS_URL", "")
        _cache_manager = CacheManager(redis_url)
    return _cache_manager


# Convenience instance for direct import
cache = get_cache()


# Cache key builders for common patterns
def build_user_cache_key(user_id: int) -> str:
    """Build cache key for user data."""
    return f"user:{user_id}"


def build_event_cache_key(event_id: int) -> str:
    """Build cache key for event data."""
    return f"event:detail:{event_id}"


def build_event_list_cache_key(
    skip: int = 0, limit: int = 100, is_featured: Optional[bool] = None
) -> str:
    """Build cache key for event list."""
    featured_str = f"featured:{is_featured}" if is_featured is not None else "all"
    return f"event:list:{featured_str}:{skip}:{limit}"


def invalidate_event_caches(event_id: Optional[int] = None) -> None:
    """
    Invalidate event-related caches.

    Args:
        event_id: Optional specific event ID to invalidate, or None for all events
    """
    if event_id:
        cache.delete(build_event_cache_key(event_id))
    # Always invalidate list caches when any event changes
    cache.delete_pattern("event:list:*")
    logger.info(f"Invalidated event caches (event_id: {event_id})")


def invalidate_user_cache(user_id: int) -> None:
    """
    Invalidate user-related caches.

    Args:
        user_id: User ID
    """
    cache.delete(build_user_cache_key(user_id))
    logger.info(f"Invalidated user cache (user_id: {user_id})")
