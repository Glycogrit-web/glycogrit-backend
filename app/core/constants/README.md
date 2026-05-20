# Constants Module

This module provides centralized management of all magic strings used throughout the GlycoGrit backend application.

## Quick Start

### Import What You Need

```python
# Import constants
from app.core.constants import (
    HTTPHeaders,
    ErrorMessages,
    RazorpayEvents,
    MimeTypes,
    AllowedMimeTypes,
    APIRoutes,
    CommonFields
)

# Import enums (from parent module)
from app.core.enums import (
    PaymentStatus,
    RegistrationStatus,
    EventStatus,
    ActivityType,
    UserRole
)
```

### Basic Usage

```python
# Instead of magic strings
if payment.status == "completed":
    headers = {"X-Request-ID": request_id}
    raise HTTPException(404, "User not found")

# Use constants and enums
if payment.status == PaymentStatus.COMPLETED:
    headers = {HTTPHeaders.X_REQUEST_ID: request_id}
    raise HTTPException(404, ErrorMessages.USER_NOT_FOUND)
```

## Available Modules

### http_headers.py
Contains all HTTP header names used in the application.

**Classes:**
- `HTTPHeaders` - Header names (X-Request-ID, Authorization, etc.)
- `HeaderValues` - Common header values (Bearer prefix, content types)

**Example:**
```python
from app.core.constants import HTTPHeaders

request_id = request.headers.get(HTTPHeaders.X_REQUEST_ID)
response.headers[HTTPHeaders.X_PROCESS_TIME] = str(duration)
```

### error_messages.py
Contains all error messages with formatting support.

**Classes:**
- `ErrorMessages` - All application error messages

**Example:**
```python
from app.core.constants import ErrorMessages

raise HTTPException(404, ErrorMessages.USER_NOT_FOUND)

# Dynamic messages
error = ErrorMessages.format_message(
    ErrorMessages.RESOURCE_NOT_FOUND,
    resource="Challenge"
)
```

### webhook_events.py
Contains webhook event type constants for various services.

**Classes:**
- `RazorpayEvents` - Razorpay webhook event types
- `StripeEvents` - Stripe webhook event types
- `StravaWebhookEvents` - Strava webhook event types
- `ShiprocketEvents` - Shiprocket webhook event types
- `WebhookStatus` - Webhook processing status

**Example:**
```python
from app.core.constants import RazorpayEvents

if event_type == RazorpayEvents.PAYMENT_CAPTURED:
    process_payment_capture()
```

### mime_types.py
Contains MIME type constants and validation utilities.

**Classes:**
- `MimeTypes` - All MIME type constants
- `AllowedMimeTypes` - Grouped MIME types for validation
- `FileExtensions` - Extension to MIME type mappings

**Functions:**
- `get_mime_type(filename)` - Get MIME type from filename
- `get_file_extension(mime_type)` - Get extension from MIME type
- `is_valid_mime_type(mime_type, allowed_types)` - Validate MIME type

**Example:**
```python
from app.core.constants import AllowedMimeTypes, MimeTypes
from app.core.constants.mime_types import is_valid_mime_type

if not is_valid_mime_type(file.content_type, AllowedMimeTypes.PROFILE_PICTURES):
    raise ValueError("Invalid file type")
```

### api_routes.py
Contains API route path constants and utilities.

**Classes:**
- `APIVersion` - API version prefixes
- `APIRoutes` - Route path segments
- `RouteParams` - Route parameter names
- `QueryParams` - Query parameter names

**Functions:**
- `build_route(*segments)` - Build route from segments
- `build_admin_route(route)` - Build admin route

**Example:**
```python
from app.core.constants import APIVersion, APIRoutes, build_route

@router.get(build_route(APIVersion.V1, APIRoutes.EVENTS, "{event_id}"))
async def get_event(event_id: int):
    pass
```

### database_fields.py
Contains database field name constants.

**Classes:**
- `CommonFields` - Common fields (id, created_at, status, etc.)
- `UserFields` - User table field names
- `EventFields` - Event table field names
- `PaymentFields` - Payment table field names
- And more for each domain...

