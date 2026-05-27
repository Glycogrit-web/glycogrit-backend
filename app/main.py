import logging
import os
from typing import Any

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import engine, get_db
from app.core.exceptions import AppException
from app.core.health import HealthCheck, HealthStatus
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.middleware import RequestIDMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.modules.activities.api import activities_router, progress_router
from app.modules.certificates.api.certificates import router as certificates_router

# Engagement modules
from app.modules.challenges.api.challenges import router as challenges_router

# Event & Registration modules
from app.modules.events.api.events import router as events_router
from app.modules.events.api.events import activities_router

# Integration modules
from app.modules.fitness_trackers.api.fitness_trackers import router as fitness_trackers_router
from app.modules.gallery.api.gallery import router as gallery_router

# Supporting modules
from app.modules.payments.api.routes import router as payments_router
from app.modules.registrations.api.registrations import router as registrations_router
from app.modules.rewards.api.rewards import router as rewards_router

# ============================================================================
# DDD MODULE IMPORTS (New Architecture) - All Old Imports Removed
# ============================================================================
# Core modules
from app.modules.users.api import auth_router, users_router
from app.modules.webhooks.api.webhooks import router as webhooks_router

# Configure logging with sensitive data filtering
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Apply sensitive data filters to all handlers (GDPR/PCI-DSS compliance)
from app.core.logging_filters import SensitiveDataFilter, StructuredDataFilter

for handler in logging.root.handlers:
    handler.addFilter(SensitiveDataFilter(enable_filtering=settings.ENVIRONMENT != "development"))
    handler.addFilter(StructuredDataFilter())

app = FastAPI(
    title="GlycoGrit Backend API",
    description="Backend API for GlycoGrit cycling community platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiting state to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add Security Headers middleware (should be first)
app.add_middleware(SecurityHeadersMiddleware)

# Add Request ID middleware (must be added before CORS)
app.add_middleware(RequestIDMiddleware)

# CORS configuration
# SECURITY: Wildcard origins are disabled in production
allowed_origins = settings.allowed_origins_list

# Validate CORS configuration
if allowed_origins == ["*"]:
    if settings.ENVIRONMENT == "production":
        logger.error("⚠️  SECURITY VIOLATION: Wildcard CORS not allowed in production!")
        logger.error("⚠️  Set ALLOWED_ORIGINS environment variable to explicit origins")
        raise ValueError("Wildcard CORS origins not allowed in production environment")
    else:
        logger.warning("⚠️  WARNING: Using wildcard CORS origins in development")
        logger.warning("⚠️  This should NEVER be used in production!")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # Can't use credentials with wildcard
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )


