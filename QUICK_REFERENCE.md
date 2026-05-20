# Backend Refactoring Quick Reference

Quick reference for new reusable utilities and design patterns.

## 🎯 Quick Start

### When to Use What

| Task | Use This | Location |
|------|----------|----------|
| Database pagination | `QueryHelper.paginated_query()` | `app/core/query_helper.py` |
| OAuth URL generation | `OAuthProviderManager.get_authorization_url()` | `app/core/oauth_provider_manager.py` |
| OAuth callback handling | `OAuthProviderManager.handle_callback()` | `app/core/oauth_provider_manager.py` |
| Connection CRUD | `ConnectionManagementService` | `app/services/connection_management_service.py` |
| API responses | `ResponseBuilder.success()` | `app/core/response_builder.py` |
| Webhook handling | `WebhookHandler` (base class) | `app/core/webhook_handler.py` |
| Service layer | `CRUDService` (base class) | `app/services/base.py` |
| Repository layer | `BaseRepository` (base class) | `app/repositories/base.py` |

---

## 📊 QueryHelper

```python
from app/core/query_helper import QueryHelper

# Paginated query with filters
items, total = QueryHelper.paginated_query(
    Event,          # Model class
    db,             # Session
    page=1,         # Page number
    limit=20,       # Items per page
    status="active", # Filters (kwargs)
    category="running"
)

# Search across fields
query = QueryHelper.search_across_fields(
    query, Event, "marathon", ["name", "description"]
)

# Get single record
user = QueryHelper.get_or_none(User, db, email="user@example.com")

# Check existence
exists = QueryHelper.exists(Event, db, slug="my-event")
```

---

## 🔐 OAuth Provider Manager

```python
from app.core.oauth_provider_manager import OAuthProviderManager

# Get authorization URL
auth_url = OAuthProviderManager.get_authorization_url("google_fit")

# Handle OAuth callback (returns tokens + user info)
result = await OAuthProviderManager.handle_callback("strava", auth_code)
# Returns: {
#   "access_token": "...",
#   "refresh_token": "...",
#   "expires_at": datetime,
#   "scope": "...",
#   "user_info": {...}
# }

# Check if provider is supported
if OAuthProviderManager.is_supported("fitbit"):
    # Do something

# List all providers
providers = OAuthProviderManager.list_providers()
# Returns: ["google_fit", "strava", "fitbit", "wahoo", "garmin"]
```

---

## 🔌 Connection Management Service

```python
from app.services.connection_management_service import ConnectionManagementService

conn_service = ConnectionManagementService(db)

# Get user's connection for a provider
connection = conn_service.get_user_connection(
    user_id=user.id,
    provider="strava",
    active_only=True
)

# Get all user connections
all_conns = conn_service.get_all_user_connections(user.id)
# Returns: {"strava": {...}, "google_fit": {...}}

# Create/update connection
connection = conn_service.create_connection(
    user_id=user.id,
    provider="google_fit",
    access_token=token,
    refresh_token=refresh,
    expires_at=expires_at,
    user_info=user_info,
    scope="read write"
)

# Delete connection
success, provider = conn_service.delete_connection(
    connection_id=123,
    user_id=user.id
)

# Check for duplicate
is_duplicate = conn_service.check_duplicate_provider_connection(
    provider_user_id="google_12345",
    provider="google_fit",
    exclude_user_id=user.id
)

# Update last sync
conn_service.update_last_sync(user.id, "strava")
```

---

## 📦 Response Builder

```python
from app.core.response_builder import ResponseBuilder

# Success response
return ResponseBuilder.success(
    data={"user": user_dict},
    message="User created successfully"
)

# Paginated response
return ResponseBuilder.paginated(
    items=events,
    total=100,
    page=1,
    page_size=20
)

# Created response
return ResponseBuilder.created(
    data=event,
    resource_id=event.id,
    message="Event created"
)

# Error responses
return ResponseBuilder.not_found("User", user_id)
return ResponseBuilder.unauthorized()
return ResponseBuilder.validation_error({"email": ["Invalid format"]})
```

### Standard Response Formats

**Success:**
```json
{
  "success": true,
  "data": {...},
  "timestamp": "2024-01-15T10:30:00"
}
```

**Paginated:**
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 100,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "message": "Resource not found",
    "code": "NOT_FOUND"
  }
}
```

---

## 🪝 Webhook Handler

```python
from app.core.webhook_handler import RazorpayWebhookHandler

# Create custom webhook handler
class MyWebhookHandler(RazorpayWebhookHandler):
    def __init__(self, db: Session, secret: str):
        super().__init__(secret)
        self.db = db

    async def _handle_payment_captured(self, payment: Dict) -> Dict:
        # Your logic here
        return {"status": "processed"}

# Use in endpoint
@router.post("/webhooks/razorpay")
async def handle_webhook(request: Request, db: Session):
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    handler = MyWebhookHandler(db, os.getenv("RAZORPAY_SECRET"))
    return await handler.process(payload, signature, "payment")
```

---

## 🏗️ Service Layer

```python
from app.services.base import CRUDService

# Create a service
class EventService(CRUDService[Event, EventRepository]):
    def __init__(self, db: Session):
        super().__init__(db, EventRepository)

    # Add custom methods
    def get_upcoming_events(self):
        return self.repository.find_by(status="upcoming")

