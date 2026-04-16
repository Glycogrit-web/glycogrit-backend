# Database Patterns & Best Practices Skill

## Purpose
Reusable database patterns and best practices learned from NOVA API service for future implementation when needed.

## When to Use This Skill
- When scaling requires async operations
- When implementing caching layer
- When optimizing query performance
- When setting up monitoring
- When implementing advanced repository patterns

## Key Patterns

### 1. Async Database Operations (For Future Scaling)

```python
# AsyncIO with asyncpg for better concurrency
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

DATABASE_URL = f"postgresql+asyncpg://{USER}:{PASS}@{HOST}:{PORT}/{DB}"

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,          # Verify connections before use
    pool_size=10,                # Base pool size
    max_overflow=20,             # Additional connections
    pool_recycle=3600,           # Recycle after 1 hour
    pool_timeout=30,             # Wait 30s for connection
    connect_args={
        "timeout": 10,           # Connection timeout
        "command_timeout": 60    # Query timeout
    }
)

# Async session
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Async repository
class AsyncBaseRepository:
    async def create(self, **kwargs):
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
```

**Use When**:
- Handling 1000+ concurrent users
- Need non-blocking I/O operations
- High-traffic API endpoints

### 2. Redis Caching Layer (For Future Performance)

```python
# Redis patterns for leaderboards and caching
import redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Leaderboard (Sorted Set)
def update_leaderboard(event_id: int, user_id: int, time_seconds: int):
    key = f"leaderboard:event:{event_id}:overall"
    redis_client.zadd(key, {f"user:{user_id}": time_seconds})
    redis_client.expire(key, 3600)  # 1 hour TTL

# Get top 10
def get_top_10(event_id: int):
    key = f"leaderboard:event:{event_id}:overall"
    return redis_client.zrange(key, 0, 9, withscores=True)

# Cache event list
def cache_events(events: list):
    key = "events:featured"
    redis_client.setex(key, 300, json.dumps(events))  # 5 min TTL

# Rate limiting
def check_rate_limit(user_id: int, endpoint: str, max_requests: int = 100):
    key = f"rate_limit:{user_id}:{endpoint}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 60)  # 1 minute window
    return count <= max_requests
```

**Use When**:
- Leaderboards need real-time updates
- Frequently accessed data (event lists, user profiles)
- Need rate limiting
- Session management

### 3. Configuration Validation

```python
class DatabaseConfig:
    CONNECTION_POOL_SIZE: int = int(os.getenv('DB_POOL_SIZE', '10'))
    CONNECTION_POOL_MAX_OVERFLOW: int = int(os.getenv('DB_MAX_OVERFLOW', '20'))
    QUERY_TIMEOUT: int = int(os.getenv('DB_QUERY_TIMEOUT', '30'))

    @classmethod
    def validate_config(cls) -> None:
        """Validate configuration on startup"""
        errors = []

        if cls.CONNECTION_POOL_SIZE <= 0:
            errors.append(f"POOL_SIZE must be > 0, got {cls.CONNECTION_POOL_SIZE}")

        if cls.CONNECTION_POOL_MAX_OVERFLOW < 0:
            errors.append(f"MAX_OVERFLOW cannot be negative")

        if cls.QUERY_TIMEOUT <= 0:
            errors.append(f"QUERY_TIMEOUT must be > 0")

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors))

# Validate on import
DatabaseConfig.validate_config()
```

**Use When**: Setting up production configuration

### 4. Advanced Repository Pattern

```python
from typing import Generic, TypeVar, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar('ModelType')

class AsyncBaseRepository(Generic[ModelType]):
    """Async repository with session injection"""

    def __init__(self, session: AsyncSession, model_class: type[ModelType]):
        self.session = session  # Injected, not owned
        self.model_class = model_class
        self.logger = get_logger(self.__class__.__name__)

    async def create(self, **kwargs) -> ModelType:
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            await self.session.flush()  # Don't commit - let caller control
            await self.session.refresh(instance)
            self.logger.debug(f"Created {self.model_class.__name__}")
            return instance
        except IntegrityError as e:
            self.logger.error(f"IntegrityError: {e}")
            raise

    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == id)
        )
        return result.scalars().first()

    async def find_by(self, **filters) -> List[ModelType]:
        query = select(self.model_class)
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query = query.where(getattr(self.model_class, key) == value)
        result = await self.session.execute(query)
        return list(result.scalars().all())
```

**Use When**: Building complex data access layer

### 5. Query Optimization Patterns

