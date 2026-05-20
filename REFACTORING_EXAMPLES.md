# Magic Strings Refactoring Examples

This document provides concrete before/after examples for refactoring magic strings in the GlycoGrit codebase.

## Table of Contents
1. [Models](#models)
2. [API Endpoints](#api-endpoints)
3. [Business Logic](#business-logic)
4. [Webhook Handlers](#webhook-handlers)
5. [Middleware](#middleware)
6. [Error Handling](#error-handling)

---

## Models

### User Model

#### Before
```python
# app/models/user.py
class User(Base):
    role = Column(String(50), nullable=False, server_default='user', index=True)
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'facebook', etc.
    primary_sync_source = Column(String(50), nullable=True)  # 'strava', 'google_fit', etc.
    gender = Column(String(20), nullable=True)

    @property
    def is_admin(self) -> bool:
        return self.role in ('admin', 'super_admin')
```

#### After
```python
# app/models/user.py
from app.core.enums import UserRole, Gender, OAuthProvider, FitnessTrackerProvider

class User(Base):
    role = Column(String(50), nullable=False, server_default=UserRole.USER, index=True)
    oauth_provider = Column(String(50), nullable=True)
    primary_sync_source = Column(String(50), nullable=True)
    gender = Column(String(20), nullable=True)

    @property
    def is_admin(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
```

### Payment Model

#### Before
```python
# app/models/payment.py
class Payment(Base):
    status = Column(String(50), default="pending")
    payment_method = Column(String(50), nullable=True)  # 'credit_card', 'debit_card', etc.
    gateway = Column(String(50), default="razorpay")

    def is_successful(self) -> bool:
        return self.status in ("completed", "authorized")
```

#### After
```python
# app/models/payment.py
from app.core.enums import PaymentStatus, PaymentMethod, PaymentGateway

class Payment(Base):
    status = Column(String(50), default=PaymentStatus.PENDING)
    payment_method = Column(String(50), nullable=True)
    gateway = Column(String(50), default=PaymentGateway.RAZORPAY)

    def is_successful(self) -> bool:
        return self.status in [PaymentStatus.COMPLETED, PaymentStatus.AUTHORIZED]
```

### Registration Model

#### Before
```python
# app/models/registration.py
class Registration(Base):
    status = Column(String(50), default="pending")
    payment_status = Column(String(50), default="pending")
    t_shirt_size = Column(String(10), nullable=True)  # 'S', 'M', 'L', etc.

    def is_confirmed(self) -> bool:
        return self.status == "confirmed" and self.payment_status == "completed"
```

#### After
```python
# app/models/registration.py
from app.core.enums import RegistrationStatus, PaymentStatus, TShirtSize

class Registration(Base):
    status = Column(String(50), default=RegistrationStatus.PENDING)
    payment_status = Column(String(50), default=PaymentStatus.PENDING)
    t_shirt_size = Column(String(10), nullable=True)

    def is_confirmed(self) -> bool:
        return (self.status == RegistrationStatus.CONFIRMED and
                self.payment_status == PaymentStatus.COMPLETED)
```

### Event Model

#### Before
```python
# app/models/event.py
class Event(Base):
    status = Column(String(50), default="draft")
    difficulty = Column(String(50), nullable=True)  # 'beginner', 'intermediate', 'advanced'

    def is_published(self) -> bool:
        return self.status == "published"

    def can_register(self) -> bool:
        return self.status in ("published", "upcoming")
```

#### After
```python
# app/models/event.py
from app.core.enums import EventStatus, EventDifficulty

class Event(Base):
    status = Column(String(50), default=EventStatus.DRAFT)
    difficulty = Column(String(50), nullable=True)

    def is_published(self) -> bool:
        return self.status == EventStatus.PUBLISHED

    def can_register(self) -> bool:
        return self.status in [EventStatus.PUBLISHED, EventStatus.UPCOMING]
```

---

## API Endpoints

### Authentication Endpoints

#### Before
```python
# app/api/auth.py
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/login")
async def login(credentials: LoginRequest):
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"status": "success", "token": token}
```

#### After
```python
# app/api/auth.py
from fastapi import APIRouter, HTTPException
from app.core.constants import APIVersion, APIRoutes, ErrorMessages
from app.core.enums import APIResponseStatus

router = APIRouter(
    prefix=f"{APIVersion.V1}{APIRoutes.AUTH}",
    tags=["Authentication"]
)

@router.post(APIRoutes.LOGIN)
async def login(credentials: LoginRequest):
    if not user:
        raise HTTPException(
            status_code=404,
            detail=ErrorMessages.USER_NOT_FOUND
        )

    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail=ErrorMessages.INVALID_CREDENTIALS
        )

    return {
        "status": APIResponseStatus.SUCCESS,
        "token": token
    }
```

### Event Endpoints

#### Before
```python
# app/api/events.py
@router.get("/api/v1/events")
async def list_events(status: str = None):
    query = db.query(Event)

    if status:
        if status not in ["draft", "published", "upcoming", "completed"]:
            raise HTTPException(400, "Invalid event status")
        query = query.filter(Event.status == status)

    return {"status": "success", "events": events}

@router.post("/api/v1/events")
async def create_event(event_data: EventCreate, current_user: User):
    if current_user.role not in ["admin", "organizer"]:
        raise HTTPException(403, "Only admins and organizers can create events")

    event = Event(**event_data.dict())
    event.status = "draft"
    db.add(event)
    db.commit()

    return {"status": "success", "event": event}
```

#### After
```python
# app/api/events.py
from app.core.constants import APIVersion, APIRoutes, ErrorMessages
from app.core.enums import EventStatus, UserRole, APIResponseStatus

@router.get(f"{APIVersion.V1}{APIRoutes.EVENTS}")
async def list_events(status: EventStatus = None):
    query = db.query(Event)

    if status:
        query = query.filter(Event.status == status)

    return {
        "status": APIResponseStatus.SUCCESS,
        "events": events
    }

@router.post(f"{APIVersion.V1}{APIRoutes.EVENTS}")
async def create_event(event_data: EventCreate, current_user: User):
    if current_user.role not in [UserRole.ADMIN, UserRole.ORGANIZER]:
        raise HTTPException(
            403,
            ErrorMessages.format_message(
                ErrorMessages.ORGANIZER_OR_ADMIN_ONLY
            )
        )

    event = Event(**event_data.dict())
    event.status = EventStatus.DRAFT
    db.add(event)
    db.commit()

    return {
        "status": APIResponseStatus.SUCCESS,
        "event": event
    }
```

---

## Business Logic

### Payment Processing

#### Before
```python
# app/services/payment_service.py
class PaymentService:
    def process_payment(self, payment_id: int):
        payment = db.query(Payment).get(payment_id)

        if payment.status == "completed":
            raise ValueError("Payment already processed")

        try:
            response = razorpay_client.capture_payment(payment.gateway_payment_id)

            if response["status"] == "captured":
                payment.status = "completed"
                payment.registration.status = "confirmed"

                # Send confirmation email
                send_email(
                    to=payment.user.email,
                    subject="Payment Successful",
                    body="Your payment has been processed successfully"
                )
            else:
                payment.status = "failed"

        except Exception as e:
            payment.status = "failed"
            raise

        db.commit()
        return {"status": "success"}
```

#### After
```python
# app/services/payment_service.py
from app.core.enums import PaymentStatus, RegistrationStatus, APIResponseStatus
from app.core.constants import ErrorMessages

class PaymentService:
    def process_payment(self, payment_id: int):
        payment = db.query(Payment).get(payment_id)

        if payment.status == PaymentStatus.COMPLETED:
            raise ValueError(ErrorMessages.PAYMENT_ALREADY_PROCESSED)

        try:
            response = razorpay_client.capture_payment(payment.gateway_payment_id)

            if response["status"] == "captured":
                payment.status = PaymentStatus.COMPLETED
                payment.registration.status = RegistrationStatus.CONFIRMED

                # Send confirmation email
                send_email(
                    to=payment.user.email,
                    subject="Payment Successful",
                    body="Your payment has been processed successfully"
                )
            else:
                payment.status = PaymentStatus.FAILED

        except Exception as e:
            payment.status = PaymentStatus.FAILED
            raise

        db.commit()
        return {"status": APIResponseStatus.SUCCESS}
```

### Activity Sync Service

#### Before
```python
# app/services/fitness_tracker_service.py
class FitnessTrackerService:
    def sync_activities(self, user_id: int, provider: str):
        user = db.query(User).get(user_id)

        if provider not in ["strava", "google_fit", "garmin", "fitbit"]:
            raise ValueError(f"Invalid provider: {provider}")

        if provider == "strava":
            connection = user.strava_connection
            if not connection:
                raise ValueError("Strava not connected")
            activities = self.fetch_strava_activities(connection)

        elif provider == "google_fit":
            connection = user.google_fit_connection
            if not connection:
                raise ValueError("Google Fit not connected")
            activities = self.fetch_google_fit_activities(connection)

        # Store activities
        for activity_data in activities:
            activity = Activity(
                user_id=user_id,
                source=provider,
                activity_type=activity_data.get("type", "running"),
                distance=activity_data["distance"],
            )
            db.add(activity)

        db.commit()
        return {"status": "success", "count": len(activities)}
```

#### After
```python
# app/services/fitness_tracker_service.py
from app.core.enums import FitnessTrackerProvider, ActivityType, APIResponseStatus
from app.core.constants import ErrorMessages

class FitnessTrackerService:
    def sync_activities(self, user_id: int, provider: FitnessTrackerProvider):
        user = db.query(User).get(user_id)

        if provider == FitnessTrackerProvider.STRAVA:
            connection = user.strava_connection
            if not connection:
                raise ValueError(
                    ErrorMessages.format_message(
                        ErrorMessages.TRACKER_NOT_CONNECTED,
                        tracker="Strava"
                    )
                )
            activities = self.fetch_strava_activities(connection)

        elif provider == FitnessTrackerProvider.GOOGLE_FIT:
            connection = user.google_fit_connection
            if not connection:
                raise ValueError(
                    ErrorMessages.format_message(
                        ErrorMessages.TRACKER_NOT_CONNECTED,
                        tracker="Google Fit"
                    )
                )
            activities = self.fetch_google_fit_activities(connection)

        # Store activities
        for activity_data in activities:
            activity = Activity(
                user_id=user_id,
                source=provider,
                activity_type=activity_data.get("type", ActivityType.RUNNING),
                distance=activity_data["distance"],
            )
            db.add(activity)

        db.commit()
        return {
            "status": APIResponseStatus.SUCCESS,
            "count": len(activities)
        }
```

---

## Webhook Handlers

### Razorpay Webhook

#### Before
```python
# app/api/webhooks.py
from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib

router = APIRouter()

@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    # Verify signature
    signature = request.headers.get("X-Razorpay-Signature")
    if not signature:
        raise HTTPException(400, "Missing signature")

    body = await request.body()
    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if signature != expected_signature:
        raise HTTPException(401, "Invalid signature")

    # Process webhook
    payload = await request.json()
    event_type = payload["event"]

    if event_type == "payment.captured":
        payment_id = payload["payload"]["payment"]["entity"]["id"]
        payment = db.query(Payment).filter_by(gateway_payment_id=payment_id).first()

        if payment:
            payment.status = "completed"
            payment.registration.status = "confirmed"
            db.commit()

    elif event_type == "payment.failed":
        payment_id = payload["payload"]["payment"]["entity"]["id"]
        payment = db.query(Payment).filter_by(gateway_payment_id=payment_id).first()

        if payment:
            payment.status = "failed"
            db.commit()

    return {"status": "success"}
```

#### After
```python
# app/api/webhooks.py
from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib
from app.core.constants import HTTPHeaders, APIRoutes, ErrorMessages, RazorpayEvents
from app.core.enums import PaymentStatus, RegistrationStatus, APIResponseStatus

router = APIRouter()

@router.post(APIRoutes.WEBHOOKS + "/razorpay")
async def razorpay_webhook(request: Request):
    # Verify signature
    signature = request.headers.get(HTTPHeaders.X_RAZORPAY_SIGNATURE)
    if not signature:
        raise HTTPException(400, ErrorMessages.WEBHOOK_SIGNATURE_INVALID)

    body = await request.body()
    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if signature != expected_signature:
        raise HTTPException(401, ErrorMessages.WEBHOOK_SIGNATURE_INVALID)

    # Process webhook
    payload = await request.json()
    event_type = payload["event"]

    if event_type == RazorpayEvents.PAYMENT_CAPTURED:
        payment_id = payload["payload"]["payment"]["entity"]["id"]
        payment = db.query(Payment).filter_by(gateway_payment_id=payment_id).first()

        if payment:
            payment.status = PaymentStatus.COMPLETED
            payment.registration.status = RegistrationStatus.CONFIRMED
            db.commit()

    elif event_type == RazorpayEvents.PAYMENT_FAILED:
        payment_id = payload["payload"]["payment"]["entity"]["id"]
        payment = db.query(Payment).filter_by(gateway_payment_id=payment_id).first()

        if payment:
            payment.status = PaymentStatus.FAILED
            db.commit()

    return {"status": APIResponseStatus.SUCCESS}
```

---

## Middleware

### Request ID Middleware

#### Before
```python
# app/middleware/request_id.py
from fastapi import Request
import uuid

async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response
```

#### After
```python
# app/middleware/request_id.py
from fastapi import Request
import uuid
from app.core.constants import HTTPHeaders

async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())

    response = await call_next(request)
    response.headers[HTTPHeaders.X_REQUEST_ID] = request_id

    return response
```

### Rate Limiting Middleware

#### Before
```python
# app/middleware/rate_limit.py
from fastapi import Request, HTTPException

async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host

    if is_rate_limited(client_ip):
        raise HTTPException(429, "Too many requests")

    response = await call_next(request)

    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Remaining"] = str(get_remaining(client_ip))
    response.headers["X-RateLimit-Reset"] = str(get_reset_time(client_ip))

    return response
```

#### After
```python
# app/middleware/rate_limit.py
from fastapi import Request, HTTPException
from app.core.constants import HTTPHeaders, ErrorMessages

async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host

    if is_rate_limited(client_ip):
        raise HTTPException(429, ErrorMessages.RATE_LIMIT_EXCEEDED)

    response = await call_next(request)

    # Add rate limit headers
    response.headers[HTTPHeaders.X_RATELIMIT_LIMIT] = "100"
    response.headers[HTTPHeaders.X_RATELIMIT_REMAINING] = str(get_remaining(client_ip))
    response.headers[HTTPHeaders.X_RATELIMIT_RESET] = str(get_reset_time(client_ip))

    return response
```

---

## Error Handling

### Exception Handlers

#### Before
```python
# app/core/exception_handlers.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "failed",
            "error": exc.detail,
            "request_id": request.headers.get("X-Request-ID")
        }
    )

async def validation_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=400,
        content={
            "status": "failed",
            "error": "Validation error",
            "details": str(exc)
        }
    )
```

#### After
```python
# app/core/exception_handlers.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.constants import HTTPHeaders, ErrorMessages
from app.core.enums import APIResponseStatus

async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": APIResponseStatus.FAILED,
            "error": exc.detail,
            "request_id": request.headers.get(HTTPHeaders.X_REQUEST_ID)
        }
    )

async def validation_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=400,
        content={
            "status": APIResponseStatus.FAILED,
            "error": ErrorMessages.INVALID_REQUEST,
            "details": str(exc)
        }
    )
```

### File Upload Validation

#### Before
```python
# app/api/gallery.py
from fastapi import UploadFile, HTTPException

ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"]
MAX_SIZE = 5 * 1024 * 1024  # 5MB

async def upload_image(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            400,
            f"Invalid file type. Allowed: {', '.join(ALLOWED_TYPES)}"
        )

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "File too large. Max 5MB")

    # Upload to storage
    url = await storage.upload(content, file.filename)

    return {"status": "success", "url": url}
```

#### After
```python
# app/api/gallery.py
from fastapi import UploadFile, HTTPException
from app.core.constants import AllowedMimeTypes, ErrorMessages
from app.core.constants.mime_types import is_valid_mime_type
from app.core.enums import APIResponseStatus

MAX_SIZE = 5 * 1024 * 1024  # 5MB

async def upload_image(file: UploadFile):
    if not is_valid_mime_type(file.content_type, AllowedMimeTypes.GALLERY_IMAGES):
        raise HTTPException(
            400,
            ErrorMessages.format_message(
                ErrorMessages.INVALID_FILE_TYPE,
                types=", ".join(AllowedMimeTypes.GALLERY_IMAGES)
            )
        )

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, ErrorMessages.FILE_TOO_LARGE)

    # Upload to storage
    url = await storage.upload(content, file.filename)

    return {
        "status": APIResponseStatus.SUCCESS,
        "url": url
    }
```

---

## Summary

### Key Principles

1. **Import at the top**: Always import constants and enums at the module level
2. **Use enums for database values**: Status, type, category fields should use enums
3. **Use constants for infrastructure**: Headers, routes, error messages use constants
4. **Type hints**: Add proper type hints when using enums
5. **Consistency**: Use the same constant everywhere for the same value

### Benefits Achieved

✅ **Type Safety**: IDE autocomplete catches typos
✅ **Consistency**: Same value used everywhere
✅ **Maintainability**: Change once, update everywhere
✅ **Readability**: Self-documenting code
✅ **Testability**: Easy to mock and test

### Next Steps

1. Use the `migrate_magic_strings.py` script to find remaining magic strings
2. Follow these examples to refactor your code
3. Run tests after each major refactoring
4. Update documentation as needed

---

**Last Updated**: 2026-05-21
