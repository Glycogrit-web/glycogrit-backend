# Redis Caching Strategy for GlycoGrit

## Overview
Redis will be used as a high-performance caching layer and for real-time data operations in the GlycoGrit platform.

## Installation

### Add Redis to requirements.txt:
```
redis==5.0.1
hiredis==2.3.2  # C parser for better performance
```

### Railway Setup:
1. Add Redis plugin in Railway dashboard
2. Railway automatically provides `REDIS_URL` environment variable

### Local Development:
```bash
# macOS
brew install redis
brew services start redis

# Linux (Ubuntu/Debian)
sudo apt-get install redis-server
sudo systemctl start redis
```

---

## Redis Configuration

### Connection Setup:
```python
# app/core/redis_client.py
import redis
from redis.connection import ConnectionPool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            cls._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                decode_responses=True,
                socket_keepalive=True,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
        return cls._instance

    def get_client(self):
        """Get Redis client from pool"""
        return redis.Redis(connection_pool=self._pool)

    def health_check(self):
        """Check Redis connection"""
        try:
            client = self.get_client()
            return client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

# Initialize singleton
redis_client = RedisClient()

def get_redis():
    """Dependency injection for FastAPI"""
    return redis_client.get_client()
```

### Update config.py:
```python
# app/core/config.py
class Settings(BaseSettings):
    # ... existing settings ...

    # Redis Configuration
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )
```

---

## Caching Strategies

### 1. Event Listings Cache

**Use Case:** Frequently accessed event lists
**TTL:** 5 minutes (300 seconds)
**Invalidation:** On event creation/update/deletion

```python
# app/services/event_cache.py
import json
from typing import List, Optional
from app.core.redis_client import get_redis

class EventCache:
    CACHE_PREFIX = "events"
    DEFAULT_TTL = 300  # 5 minutes

    @staticmethod
    def get_featured_events() -> Optional[List]:
        """Get cached featured events"""
        redis = get_redis()
        key = f"{EventCache.CACHE_PREFIX}:featured"
        cached = redis.get(key)

        if cached:
            return json.loads(cached)
        return None

    @staticmethod
    def set_featured_events(events: List, ttl: int = DEFAULT_TTL):
        """Cache featured events"""
        redis = get_redis()
        key = f"{EventCache.CACHE_PREFIX}:featured"
        redis.setex(key, ttl, json.dumps(events))

    @staticmethod
    def get_events_by_city(city: str) -> Optional[List]:
        """Get cached events by city"""
        redis = get_redis()
        key = f"{EventCache.CACHE_PREFIX}:city:{city.lower()}"
        cached = redis.get(key)

        if cached:
            return json.loads(cached)
        return None

    @staticmethod
    def set_events_by_city(city: str, events: List, ttl: int = DEFAULT_TTL):
        """Cache events by city"""
        redis = get_redis()
        key = f"{EventCache.CACHE_PREFIX}:city:{city.lower()}"
        redis.setex(key, ttl, json.dumps(events))

    @staticmethod
    def invalidate_event_caches():
        """Clear all event caches when events are modified"""
        redis = get_redis()
        # Delete all keys matching pattern
        for key in redis.scan_iter(f"{EventCache.CACHE_PREFIX}:*"):
            redis.delete(key)
```

---

### 2. Leaderboard Real-Time Cache

**Use Case:** Live event leaderboards
**TTL:** 1 minute (60 seconds) for active events
**Data Structure:** Sorted Sets (ZSET)