# Global exception handler for custom exceptions
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle all custom application exceptions and return appropriate JSON responses."""
    # Get request ID from request state (set by RequestIDMiddleware)
    request_id = getattr(request.state, "request_id", None)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "status_code": exc.status_code,
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id} if request_id else {},
    )


# ============================================================================
# REGISTER ALL DDD MODULE ROUTERS
# ============================================================================
# All old API routers have been removed. Only DDD architecture routers below.

# Core - Authentication & Users
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])

# Core - Activities & Progress
app.include_router(activities_router, prefix="/api/v1", tags=["activities"])
app.include_router(progress_router, prefix="/api/v1", tags=["progress"])

# Events & Registrations
app.include_router(events_router, prefix="/api/v1", tags=["events"])
app.include_router(activities_router, prefix="/api/v1", tags=["activities"])
app.include_router(registrations_router, prefix="/api/v1", tags=["registrations"])

# Engagement - Challenges, Rewards, Certificates
app.include_router(challenges_router, prefix="/api/v1", tags=["challenges"])
app.include_router(rewards_router, prefix="/api/v1", tags=["rewards"])
app.include_router(
    rewards_router, prefix="/api", tags=["rewards"]
)  # Legacy route for frontend compatibility
app.include_router(certificates_router, prefix="/api/v1", tags=["certificates"])

# Integrations - Fitness Trackers
app.include_router(fitness_trackers_router, prefix="/api/v1", tags=["fitness-trackers"])

# Supporting - Payments, Webhooks, Gallery
app.include_router(payments_router, prefix="/api/v1", tags=["payments"])
app.include_router(webhooks_router, prefix="/api/v1", tags=["webhooks"])
app.include_router(gallery_router, prefix="/api/v1", tags=["gallery"])


@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    print("\n" + "=" * 80)
    print("🚀  GLYCOGRIT BACKEND API - STARTING UP")
    print("=" * 80)

    # Section 1: Environment Configuration
    print("\n📋 ENVIRONMENT CONFIGURATION")
    print("-" * 80)
    print(f"   Environment     : {settings.ENVIRONMENT.upper()}")
    print(f"   Server          : {settings.HOST}:{settings.PORT}")
    print(f"   API Docs        : http://{settings.HOST}:{settings.PORT}/docs")

    # Section 2: CORS Configuration
    print("\n🌐 CORS CONFIGURATION")
    print("-" * 80)
    origins = settings.allowed_origins_list
    if origins == ["*"]:
        print("   Status          : ⚠️  WILDCARD (ALL ORIGINS - DEVELOPMENT ONLY)")
    else:
        print("   Status          : ✅ ENABLED")
        print(f"   Allowed Origins : {len(origins)} domain(s)")
        for i, origin in enumerate(origins):
            prefix = "   └─" if i == len(origins) - 1 else "   ├─"
            print(f"{prefix} {origin}")

    # Section 3: Database Configuration
    print("\n💾 DATABASE CONFIGURATION")
    print("-" * 80)
    db_url = settings.DATABASE_URL
    if "@" in db_url:
        try:
            protocol = db_url.split("://")[0]
            rest = db_url.split("://")[1]
            user_part = rest.split("@")[0].split(":")[0]
            host_part = rest.split("@")[1]
            hostname = host_part.split(":")[0] if ":" in host_part else host_part.split("/")[0]

            print(f"   Database Type   : {protocol.upper()}")
            print(f"   User            : {user_part}")
            print(f"   Host            : {hostname}")

            # Connection pool settings
            print("   Pool Size       : 10 connections")
            print("   Max Overflow    : 20 connections")
            print("   Pool Recycle    : 3600s (1 hour)")

            # Check hostname type
            if "railway.internal" in hostname:
                print("   Network         : ✅ Internal Railway network")
            elif "proxy.rlwy.net" in hostname or "railway.app" in hostname:
                print("   Network         : ⚠️  External proxy (may have latency)")
            else:
                print("   Network         : Custom/Local")
        except Exception as e:
            print(f"   ⚠️  Could not parse DATABASE_URL: {e}")
    else:
        print("   ⚠️  DATABASE_URL format unexpected")

    # Section 4: Database Connection Test
    print("\n🔍 DATABASE CONNECTION TEST")
    print("-" * 80)
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("   Status          : ✅ CONNECTED")
                print("   Test Query      : SELECT 1 → SUCCESS")
            else:
                print("   Status          : ⚠️  CONNECTED (unexpected result)")
    except Exception as e:
        print("   Status          : ❌ CONNECTION FAILED")
        print(f"   Error Type      : {type(e).__name__}")
        print(f"   Error Message   : {str(e)}")

        # Only show traceback in development
        if settings.ENVIRONMENT == "development":
            import traceback

            print("\n   Traceback:")
            print("   " + "\n   ".join(traceback.format_exc().split("\n")))

    # Section 5: Background Services
    print("\n⚙️  BACKGROUND SERVICES")
    print("-" * 80)
    try:
        import asyncio

        from app.modules.fitness_trackers.services.background_sync_service import run_periodic_sync

        asyncio.create_task(run_periodic_sync())
        print("   Fitness Sync    : ✅ STARTED")
    except Exception as e:
        print(f"   Fitness Sync    : ❌ FAILED ({str(e)})")

    # Section 6: Security & Features
    print("\n🔒 SECURITY & FEATURES")
    print("-" * 80)
    print("   Rate Limiting   : ✅ ENABLED (SlowAPI)")
    print("   Security Headers: ✅ ENABLED (CSP, HSTS, X-Frame-Options)")
    print("   Request Tracking: ✅ ENABLED (X-Request-ID)")
    print("   Data Filtering  : ✅ ENABLED (PII/Sensitive data masking)")

    # Show API documentation availability
    if settings.ENVIRONMENT == "production":
        print("   API Docs        : ⚠️  PUBLIC (consider restricting in production)")
    else:
        print("   API Docs        : ✅ AVAILABLE (/docs, /redoc)")

    # Final Status
    print("\n" + "=" * 80)
    print("✅  STARTUP COMPLETE - SERVER READY TO ACCEPT CONNECTIONS")
    print("=" * 80 + "\n")


@app.get("/", tags=["root"])
@limiter.limit("100/minute")
async def root(request: Request, response: Response) -> dict[str, str]:
    """
    Root endpoint providing API information.

    Returns basic API metadata including version and environment.

    Args:
        request: FastAPI Request object (required for rate limiting)
        response: FastAPI Response object (required for rate limit headers)

    Returns:
        Dict containing API metadata

    Rate Limit:
        100 requests per minute per client
    """
    return {
        "message": "GlycoGrit Backend API",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["health"])
@limiter.limit("200/minute")
async def health_check(
    request: Request, response: Response, detailed: bool = False
) -> dict[str, Any]:
    """
    Health check endpoint for monitoring and load balancers.

    Supports both simple and detailed health checks:
    - Simple (default): Fast check with basic status (for load balancers)
    - Detailed (?detailed=true): Comprehensive check with database, resources, uptime

    Args:
        request: FastAPI Request object (required for rate limiting)
        response: FastAPI Response object (required for rate limit headers)
        detailed: Whether to include detailed health metrics (default: False)

    Returns:
        Dict containing health status and metrics

    Rate Limit:
        200 requests per minute (lenient for health checks)

    Examples:
        Simple: GET /health
        Detailed: GET /health?detailed=true
    """
    if not detailed:
        # Simple check for load balancers - fast, no DB connection
        result = HealthCheck.simple_health_check()
        result.update(
            {
                "application": "GlycoGrit Backend API",
                "version": "1.0.0",
                "environment": settings.ENVIRONMENT,
            }
        )
        return result

    # Detailed health check with all components
    logger.info("Performing detailed health check...")
    result = HealthCheck.full_health_check(db=next(get_db()), engine=engine, include_resources=True)

    # Add application metadata
    result["application"] = {
        "name": "GlycoGrit Backend API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "port": settings.PORT,
    }

    # Set appropriate HTTP status code based on health
    if result["status"] == HealthStatus.UNHEALTHY:
        response.status_code = 503  # Service Unavailable
    elif result["status"] == HealthStatus.DEGRADED:
        response.status_code = 200  # Still accessible but with warnings

    return result


@app.get("/api/v1/test", tags=["testing"])
@limiter.limit("50/minute")
async def test_endpoint(request: Request, response: Response) -> dict[str, str]:
    """
    Simple test endpoint to verify API is working.

    Args:
        request: FastAPI Request object (required for rate limiting)
        response: FastAPI Response object (required for rate limit headers)

    Returns:
        Dict with test message and environment info

    Rate Limit:
        50 requests per minute per client
    """
    return {
        "message": "API is working!",
        "environment": settings.ENVIRONMENT,
        "railway_env": os.getenv("RAILWAY_ENVIRONMENT", "not set"),
    }


@app.get("/api/v1/users/me", tags=["testing"])
@limiter.limit("30/minute")
async def get_current_user(request: Request, response: Response) -> dict[str, Any]:
    """
    Mock user endpoint for testing.

    Note: This is a temporary endpoint for testing purposes.

    Args:
        request: FastAPI Request object (required for rate limiting)
        response: FastAPI Response object (required for rate limit headers)

    Returns:
        Dict with mock user data

    Rate Limit:
        30 requests per minute per client
    """
    return {
        "id": 1,
        "email": "test@example.com",
        "name": "Test User",
        "message": "This is a test endpoint",
    }


@app.get("/api/v1/db-test", tags=["health"])
@limiter.limit("10/minute")
async def test_database(
    request: Request, response: Response, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Test database connection endpoint.

    Executes a simple query to verify database connectivity.

    Args:
        request: FastAPI Request object (required for rate limiting)
        response: FastAPI Response object (required for rate limit headers)
        db: Database session dependency

    Returns:
        Dict with database connection test results

    Rate Limit:
        10 requests per minute (strict due to database query)
    """
    logger.info("🔍 /api/v1/db-test endpoint called")
    logger.info("DATABASE_URL environment variables:")
    logger.info(f"  - DATABASE_URL: {'SET' if os.getenv('DATABASE_URL') else 'NOT SET'}")
    logger.info(
        f"  - DATABASE_PRIVATE_URL: {'SET' if os.getenv('DATABASE_PRIVATE_URL') else 'NOT SET'}"
    )

    try:
        logger.info("Attempting to execute test query...")
        # Execute a simple query to test connection
        result = db.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        logger.info(f"✅ Query executed successfully, result: {row[0] if row else None}")

        response = {
            "status": "success",
            "message": "Database connection successful",
            "test_query_result": row[0] if row else None,
            "database_url": (
                settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "local"
            ),
            "env_vars": {
                "DATABASE_URL": "SET" if os.getenv("DATABASE_URL") else "NOT SET",
                "DATABASE_PRIVATE_URL": "SET" if os.getenv("DATABASE_PRIVATE_URL") else "NOT SET",
            },
        }
        logger.info(f"Response: {response}")
        return response
    except Exception as e:
        logger.error("❌ Database connection failed!")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Using DATABASE_URL: {settings.DATABASE_URL[:50]}...")
        return {
            "status": "error",
            "message": f"Database connection failed: {str(e)}",
            "error_type": type(e).__name__,
        }