```python
# Avoid N+1 queries with eager loading
from sqlalchemy.orm import joinedload, selectinload

# Bad: N+1 queries
events = db.query(Event).all()
for event in events:
    registrations = event.registrations  # Additional query!

# Good: Single query with join
events = db.query(Event).options(
    joinedload(Event.registrations)
).all()

# For large collections, use selectinload
events = db.query(Event).options(
    selectinload(Event.registrations)
).all()

# Pagination with counting
def get_paginated_events(page: int, per_page: int):
    total = db.query(Event).count()
    events = db.query(Event)\
        .offset((page - 1) * per_page)\
        .limit(per_page)\
        .all()
    return {
        'items': events,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }
```

**Use When**: Optimizing slow queries

### 6. Database Monitoring

```python
# Production monitoring endpoints
@app.get("/api/v1/health/database")
async def database_health():
    from app.core.database_monitor import DatabaseMonitor
    return DatabaseMonitor.get_full_health_report()

@app.get("/api/v1/metrics/slow-queries")
async def slow_queries():
    from app.core.database_monitor import DatabaseMonitor
    return DatabaseMonitor.get_slow_queries(limit=20)

@app.get("/api/v1/metrics/pool-stats")
async def pool_stats():
    from app.core.database_monitor import DatabaseMonitor
    return DatabaseMonitor.get_connection_pool_stats()
```

**Use When**: Setting up production monitoring

### 7. Transaction Management Patterns

```python
# Pattern 1: Service layer controls transactions
class EventService:
    def __init__(self, db: Session):
        self.db = db
        self.event_repo = EventRepository(db)
        self.registration_repo = RegistrationRepository(db)

    def register_for_event(self, user_id: int, event_id: int):
        try:
            # Multiple operations in one transaction
            event = self.event_repo.get(event_id)
            if event.current_participants >= event.max_participants:
                raise ValueError("Event full")

            registration = self.registration_repo.create(
                user_id=user_id,
                event_id=event_id
            )

            event.current_participants += 1
            self.event_repo.update(event_id, {
                'current_participants': event.current_participants
            })

            self.db.commit()  # Commit all or nothing
            return registration
        except Exception as e:
            self.db.rollback()
            raise

# Pattern 2: Context manager for transactions
from contextlib import contextmanager

@contextmanager
def transaction(db: Session):
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise

# Usage
with transaction(db):
    event_repo.create(...)
    registration_repo.create(...)
```

**Use When**: Managing complex multi-step operations

## Implementation Checklist

When implementing these patterns, follow this order:

1. **Start Simple** (Current)
   - [ ] SQL migrations working
   - [ ] Basic CRUD operations
   - [ ] Connection pooling configured
   - [ ] Health monitoring in place

2. **Add When Needed** (Scale Phase)
   - [ ] Async operations (1000+ users)
   - [ ] Redis caching (slow queries)
   - [ ] Advanced repositories (complex queries)
   - [ ] Query optimization (performance issues)

3. **Production Ready** (Launch Phase)
   - [ ] Monitoring dashboards
   - [ ] Alerting for slow queries
   - [ ] Connection pool tuning
   - [ ] Backup automation
   - [ ] Performance testing

## Connection Pool Settings by Scale

```python
# Development (Current)
pool_size=5
max_overflow=10

# Small Production (< 1000 users)
pool_size=10
max_overflow=20

# Medium Production (1000-10000 users)
pool_size=20
max_overflow=40

# Large Production (10000+ users)
pool_size=50
max_overflow=100
# Consider read replicas
```

## Security Checklist

- [ ] Environment variables for credentials
- [ ] Parameterized queries (SQLAlchemy ORM)
- [ ] Password hashing (bcrypt/argon2)
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention
- [ ] Rate limiting on sensitive endpoints
- [ ] Audit logging for critical operations

## Performance Optimization Checklist

- [ ] Index foreign keys
- [ ] Index WHERE clause columns
- [ ] Composite indexes for multi-column queries
- [ ] Monitor unused indexes
- [ ] Use EXPLAIN ANALYZE on slow queries
- [ ] Eager loading for relationships
- [ ] Pagination on large result sets
- [ ] Connection pooling configured
- [ ] Query result caching (Redis)

## References

- NOVA API Service: `/Users/ygahlot/newRelicProject/NOVA/nova-api-service/`
- SQLAlchemy Async: https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html
- PostgreSQL Performance: https://wiki.postgresql.org/wiki/Performance_Optimization
- Redis Patterns: https://redis.io/docs/manual/patterns/

## Notes

This skill document contains patterns to implement **later when needed**. For now:
- Keep things simple
- Focus on getting basic functionality working
- Add complexity only when solving actual problems
- Learn and debug step by step

**Remember**: Premature optimization is the root of all evil. Start simple, scale when needed.
