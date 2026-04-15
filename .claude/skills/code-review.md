# Code Review Skill

**Purpose**: Automatically review Python/FastAPI code for adherence to project standards, best practices, and security guidelines.

## Review Checklist

### 1. File Organization and Naming ✅
- [ ] Files follow snake_case naming convention
- [ ] Modules organized in appropriate directories (`app/api/`, `app/models/`, etc.)
- [ ] Related code grouped logically
- [ ] No duplicate or redundant files

**Good**:
```
app/
├── api/v1/endpoints/
│   ├── users.py
│   ├── rides.py
│   └── events.py
├── models/
│   ├── user.py
│   ├── ride.py
│   └── event.py
```

**Bad**:
```
app/
├── Users.py
├── user_stuff.py
├── handleUsers.py  # Mixed naming conventions
```

### 2. FastAPI Best Practices ✅
- [ ] Route handlers are async when appropriate
- [ ] Dependency injection used for database sessions
- [ ] Proper status codes returned
- [ ] Response models defined with Pydantic
- [ ] Request validation with Pydantic schemas
- [ ] Proper error handling with HTTPException

**Good**:
```python
@router.post("/rides/", response_model=RideResponse, status_code=201)
async def create_ride(
    ride: RideCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new ride."""
    new_ride = Ride(**ride.dict(), organizer_id=current_user.id)
    db.add(new_ride)
    await db.commit()
    await db.refresh(new_ride)
    return new_ride
```

**Bad**:
```python
@router.post("/rides/")  # No response model, no status code
def create_ride(ride):  # Not async, no type hints, no dependency injection
    # Direct DB access without session management
    new_ride = Ride(**ride)
    db.add(new_ride)
    db.commit()
    return new_ride
```

### 3. Python Type Hints ✅
- [ ] All function parameters have type hints
- [ ] All function return types specified
- [ ] Optional types used correctly
- [ ] Generic types properly typed (List, Dict, etc.)

**Good**:
```python
from typing import List, Optional
from uuid import UUID

async def get_ride(
    ride_id: UUID,
    db: AsyncSession
) -> Optional[Ride]:
    result = await db.execute(
        select(Ride).where(Ride.id == ride_id)
    )
    return result.scalar_one_or_none()

async def list_rides(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[Ride]:
    result = await db.execute(
        select(Ride).offset(skip).limit(limit)
    )
    return result.scalars().all()
```

### 4. SQLAlchemy 2.0 Patterns ✅
- [ ] Using async sessions
- [ ] Proper relationship definitions
- [ ] Lazy loading avoided (use eager loading)
- [ ] Transactions handled correctly
- [ ] Proper cascade settings

**Good**:
```python
from sqlalchemy import select, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

class Ride(Base):
    __tablename__ = "rides"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200))
    organizer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

    # Relationship with explicit lazy loading
    organizer: Mapped["User"] = relationship(
        back_populates="organized_rides",
        lazy="selectin"
    )
```

### 5. Pydantic Schema Design ✅
- [ ] Separate schemas for Create, Update, Response
- [ ] Base schemas used for common fields
- [ ] Config class with `from_attributes = True`
- [ ] Field validation with validators
- [ ] Proper use of Optional for nullable fields

**Good**:
```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID

class RideBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    start_time: datetime
    distance_km: float = Field(..., gt=0, le=500)
    difficulty: str = Field(..., pattern="^(easy|moderate|hard)$")

class RideCreate(RideBase):
    max_participants: int = Field(default=20, ge=2, le=100)

    @validator('start_time')
    def start_time_must_be_future(cls, v):
        if v <= datetime.utcnow():
            raise ValueError('start_time must be in the future')
        return v

class RideResponse(RideBase):
    id: UUID
    organizer_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### 6. Authentication & Authorization ✅
- [ ] Endpoints properly protected with dependencies
- [ ] Firebase token validation implemented
- [ ] User authorization checked (e.g., only organizer can edit ride)
- [ ] No sensitive data in responses

**Good**:
```python
async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Validate Firebase token and get current user."""
    try:
        token = authorization.replace("Bearer ", "")
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token["uid"]

        result = await db.execute(
            select(User).where(User.firebase_uid == uid)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication")

@router.delete("/rides/{ride_id}", status_code=204)
async def delete_ride(
    ride_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a ride (organizer only)."""
    ride = await get_ride_or_404(ride_id, db)

    if ride.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.delete(ride)
    await db.commit()
```

### 7. Error Handling ✅
- [ ] Proper HTTP exceptions used
- [ ] Meaningful error messages
- [ ] Appropriate status codes
- [ ] No raw exceptions leaked to client
- [ ] Database errors caught and handled

**Good**:
```python
from fastapi import HTTPException, status

async def get_ride_or_404(ride_id: UUID, db: AsyncSession) -> Ride:
    """Get ride by ID or raise 404."""
    result = await db.execute(
        select(Ride).where(Ride.id == ride_id)
    )
    ride = result.scalar_one_or_none()

    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ride {ride_id} not found"
        )

    return ride
```

### 8. Security Best Practices ✅
- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all endpoints
- [ ] SQL injection prevented (using SQLAlchemy ORM)
- [ ] No sensitive data in logs
- [ ] CORS properly configured
- [ ] Rate limiting considered for public endpoints

**Security Checklist**:
```python
# ❌ BAD - Hardcoded secret
JWT_SECRET = "super-secret-key-123"