**Example:**
```python
from app.core.constants import UserFields, CommonFields

query = select(User).where(
    getattr(User, UserFields.EMAIL) == email,
    getattr(User, CommonFields.IS_ACTIVE) == True
)
```

## Related: Enums Module

Enums are located in `app/core/enums.py` and should be used for:
- Status values (PaymentStatus, RegistrationStatus, EventStatus)
- Type categorizations (ActivityType, RewardType)
- User roles (UserRole)
- Other enumerated values stored in the database

**Example:**
```python
from app.core.enums import PaymentStatus, UserRole

payment.status = PaymentStatus.COMPLETED
if user.role == UserRole.ADMIN:
    grant_admin_access()
```

## Best Practices

### 1. Import at Module Level
Always import constants at the top of your file:

```python
# ✅ Good
from app.core.constants import HTTPHeaders, ErrorMessages
from app.core.enums import PaymentStatus

def my_function():
    if payment.status == PaymentStatus.COMPLETED:
        pass

# ❌ Bad
def my_function():
    from app.core.enums import PaymentStatus
    if payment.status == PaymentStatus.COMPLETED:
        pass
```

### 2. Use Enums for Database Values
Use enums for any value that will be stored in the database:

```python
# ✅ Good
from app.core.enums import PaymentStatus
payment.status = PaymentStatus.COMPLETED

# ❌ Bad
payment.status = "completed"
```

### 3. Use Constants for Infrastructure
Use constants for headers, error messages, routes, etc.:

```python
# ✅ Good
from app.core.constants import HTTPHeaders, ErrorMessages
request_id = request.headers.get(HTTPHeaders.X_REQUEST_ID)
raise HTTPException(404, ErrorMessages.USER_NOT_FOUND)

# ❌ Bad
request_id = request.headers.get("X-Request-ID")
raise HTTPException(404, "User not found")
```

### 4. Type Hints
Add proper type hints when using enums:

```python
# ✅ Good
from app.core.enums import PaymentStatus

def process_payment(status: PaymentStatus) -> dict:
    if status == PaymentStatus.COMPLETED:
        return {"success": True}

# ❌ Bad (no type hint)
def process_payment(status):
    if status == "completed":
        return {"success": True}
```

### 5. Dynamic Error Messages
Use the `format_message` utility for dynamic errors:

```python
# ✅ Good
from app.core.constants import ErrorMessages

error = ErrorMessages.format_message(
    ErrorMessages.RESOURCE_NOT_FOUND,
    resource="Event"
)

# ❌ Bad
error = f"Event not found"
```

## Migration

If you're migrating existing code:

1. **Scan for magic strings:**
   ```bash
   python migrate_magic_strings.py --scan
   ```

2. **Generate detailed report:**
   ```bash
   python migrate_magic_strings.py --report
   ```

3. **Follow the examples in:**
   - `REFACTORING_EXAMPLES.md` - Concrete before/after examples
   - `MAGIC_STRINGS_MIGRATION_CHECKLIST.md` - Step-by-step checklist
   - `CONSTANTS_MANAGEMENT_GUIDE.md` - Complete usage guide

## Documentation

For complete documentation, see:
- [Constants Management Guide](../../../CONSTANTS_MANAGEMENT_GUIDE.md) - Complete usage guide
- [Refactoring Examples](../../REFACTORING_EXAMPLES.md) - Before/after code examples
- [Migration Checklist](../../../MAGIC_STRINGS_MIGRATION_CHECKLIST.md) - Step-by-step migration guide

## Contributing

When adding new constants:

1. **Determine the category** - Headers, errors, routes, etc.
2. **Add to appropriate file** - Choose the right constants file
3. **Update `__init__.py`** - Export new classes if needed
4. **Document** - Add usage example if it's a new category
5. **Test** - Ensure existing code still works

## Support

For questions:
1. Check this README first
2. Review the main constants guide
3. Look at refactoring examples
4. Check existing code for similar patterns
5. Ask the team

---

**Version:** 1.0.0
**Last Updated:** 2026-05-21
