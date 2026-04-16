# Database Management Best Practices

## Learned from NOVA API Service

This document outlines the professional database management patterns and best practices we're implementing, based on analysis of the NOVA API service codebase.

## ✅ What We've Implemented

### 1. SQL-Based Migration System

**Pattern**: Simple, maintainable SQL migration files with tracking

**Implementation**: `database_scripts/run_migrations.py`

- ✅ Migration files with numeric prefixes (001_, 002_, etc.)
- ✅ Migration tracking table (`schema_migrations`)
- ✅ Checksum validation
- ✅ Execution time tracking
- ✅ Rollback prevention (never modify existing migrations)

**Why**: SQL migrations are:
- Easy to review in PRs
- Database-agnostic SQL syntax
- Can be run manually if needed
- Clear audit trail

### 2. Repository Pattern

**Pattern**: Abstract data access layer separating business logic from database operations

**Implementation**: `app/repositories/base.py`

**Key Features**:
- Generic CRUD operations
- Type safety with TypeVar
- Consistent interface across all models
- Easier testing with mock repositories
- Centralized query optimization

**Example**:
```python
class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def find_by_email(self, email: str) -> Optional[User]:
        return self.db.query(self.model).filter(
            self.model.email == email
        ).first()
```

### 3. Database Health Monitoring

**Pattern**: Comprehensive monitoring utilities for production readiness

**Implementation**: `app/core/database_monitor.py`

**Features**:
- Connection health checks
- Connection pool statistics
- Database size metrics
- Table size analysis
- Active connection tracking
- Index usage statistics
- Slow query identification
- Full health reports

### 4. Configuration Management

**Pattern**: Validated configuration classes with environment variables

**Implementation**: `app/core/config.py`

**Based on NOVA's**:
- Validation on import
- Environment variable defaults
- Type-safe configuration
- Configuration summary logging

## 🎯 NOVA Patterns We Should Adopt

### 1. Async Database Operations

**NOVA Pattern**:
```python
# They use AsyncSession with asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

DATABASE_URL = f"postgresql+asyncpg://{USER}:{PASS}@{HOST}:{PORT}/{DB}"

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_timeout=30
)
```

**Benefits**:
- Better concurrency for I/O-bound operations
- Non-blocking database calls
- Better resource utilization
- Scalability for high-traffic APIs

**Our Implementation** (currently synchronous):
```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)
```

**Recommendation**: Start with sync, migrate to async when needed

### 2. Session Injection (Dependency Injection)

**NOVA Pattern**:
```python
# Repository doesn't own session
class BaseRepository:
    def __init__(self, session: AsyncSession, model_class: type[ModelType]):
        self.session = session  # Injected, not owned
        self.model_class = model_class
```

**Benefits**:
- Caller controls transactions
- Multiple repositories can share one session
- Better transaction management
- Easier testing

**Our Current Pattern**:
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Recommendation**: Keep our current pattern for simplicity, it's FastAPI standard

### 3. Configuration Validation

**NOVA Pattern**:
```python
class DatabaseConfig:
    CONNECTION_POOL_SIZE: int = 10
    CONNECTION_POOL_MAX_OVERFLOW: int = 20
    QUERY_TIMEOUT: int = 30

    @classmethod
    def validate_config(cls) -> None:
        errors = []
        if cls.CONNECTION_POOL_SIZE <= 0:
            errors.append("POOL_SIZE must be > 0")
        if errors:
            raise ValueError("\\n".join(errors))

# Validate on import
DatabaseConfig.validate_config()
```

**Benefits**:
- Fail fast on invalid configuration
- Clear error messages
- Prevents runtime surprises
- Self-documenting configuration

**Action Item**: Add validation to our `config.py`

### 4. Connection Pool Best Practices

**NOVA Configuration**:
```python
pool_pre_ping=True          # Verify connections before use
pool_size=10                # Base pool size
max_overflow=20             # Additional connections
pool_recycle=3600           # Recycle after 1 hour
pool_timeout=30             # Wait 30s for connection
connect_args={
    "timeout": 10,          # Connection timeout
    "command_timeout": 60   # Query timeout
}
```

**Our Configuration**:
```python
pool_pre_ping=True
pool_size=5
max_overflow=10
connect_args={
    "connect_timeout": 10
}
```

**Recommendation**: Increase pool size for production

### 5. Logging Best Practices

**NOVA Pattern**:
```python
class BaseRepository:
    def __init__(self, session, model_class):
        self.logger = get_logger(self.__class__.__name__)

    async def create(self, **kwargs):
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            await self.session.flush()
            self.logger.debug(f"Created {self.model_class.__name__} with id={instance.id}")
            return instance
        except IntegrityError as e:
            self.logger.error(f"IntegrityError: {e}")
            raise
```

**Benefits**:
- Consistent logging format
- Easy to trace operations
- Helps debugging production issues
- Audit trail

**Action Item**: Add logging to our repositories

## 📋 Implementation Checklist

### Immediate Actions