# ✅ GOOD - From environment
from app.core.config import settings
JWT_SECRET = settings.jwt_secret_key

# ❌ BAD - SQL injection vulnerable
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ GOOD - SQLAlchemy ORM (safe)
result = await db.execute(
    select(User).where(User.id == user_id)
)

# ❌ BAD - Logging sensitive data
logger.info(f"User password: {password}")

# ✅ GOOD - No sensitive data in logs
logger.info(f"User {user_id} authenticated successfully")
```

### 9. Code Organization ✅
- [ ] Single Responsibility Principle followed
- [ ] Functions are concise (<50 lines)
- [ ] No code duplication
- [ ] Helper functions extracted
- [ ] Business logic separated from route handlers

**Good Pattern**:
```python
# app/services/ride_service.py
class RideService:
    """Business logic for rides."""

    @staticmethod
    async def create_ride(
        ride_data: RideCreate,
        organizer: User,
        db: AsyncSession
    ) -> Ride:
        """Create a new ride with validation."""
        # Business logic here
        ...

# app/api/v1/endpoints/rides.py
@router.post("/rides/", response_model=RideResponse)
async def create_ride(
    ride: RideCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create ride endpoint."""
    return await RideService.create_ride(ride, current_user, db)
```

### 10. Testing Considerations ✅
- [ ] Code is testable (dependencies injected)
- [ ] No direct database access in route handlers
- [ ] External dependencies mockable
- [ ] Test fixtures available

### 11. Documentation ✅
- [ ] Docstrings on all public functions
- [ ] API endpoint descriptions provided
- [ ] Complex logic commented
- [ ] README updated if needed

**Good**:
```python
@router.get("/rides/", response_model=List[RideResponse])
async def list_rides(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    difficulty: Optional[str] = Query(None, pattern="^(easy|moderate|hard)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all rides with optional filtering.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        difficulty: Filter by difficulty level (easy, moderate, hard)

    Returns:
        List of rides matching the criteria
    """
    query = select(Ride).offset(skip).limit(limit)

    if difficulty:
        query = query.where(Ride.difficulty == difficulty)

    result = await db.execute(query)
    return result.scalars().all()
```

### 12. Performance Considerations ✅
- [ ] N+1 queries avoided (use eager loading)
- [ ] Proper indexing on database columns
- [ ] Pagination implemented for list endpoints
- [ ] Async/await used correctly

**Good**:
```python
# Eager load relationships to avoid N+1
result = await db.execute(
    select(Ride)
    .options(selectinload(Ride.organizer))
    .options(selectinload(Ride.participants))
)
rides = result.scalars().all()
```

## Review Process

1. **Automatic Checks**
   - Run after file save or commit
   - Highlight issues in code

2. **Manual Review**
   ```bash
   claude skill code-review
   ```

3. **Review Output**
   ```markdown
   ## Code Review Results

   ### ✅ Passed (8/12)
   - File organization
   - Type hints
   - Error handling
   - Security practices
   - Documentation
   - FastAPI patterns
   - Pydantic schemas
   - Authentication

   ### ⚠️ Warnings (2/12)
   - Performance: Potential N+1 query in `get_rides_with_participants()`
   - Testing: Missing test coverage for `update_ride()`

   ### ❌ Failed (2/12)
   - SQLAlchemy: Using deprecated `Query` API instead of `select()`
   - Code organization: Route handler has 75 lines (max 50)

   ### Recommendations
   1. Refactor `app/api/v1/endpoints/rides.py:45` to use SQLAlchemy 2.0 select()
   2. Extract business logic from `create_ride_with_participants()` to service layer
   3. Add eager loading for participants in `get_rides_with_participants()`
   ```

## Common Issues and Fixes

### Issue 1: Missing Type Hints
```python
# ❌ Before
async def get_user(user_id):
    return await db.get(User, user_id)

# ✅ After
async def get_user(user_id: UUID) -> Optional[User]:
    return await db.get(User, user_id)
```

### Issue 2: No Response Model
```python
# ❌ Before
@router.get("/users/{user_id}")
async def get_user(user_id: UUID):
    return user

# ✅ After
@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID) -> UserResponse:
    return user
```

### Issue 3: Hardcoded Values
```python
# ❌ Before
DATABASE_URL = "postgresql://user:pass@localhost/db"

# ✅ After
from app.core.config import settings
DATABASE_URL = settings.database_url
```

## Configuration

Edit `.claude/code-review.config.json`:
```json
{
  "enabled": true,
  "auto_review": true,
  "rules": {
    "type_hints": "error",
    "response_models": "error",
    "security": "error",
    "performance": "warning",
    "documentation": "warning"
  },
  "ignore_patterns": [
    "tests/**",
    "alembic/versions/**"
  ]
}
```

## Integration

- Runs automatically on file save
- Can be triggered manually
- Integrates with git pre-commit hooks
- Provides actionable feedback

## Notes

- **Non-blocking**: Won't prevent commits
- **Educational**: Explains why something is an issue
- **Configurable**: Adjust rules per project needs
- **Fast**: Uses AST parsing, not full execution
