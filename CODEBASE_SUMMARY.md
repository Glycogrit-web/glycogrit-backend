# GlycoGrit Backend - Codebase Summary

> **Last Updated**: May 2, 2025
> **Auto-maintained by**: `/update-codebase-summary` skill

## Quick Navigation

- [Tech Stack](#tech-stack)
- [Folder Structure](#folder-structure)
- [Core Infrastructure](#core-infrastructure)
- [Database Models](#database-models)
- [Business Logic Services](#business-logic-services)
- [API Routes](#api-routes)
- [Key Workflows](#key-workflows)
- [Architecture Patterns](#architecture-patterns)

---

## Tech Stack

- **Framework**: Python 3.10+ with FastAPI 0.109.2
- **Database**: PostgreSQL via SQLAlchemy 2.0.27
- **Authentication**: JWT tokens (PyJWT 2.8.0) + Google OAuth
- **Payment**: Razorpay 1.4.2 integration
- **Storage**: Cloudflare R2 (S3-compatible via boto3)
- **Image Processing**: Pillow 10.2.0
- **Rate Limiting**: SlowAPI 0.1.9
- **Background Jobs**: APScheduler 3.10.4
- **Deployment**: Railway with Docker

---

## Folder Structure

```
glycogrit-backend/
├── app/
│   ├── api/              # FastAPI route handlers
│   ├── core/             # Core utilities (auth, config, database)
│   ├── models/           # SQLAlchemy ORM models
│   ├── repositories/     # Data access layer
│   ├── schemas/          # Pydantic validation schemas
│   ├── services/         # Business logic layer
│   └── middleware/       # Request/response middleware
├── alembic/              # Database migrations
├── tests/                # Unit, integration, e2e tests
└── main.py               # Application entry point
```

---

## Core Infrastructure

**[app/core/](app/core/)**:
- **auth.py** - JWT token creation/verification, password hashing, authentication dependencies
- **config.py** - Pydantic Settings for environment configuration (DB, OAuth, Razorpay, R2)
- **database.py** - SQLAlchemy engine, session factory, database connection management
- **exceptions.py** - Custom exception classes for API error handling
- **permissions.py** - Authorization logic for admin and organizer role checks
- **rate_limit.py** - SlowAPI rate limiting configuration for endpoints
- **health.py** - Health check implementation (simple + detailed modes)
- **database_monitor.py** - Database monitoring utilities

---

## Database Models

**[app/models/](app/models/)**:
- **user.py** - User authentication, profile, OAuth support (email/phone flexible identifiers)
- **event.py** - Event entity with activities, tiers, dates, location, capacity tracking
- **registration.py** - Event registrations with tier support, payment tracking, status management
- **event_registration_tier.py** - Tier definitions (Bronze/Silver/Gold) with pricing, rewards, capacity
- **registration_tier.py** - User tier history tracking with upgrade relationships
- **payment.py** - Payment transactions with Razorpay integration, refund support
- **activity_progress.py** - User progress tracking with proof verification, Strava sync
- **strava_connection.py** - Strava OAuth tokens and connection status
- **fitness_tracker.py** - Fitness tracker connections (Apple Health, Google Fit, etc.)
- **user_activity_log.py** - Activity history logs
- **user_goodie.py** - Rewards/goodies earned by users with verification status

---

## Business Logic Services

**[app/services/](app/services/)**:
- **registration_service.py** (40KB) - Event registration logic, tier-based registration, tier upgrades with payment atomicity
- **payment_service.py** - Payment order creation via Razorpay, signature verification, refund processing
- **event_service.py** - Event CRUD operations, filters, organizer authorization
- **user_service.py** - User management, OAuth authentication, profile updates, identifier management
- **tier_service.py** - Tier CRUD operations, capacity validation, registration count management
- **activity_service.py** - Activity tracking, progress updates, proof verification
- **storage_service.py** - Cloudflare R2 file uploads with image optimization (WebP conversion, resizing)
- **activity_sync_service.py** - Strava activity synchronization and progress updates
- **fitness_tracker_service.py** - Fitness tracker integration services
- **challenge_evaluation_service.py** - Challenge completion evaluation
- **challenge_scheduler.py** - Scheduled challenge evaluation tasks
- **scheduler.py** - APScheduler setup for background jobs
- **shiprocket_service.py** - Shipping integration service

**[app/services/payment_gateway/](app/services/payment_gateway/)**:
- **base.py** - Abstract payment gateway interface
- **factory.py** - Payment gateway factory pattern
- **razorpay_gateway.py** - Razorpay implementation

**[app/services/fitness_trackers/](app/services/fitness_trackers/)**:
- **base.py** - Abstract fitness tracker interface
- **factory.py** - Fitness tracker factory pattern
- **apple_health.py** - Apple Health integration
- **google_fit.py** - Google Fit integration
- **nike_run_club.py** - Nike Run Club integration

---

## API Routes

**[app/api/](app/api/)**:
- **auth.py** - Authentication endpoints (login, register, Google OAuth, profile management)
- **events.py** - Event CRUD, activity management, registration endpoints
- **registrations.py** - Tier-based registration, tier upgrades, registration history
- **payments.py** - Payment order creation, verification, refund endpoints
- **event_tiers.py** - Tier management for events (admin operations)
- **webhooks.py** - Payment gateway webhook handlers (Razorpay)
- **strava.py** - Strava OAuth flow and activity sync endpoints
- **challenges.py** - Challenge-specific endpoints
- **activities.py** - Activity tracking endpoints
- **activity_progress.py** - Progress tracking endpoints
- **fitness_trackers.py** - Fitness tracker integration endpoints
- **goodies.py** - Rewards/goodies management endpoints
- **progress.py** - User progress endpoints

---

## Data Access Layer

**[app/repositories/](app/repositories/)**:
- **base.py** - Base repository with common CRUD operations pattern
- **event_repository.py** - Event data access with filters and queries
- **registration_repository.py** - Registration queries and status updates
- **user_repository.py** - User data access and authentication queries
- **payment_repository.py** - Payment transaction queries and updates
- **activity_repository.py** - Activity data access

---

## Validation Schemas

**[app/schemas/](app/schemas/)**:
- **auth.py** - Login, register, token request/response schemas
- **user.py** - User profile schemas with validation
- **event.py** - Event creation/update schemas with activity definitions
- **registration.py** - Registration request/response schemas
- **payment.py** - Payment order and verification schemas
- **tier.py** - Tier definition schemas with pricing and rewards
- **activity.py** - Activity schemas
- **activity_progress.py** - Progress tracking schemas
- **goodie.py** - Goodie/reward schemas

---

## Key Workflows

### Event Registration Flow (Tier-Based)

1. **Request**: Frontend calls `POST /api/v1/registrations/events/{event_id}/tiers/{tier_id}`
2. **Validation**: [registration_service.py](app/services/registration_service.py) validates event, tier, and user eligibility
3. **Payment Order**: If paid tier, [payment_service.py](app/services/payment_service.py) creates Razorpay order BEFORE committing registration
4. **Registration**: Creates registration record with "pending" status (paid) or "confirmed" (free)
5. **Progress**: Creates ActivityProgress record automatically
6. **Verification**: Frontend verifies payment via `POST /api/v1/payments/verify`
7. **Confirmation**: Updates registration to "confirmed", increments tier and event counts

### Tier Upgrade Flow

1. **Request**: Frontend calls `POST /api/v1/registrations/{registration_id}/upgrade-tier`
2. **Validation**: Validates tier hierarchy (must upgrade to higher tier)
3. **Payment**: Calculates upgrade price, creates payment order if needed
4. **Update**: Updates tier counts, creates registration_tier entry
5. **Confirmation**: After payment verified, updates current_tier_id, rewards are additive

### Activity Tracking Flow

1. **Proof Upload**: User uploads via `POST /api/v1/activity-progress/{progress_id}/upload-proof`
2. **Storage**: [storage_service.py](app/services/storage_service.py) optimizes image and uploads to R2
3. **Strava Sync**: [activity_sync_service.py](app/services/activity_sync_service.py) fetches and matches activities
4. **Progress Update**: Updates distance_completed, calculates progress_percentage
5. **Completion**: Marks is_completed when distance_completed >= target_distance

---

## Architecture Patterns

### Repository Pattern
- Repositories handle database queries
- Services contain business logic
- API routes are thin orchestration layers
- Clear separation of concerns

### Service Layer
- Encapsulates business logic
- Receives DB session via dependency injection
- Calls repositories for data access
- Handles complex operations atomically

### Payment Gateway Abstraction
- BasePaymentGateway abstract class
- Factory pattern for gateway creation
- Easy to add new gateways (Stripe, PayPal, etc.)
- Gateway-agnostic payment records

### Schema Validation
- Pydantic schemas for request/response
- Input validation at API boundary
- Type safety throughout application
- Automatic OpenAPI documentation

---

## Common Operations

### Adding a New API Endpoint

1. Define Pydantic schema in [app/schemas/](app/schemas/)
2. Create service method in [app/services/](app/services/)
3. Add repository method if needed in [app/repositories/](app/repositories/)
4. Create API route in [app/api/](app/api/)
5. Register router in [main.py](main.py)

### Database Schema Changes

1. Modify SQLAlchemy models in [app/models/](app/models/)
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration in [alembic/versions/](alembic/versions/)
4. Apply migration: `alembic upgrade head`

### Running Tests

```bash
# Run all tests
doppler run -- pytest

# Run with coverage
doppler run -- pytest --cov=app

# Run specific test file
doppler run -- pytest tests/unit/test_payment_service.py
```

---

**Note**: This summary is auto-maintained. Run `/update-codebase-summary` after significant code changes to keep it synchronized.