```python
# app/services/leaderboard_cache.py
from typing import List, Dict
from app.core.redis_client import get_redis

class LeaderboardCache:
    CACHE_PREFIX = "leaderboard"
    LIVE_TTL = 60  # 1 minute for live events
    COMPLETED_TTL = 3600  # 1 hour for completed events

    @staticmethod
    def add_participant_time(event_id: int, registration_id: int, time_seconds: int):
        """Add participant time to leaderboard (lower is better)"""
        redis = get_redis()
        key = f"{LeaderboardCache.CACHE_PREFIX}:event:{event_id}:overall"
        redis.zadd(key, {f"reg_{registration_id}": time_seconds})
        redis.expire(key, LeaderboardCache.LIVE_TTL)

    @staticmethod
    def get_top_n(event_id: int, n: int = 10) -> List[Dict]:
        """Get top N participants"""
        redis = get_redis()
        key = f"{LeaderboardCache.CACHE_PREFIX}:event:{event_id}:overall"

        # Get top N with scores (ZRANGE returns in ascending order)
        results = redis.zrange(key, 0, n-1, withscores=True)

        leaderboard = []
        for rank, (member, score) in enumerate(results, start=1):
            registration_id = int(member.split('_')[1])
            leaderboard.append({
                'rank': rank,
                'registration_id': registration_id,
                'time_seconds': int(score)
            })

        return leaderboard

    @staticmethod
    def get_participant_rank(event_id: int, registration_id: int) -> Optional[int]:
        """Get participant's current rank"""
        redis = get_redis()
        key = f"{LeaderboardCache.CACHE_PREFIX}:event:{event_id}:overall"
        rank = redis.zrank(key, f"reg_{registration_id}")

        if rank is not None:
            return rank + 1  # Convert 0-based to 1-based rank
        return None

    @staticmethod
    def get_leaderboard_by_gender(event_id: int, gender: str, n: int = 10) -> List[Dict]:
        """Get gender-specific leaderboard"""
        redis = get_redis()
        key = f"{LeaderboardCache.CACHE_PREFIX}:event:{event_id}:gender:{gender.lower()}"

        results = redis.zrange(key, 0, n-1, withscores=True)

        leaderboard = []
        for rank, (member, score) in enumerate(results, start=1):
            registration_id = int(member.split('_')[1])
            leaderboard.append({
                'rank': rank,
                'registration_id': registration_id,
                'time_seconds': int(score),
                'gender': gender
            })

        return leaderboard

    @staticmethod
    def update_gender_leaderboard(event_id: int, registration_id: int, gender: str, time_seconds: int):
        """Update gender-specific leaderboard"""
        redis = get_redis()
        key = f"{LeaderboardCache.CACHE_PREFIX}:event:{event_id}:gender:{gender.lower()}"
        redis.zadd(key, {f"reg_{registration_id}": time_seconds})
        redis.expire(key, LeaderboardCache.LIVE_TTL)

    @staticmethod
    def get_total_participants(event_id: int) -> int:
        """Get total number of participants in leaderboard"""
        redis = get_redis()
        key = f"{LeaderboardCache.CACHE_PREFIX}:event:{event_id}:overall"
        return redis.zcard(key)

    @staticmethod
    def clear_event_leaderboard(event_id: int):
        """Clear all leaderboards for an event"""
        redis = get_redis()
        pattern = f"{LeaderboardCache.CACHE_PREFIX}:event:{event_id}:*"
        for key in redis.scan_iter(pattern):
            redis.delete(key)
```

---

### 3. Live Event Tracking

**Use Case:** Real-time participant location and status
**TTL:** 30 seconds
**Data Structure:** Hash

```python
# app/services/live_tracking_cache.py
from typing import Dict, Optional
from app.core.redis_client import get_redis
import json
from datetime import datetime

class LiveTrackingCache:
    CACHE_PREFIX = "tracking"
    TTL = 30  # 30 seconds

    @staticmethod
    def update_participant_location(
        event_id: int,
        registration_id: int,
        latitude: float,
        longitude: float,
        checkpoint_id: Optional[int] = None
    ):
        """Update participant's live location"""
        redis = get_redis()
        key = f"{LiveTrackingCache.CACHE_PREFIX}:event:{event_id}:participant:{registration_id}"

        data = {
            'latitude': latitude,
            'longitude': longitude,
            'checkpoint_id': checkpoint_id,
            'timestamp': datetime.utcnow().isoformat()
        }

        redis.setex(key, LiveTrackingCache.TTL, json.dumps(data))

    @staticmethod
    def get_participant_location(event_id: int, registration_id: int) -> Optional[Dict]:
        """Get participant's current location"""
        redis = get_redis()
        key = f"{LiveTrackingCache.CACHE_PREFIX}:event:{event_id}:participant:{registration_id}"
        data = redis.get(key)

        if data:
            return json.loads(data)
        return None

    @staticmethod
    def get_all_participants_location(event_id: int) -> Dict:
        """Get all participants' locations for an event"""
        redis = get_redis()
        pattern = f"{LiveTrackingCache.CACHE_PREFIX}:event:{event_id}:participant:*"

        locations = {}
        for key in redis.scan_iter(pattern):
            registration_id = int(key.split(':')[-1])
            data = redis.get(key)
            if data:
                locations[registration_id] = json.loads(data)

        return locations
```