- [x] SQL migration system
- [x] Repository pattern base class
- [x] Database health monitoring
- [x] Basic configuration management
- [ ] Add configuration validation
- [ ] Add comprehensive logging to repositories
- [ ] Document transaction management patterns

### Future Enhancements

- [ ] **Async Operations** (when scaling is needed)
  - Migrate to `asyncpg` driver
  - Update all repositories to async
  - Update FastAPI endpoints to async

- [ ] **Advanced Monitoring**
  - Integrate Prometheus metrics
  - Add query performance tracking
  - Set up alerting for slow queries
  - Track connection pool exhaustion

- [ ] **Caching Layer**
  - Add Redis for leaderboards
  - Cache frequently accessed data
  - Implement cache invalidation strategy

- [ ] **Connection Pool Tuning**
  - Increase pool_size for production (10-20)
  - Add query timeout configuration
  - Implement connection retry logic

## 🔒 Security Best Practices

### 1. Environment Variables

✅ **Do**:
```python
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set")
```

❌ **Don't**:
```python
DATABASE_URL = "postgresql://user:pass@host:5432/db"  # Hardcoded!
```

### 2. SQL Injection Prevention

✅ **Do** (Parameterized Queries):
```python
db.query(User).filter(User.email == email).first()
# or
db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})
```

❌ **Don't** (String Interpolation):
```python
db.execute(f"SELECT * FROM users WHERE email = '{email}'")  # Vulnerable!
```

### 3. Password Hashing

✅ **Do**:
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_hash = pwd_context.hash(password)
```

❌ **Don't**:
```python
import hashlib
password_hash = hashlib.sha256(password.encode()).hexdigest()  # Not secure!
```

## 📊 Performance Optimization

### 1. Indexing Strategy

**From our schema**:
```sql
-- Primary indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);

-- Composite indexes for common queries
CREATE INDEX idx_users_city_state ON users(city, state);
CREATE INDEX idx_events_location ON events(city, state, country);

-- Foreign key indexes
CREATE INDEX idx_registrations_user_event ON registrations(user_id, event_id);
```

**Rules**:
1. Index foreign keys
2. Index columns in WHERE clauses
3. Index columns in ORDER BY
4. Use composite indexes for multi-column queries
5. Monitor unused indexes (use `database_monitor.get_index_usage()`)

### 2. Query Optimization

**Use EXPLAIN ANALYZE**:
```sql
EXPLAIN ANALYZE
SELECT e.*, COUNT(r.id) as registrations
FROM events e
LEFT JOIN registrations r ON e.id = r.event_id
WHERE e.status = 'registration_open'
GROUP BY e.id;
```

**Avoid N+1 Queries**:
```python
# Bad: N+1 queries
events = db.query(Event).all()
for event in events:
    registrations = event.registrations  # Additional query per event

# Good: Single query with join
events = db.query(Event).options(
    joinedload(Event.registrations)
).all()
```

### 3. Connection Pooling

**Monitor Pool Health**:
```python
from app.core.database_monitor import DatabaseMonitor

stats = DatabaseMonitor.get_connection_pool_stats()
if stats['checked_out_connections'] >= stats['pool_size']:
    logger.warning("Connection pool exhausted!")
```

## 🛠️ Development Workflow

### 1. Making Schema Changes

```bash
# 1. Create new migration file
touch database_scripts/002_add_user_preferences.sql

# 2. Write SQL in migration file
# 3. Test locally
python database_scripts/db_manager.py reset --yes
python database_scripts/run_migrations.py migrate

# 4. Verify changes
python database_scripts/db_manager.py tables

# 5. Commit and deploy
git add database_scripts/
git commit -m "Add user preferences table"
git push

# 6. Run on Railway
railway run python database_scripts/run_migrations.py migrate
```

### 2. Testing Changes

```bash
# Reset database
python database_scripts/db_manager.py reset --yes

# Run migrations
python database_scripts/run_migrations.py migrate

# Seed test data
python database_scripts/db_manager.py seed

# Verify
python database_scripts/db_manager.py stats
```

### 3. Backup Before Changes

```bash
# Create backup
python database_scripts/db_manager.py backup --output pre_migration_backup.sql

# If something goes wrong, restore:
psql $DATABASE_URL < pre_migration_backup.sql
```

## 📚 Additional Resources

- [SQLAlchemy Best Practices](https://docs.sqlalchemy.org/en/14/orm/tutorial.html)
- [PostgreSQL Performance Tips](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [FastAPI Database Guide](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)

## 🎓 Key Takeaways

1. **Separation of Concerns**: Models, repositories, and business logic are separate
2. **Type Safety**: Use TypeVar and type hints throughout
3. **Transaction Management**: Caller controls commits, not repositories
4. **Configuration Validation**: Fail fast on invalid config
5. **Monitoring**: Build observability from day one
6. **Security**: Never trust user input, always use parameterized queries
7. **Performance**: Index wisely, monitor query performance
8. **Testing**: Use dependency injection for easy mocking

---

Generated for GlycoGrit Backend • Based on NOVA API Service patterns