@app.get("/api/v1/razorpay-config-test", tags=["testing"])
@limiter.limit("10/minute")
async def test_razorpay_config(request: Request, response: Response) -> dict[str, Any]:
    """
    Test Razorpay configuration endpoint.

    Shows if Razorpay credentials are loaded (safely masked).

    Args:
        request: FastAPI Request object (required for rate limiting)
        response: FastAPI Response object (required for rate limit headers)

    Returns:
        Dict with Razorpay configuration status

    Rate Limit:
        10 requests per minute
    """
    logger.info("🔍 /api/v1/razorpay-config-test endpoint called")

    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    # Safely mask the values
    def mask_key(key: str) -> str:
        if not key:
            return "NOT SET"
        if len(key) <= 8:
            return f"{key[:2]}***{key[-2:]}"
        return f"{key[:8]}...{key[-4:]}"

    config_status = {
        "status": "success",
        "razorpay_config": {
            "RAZORPAY_KEY_ID": {
                "is_set": bool(key_id),
                "value_preview": mask_key(key_id) if key_id else "NOT SET",
                "starts_with_rzp_live": key_id.startswith("rzp_live_") if key_id else False,
                "starts_with_rzp_test": key_id.startswith("rzp_test_") if key_id else False,
                "length": len(key_id) if key_id else 0,
            },
            "RAZORPAY_KEY_SECRET": {
                "is_set": bool(key_secret),
                "value_preview": mask_key(key_secret) if key_secret else "NOT SET",
                "length": len(key_secret) if key_secret else 0,
            },
            "RAZORPAY_WEBHOOK_SECRET": {
                "is_set": bool(webhook_secret),
                "value_preview": mask_key(webhook_secret) if webhook_secret else "NOT SET",
                "length": len(webhook_secret) if webhook_secret else 0,
            },
            "DEFAULT_PAYMENT_GATEWAY": settings.DEFAULT_PAYMENT_GATEWAY,
        },
        "environment": settings.ENVIRONMENT,
        "all_env_vars": {
            "RAZORPAY_KEY_ID": "SET" if os.getenv("RAZORPAY_KEY_ID") else "NOT SET",
            "RAZORPAY_KEY_SECRET": "SET" if os.getenv("RAZORPAY_KEY_SECRET") else "NOT SET",
            "RAZORPAY_WEBHOOK_SECRET": "SET" if os.getenv("RAZORPAY_WEBHOOK_SECRET") else "NOT SET",
        },
    }

    logger.info(
        f"Razorpay Key ID: {config_status['razorpay_config']['RAZORPAY_KEY_ID']['value_preview']}"
    )
    logger.info(
        f"Is Live Key: {config_status['razorpay_config']['RAZORPAY_KEY_ID']['starts_with_rzp_live']}"
    )
    logger.info(
        f"Is Test Key: {config_status['razorpay_config']['RAZORPAY_KEY_ID']['starts_with_rzp_test']}"
    )

    return config_status


# Temporary admin endpoints removed - use manage_db.py CLI for database operations