---

### 4. Session Management

**Use Case:** User authentication sessions
**TTL:** 24 hours (86400 seconds)
**Data Structure:** String (JSON)

```python
# app/services/session_cache.py
from typing import Dict, Optional
from app.core.redis_client import get_redis
import json
import uuid

class SessionCache:
    CACHE_PREFIX = "session"
    TTL = 86400  # 24 hours

    @staticmethod
    def create_session(user_id: int, user_data: Dict) -> str:
        """Create a new session"""
        redis = get_redis()
        session_id = str(uuid.uuid4())
        key = f"{SessionCache.CACHE_PREFIX}:{session_id}"

        session_data = {
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            **user_data
        }

        redis.setex(key, SessionCache.TTL, json.dumps(session_data))
        return session_id

    @staticmethod
    def get_session(session_id: str) -> Optional[Dict]:
        """Get session data"""
        redis = get_redis()
        key = f"{SessionCache.CACHE_PREFIX}:{session_id}"
        data = redis.get(key)

        if data:
            return json.loads(data)
        return None

    @staticmethod
    def delete_session(session_id: str):
        """Delete session (logout)"""
        redis = get_redis()
        key = f"{SessionCache.CACHE_PREFIX}:{session_id}"
        redis.delete(key)

    @staticmethod
    def extend_session(session_id: str):
        """Extend session TTL"""
        redis = get_redis()
        key = f"{SessionCache.CACHE_PREFIX}:{session_id}"
        redis.expire(key, SessionCache.TTL)
```

---

### 5. Rate Limiting

**Use Case:** API rate limiting per user/IP
**TTL:** 60 seconds (sliding window)
**Data Structure:** Counter

```python
# app/services/rate_limiter.py
from app.core.redis_client import get_redis
from fastapi import HTTPException, status

class RateLimiter:
    CACHE_PREFIX = "rate_limit"
    DEFAULT_LIMIT = 100  # requests per minute
    WINDOW = 60  # seconds

    @staticmethod
    def check_rate_limit(
        identifier: str,
        endpoint: str,
        limit: int = DEFAULT_LIMIT
    ) -> bool:
        """Check if request is within rate limit"""
        redis = get_redis()
        key = f"{RateLimiter.CACHE_PREFIX}:{identifier}:{endpoint}"

        # Increment counter
        current = redis.incr(key)

        # Set expiry on first request
        if current == 1:
            redis.expire(key, RateLimiter.WINDOW)

        # Check limit
        if current > limit:
            return False

        return True

    @staticmethod
    def get_remaining_requests(identifier: str, endpoint: str, limit: int = DEFAULT_LIMIT) -> int:
        """Get remaining requests in current window"""
        redis = get_redis()
        key = f"{RateLimiter.CACHE_PREFIX}:{identifier}:{endpoint}"
        current = redis.get(key)

        if current:
            remaining = limit - int(current)
            return max(0, remaining)

        return limit

# Middleware for rate limiting
from fastapi import Request

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    identifier = request.client.host  # Use IP or user_id
    endpoint = request.url.path

    if not RateLimiter.check_rate_limit(identifier, endpoint):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )

    response = await call_next(request)
    return response
```

---

### 6. OTP Storage

**Use Case:** Phone/Email verification codes
**TTL:** 5 minutes (300 seconds)
**Data Structure:** String

```python
# app/services/otp_cache.py
from app.core.redis_client import get_redis
import random
from typing import Optional

class OTPCache:
    CACHE_PREFIX = "otp"
    TTL = 300  # 5 minutes

    @staticmethod
    def generate_otp(identifier: str) -> str:
        """Generate and store OTP"""
        redis = get_redis()
        otp = str(random.randint(100000, 999999))
        key = f"{OTPCache.CACHE_PREFIX}:{identifier}"

        redis.setex(key, OTPCache.TTL, otp)
        return otp

    @staticmethod
    def verify_otp(identifier: str, otp: str) -> bool:
        """Verify OTP"""
        redis = get_redis()
        key = f"{OTPCache.CACHE_PREFIX}:{identifier}"
        stored_otp = redis.get(key)

        if stored_otp and stored_otp == otp:
            redis.delete(key)  # Delete after successful verification
            return True

        return False

    @staticmethod
    def get_remaining_time(identifier: str) -> int:
        """Get OTP remaining TTL"""
        redis = get_redis()
        key = f"{OTPCache.CACHE_PREFIX}:{identifier}"
        return redis.ttl(key)
```