# Use in endpoint
@router.get("/events")
async def list_events(db: Session = Depends(get_db)):
    service = EventService(db)
    items, total = service.paginate(page=1, page_size=20)
    return ResponseBuilder.paginated(items, total, 1, 20)
```

### Available Methods (from CRUDService)

```python
service = EventService(db)

# CRUD operations
event = service.create({"name": "Marathon", ...})
event = service.get_by_id(123)
event = service.get_by_id_or_404(123)
events = service.get_all(skip=0, limit=100)
items, total = service.paginate(page=1, page_size=20)
event = service.update(123, {"status": "active"})
success = service.delete(123)

# Queries
exists = service.exists(123)
count = service.count(status="active")
events = service.bulk_create([{...}, {...}])
```

---

## 📋 Common Patterns

### Typical API Endpoint

```python
@router.post("/resources")
async def create_resource(
    data: ResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Create service
    service = ResourceService(db)

    # 2. Business logic
    resource = service.create(data.dict(), created_by=current_user.id)

    # 3. Return response
    return ResponseBuilder.created(resource, resource_id=resource.id)
```

### Paginated List Endpoint

```python
@router.get("/resources")
async def list_resources(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    items, total = QueryHelper.paginated_query(
        Resource, db, page=page, limit=limit, status=status
    )
    return ResponseBuilder.paginated(items, total, page, limit)
```

### OAuth Integration Endpoint

```python
@router.get("/auth/{provider}/authorize")
async def get_authorize_url(provider: str):
    auth_url = OAuthProviderManager.get_authorization_url(provider)
    return {"authorization_url": auth_url}

@router.post("/auth/{provider}/callback")
async def handle_callback(
    provider: str,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = await OAuthProviderManager.handle_callback(
        provider, request.get('code')
    )

    conn_service = ConnectionManagementService(db)
    connection = conn_service.create_connection(
        user_id=current_user.id,
        provider=provider,
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_at=result["expires_at"],
        user_info=result["user_info"],
        scope=result["scope"]
    )

    return ResponseBuilder.success({
        "provider": provider,
        "connected": True,
        "connection_id": connection.id
    })
```

---

## 🔍 Cheat Sheet

### Replace This Pattern

| Old Pattern | New Pattern |
|-------------|-------------|
| `query.offset(skip).limit(limit).all()` | `QueryHelper.paginated_query()` |
| Manual OAuth URL building | `OAuthProviderManager.get_authorization_url()` |
| Manual token exchange | `OAuthProviderManager.handle_callback()` |
| `db.query(Connection).filter(...).first()` | `conn_service.get_user_connection()` |
| `return {"success": True, "data": ...}` | `ResponseBuilder.success(data)` |
| Manual pagination logic | `service.paginate()` or `QueryHelper.paginated_query()` |
| Repetitive try-except | Use decorators from `app/core/decorators.py` |

### Import Quick Reference

```python
# Query operations
from app.core.query_helper import QueryHelper

# OAuth
from app.core.oauth_provider_manager import OAuthProviderManager

# Connections
from app.services.connection_management_service import ConnectionManagementService

# Responses
from app.core.response_builder import ResponseBuilder

# Webhooks
from app.core.webhook_handler import WebhookHandler, RazorpayWebhookHandler

# Services
from app.services.base import BaseService, CRUDService, OwnedResourceService

# Repositories
from app.repositories.base import BaseRepository, QueryBuilder

# Decorators
from app.core.decorators import (
    require_role, require_admin, log_execution,
    transactional, retry_on_db_error
)
```

---

## 🎨 Design Principles Applied

- **DRY (Don't Repeat Yourself):** Utilities eliminate duplication
- **SOLID Principles:**
  - Single Responsibility: Each class has one purpose
  - Open/Closed: Extendable without modification
  - Liskov Substitution: Base classes are interchangeable
  - Interface Segregation: Clean, focused interfaces
  - Dependency Inversion: Depend on abstractions
- **Separation of Concerns:** API → Service → Repository → Database
- **Composition over Inheritance:** Utilities are composable
- **Convention over Configuration:** Sensible defaults

---

## 📚 Full Documentation

- [REFACTORING_GUIDE.md](./REFACTORING_GUIDE.md) - Detailed examples and migration guide
- [ARCHITECTURE_IMPROVEMENTS.md](./ARCHITECTURE_IMPROVEMENTS.md) - Architecture overview
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - This document

---

## 🆘 Common Questions

**Q: Should I use QueryHelper or BaseRepository?**
A: Use `BaseRepository` in service layer. Use `QueryHelper` in API endpoints for simple queries.

**Q: How do I add a new OAuth provider?**
A: Create a new class extending `OAuthProvider` in `oauth_provider_manager.py` and register it.

**Q: Can I still use manual queries?**
A: Yes, but prefer utilities for common patterns. Use manual queries for complex, specific cases.

**Q: Are these changes backward compatible?**
A: Yes! These are additive utilities. Existing code continues to work.

**Q: How do I test code using these utilities?**
A: All utilities are easily mockable. See test examples in documentation.

---

**Last Updated:** May 2024
**Version:** 1.0