---

## Cache Invalidation Patterns

### Event-Based Invalidation:
```python
# app/services/cache_invalidation.py
from app.services.event_cache import EventCache
from app.services.leaderboard_cache import LeaderboardCache

def invalidate_event_caches(event_id: int):
    """Invalidate all caches related to an event"""
    EventCache.invalidate_event_caches()
    # Don't clear leaderboard for active events
    # Only clear on event cancellation

def on_event_created(event_id: int):
    """Called when new event is created"""
    EventCache.invalidate_event_caches()

def on_event_updated(event_id: int):
    """Called when event is updated"""
    EventCache.invalidate_event_caches()

def on_result_submitted(event_id: int, registration_id: int):
    """Called when participant submits result"""
    # Update leaderboard cache immediately
    pass  # Handled by LeaderboardCache directly
```

---

## Redis Key Naming Convention

```
{resource}:{identifier}:{sub-resource}:{sub-identifier}

Examples:
- events:featured
- events:city:mumbai
- leaderboard:event:123:overall
- leaderboard:event:123:gender:male
- tracking:event:123:participant:456
- session:abc-123-def-456
- rate_limit:user_123:/api/events
- otp:phone:+919876543210
```

---

## Monitoring Redis Performance

### Key Metrics:
```python
# app/services/redis_monitor.py
from app.core.redis_client import get_redis

def get_redis_stats():
    """Get Redis statistics"""
    redis = get_redis()
    info = redis.info()

    return {
        'used_memory_human': info.get('used_memory_human'),
        'connected_clients': info.get('connected_clients'),
        'total_commands_processed': info.get('total_commands_processed'),
        'keyspace_hits': info.get('keyspace_hits'),
        'keyspace_misses': info.get('keyspace_misses'),
        'hit_rate': calculate_hit_rate(
            info.get('keyspace_hits', 0),
            info.get('keyspace_misses', 0)
        )
    }

def calculate_hit_rate(hits: int, misses: int) -> float:
    """Calculate cache hit rate"""
    total = hits + misses
    if total == 0:
        return 0.0
    return (hits / total) * 100
```

---

## Best Practices

1. **Always set TTL**: Prevent memory leaks
2. **Use connection pooling**: Better performance
3. **Handle failures gracefully**: Redis should enhance, not break your app
4. **Monitor hit rates**: Optimize caching strategy
5. **Use appropriate data structures**:
   - Strings: Simple key-value
   - Hashes: Objects with multiple fields
   - Sets: Unique collections
   - Sorted Sets: Leaderboards, rankings
   - Lists: Queues, recent items

---

## Testing Redis Cache

```python
# tests/test_redis_cache.py
import pytest
from app.services.event_cache import EventCache
from app.services.leaderboard_cache import LeaderboardCache

def test_event_cache():
    """Test event caching"""
    events = [{"id": 1, "name": "Test Event"}]
    EventCache.set_featured_events(events)

    cached = EventCache.get_featured_events()
    assert cached == events

def test_leaderboard():
    """Test leaderboard caching"""
    event_id = 123
    LeaderboardCache.add_participant_time(event_id, 1, 3600)
    LeaderboardCache.add_participant_time(event_id, 2, 3500)

    top = LeaderboardCache.get_top_n(event_id, 10)
    assert top[0]['registration_id'] == 2  # Faster time
    assert top[0]['rank'] == 1
```

---

## Failover Strategy

```python
# app/core/redis_client.py (updated)
def safe_redis_operation(func):
    """Decorator for safe Redis operations with fallback"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            return None  # Fallback to database
        except Exception as e:
            logger.error(f"Redis operation error: {e}")
            return None
    return wrapper
```

---

## Environment Variables

```bash
# .env
REDIS_URL=redis://localhost:6379/0

# Railway (automatically provided)
REDIS_URL=redis://default:password@redis.railway.internal:6379
```
