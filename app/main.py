from typing import Dict, Any, Optional
from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.database import get_db, engine
from app.core.exceptions import AppException
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.core.health import HealthCheck, HealthStatus
from app.middleware import RequestIDMiddleware
from app.api import auth, events, activities, registrations, payments, strava, challenges, fitness_trackers, goodies, event_tiers, activity_progress
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# Add Request ID middleware (must be added before CORS)
app.add_middleware(RequestIDMiddleware)

# CORS configuration
# Note: Cannot use allow_origins=["*"] with allow_credentials=True
# Must specify explicit origins from Doppler/environment
allowed_origins = settings.allowed_origins_list
# If wildcard is set, use it (but note: can't use credentials with *)
if allowed_origins == ["*"]:
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
            "request_id": request_id
        },
        headers={"X-Request-ID": request_id} if request_id else {}
    )

# Register API routers
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(event_tiers.router)
app.include_router(activities.router)
app.include_router(activity_progress.router)
app.include_router(registrations.router)
app.include_router(payments.router)
app.include_router(strava.router)
app.include_router(challenges.router)
app.include_router(fitness_trackers.router)
app.include_router(goodies.router)

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("=" * 50)
    logger.info("🚀 GlycoGrit Backend Starting Up")
    logger.info("=" * 50)
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Port: {settings.PORT}")
    logger.info(f"Host: {settings.HOST}")
    logger.info(f"ALLOWED_ORIGINS: {settings.ALLOWED_ORIGINS}")

    # Log database configuration (hide password)
    db_url = settings.DATABASE_URL
    if "@" in db_url:
        # Extract and log hostname without password
        try:
            parts = db_url.split("@")
            host_part = parts[1] if len(parts) > 1 else "unknown"
            user_part = parts[0].split("://")[1].split(":")[0] if "://" in parts[0] else "unknown"
            logger.info(f"Database User: {user_part}")
            logger.info(f"Database Host: {host_part}")
        except Exception as e:
            logger.warning(f"Could not parse DATABASE_URL: {e}")
    else:
        logger.warning("DATABASE_URL format unexpected")

    # Test database connection on startup
    logger.info("")
    logger.info("🔍 Testing database connection at startup...")
    try:
        logger.info("  Step 1: Creating connection...")
        with engine.connect() as connection:
            logger.info("  ✅ Connection established")
            logger.info("  Step 2: Executing test query (SELECT 1)...")
            result = connection.execute(text("SELECT 1"))
            logger.info("  ✅ Query executed")
            logger.info("  Step 3: Fetching result...")
            row = result.fetchone()
            logger.info(f"  ✅ Result fetched: {row}")
            logger.info("")
            logger.info("✅✅✅ DATABASE CONNECTION SUCCESSFUL! ✅✅✅")
    except Exception as e:
        logger.error("")
        logger.error("❌❌❌ DATABASE CONNECTION FAILED! ❌❌❌")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Full error: {repr(e)}")

        # Try to get more details
        import traceback
        logger.error("Traceback:")
        logger.error(traceback.format_exc())

    logger.info("=" * 50)
    logger.info("✅ Startup Complete")
    logger.info("=" * 50)


@app.get("/", tags=["root"])
@limiter.limit("100/minute")
async def root(request: Request, response: Response) -> Dict[str, str]:
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
        "environment": settings.ENVIRONMENT
    }


@app.get("/health", tags=["health"])
@limiter.limit("200/minute")
async def health_check(
    request: Request,
    response: Response,
    detailed: bool = False
) -> Dict[str, Any]:
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
        result.update({
            "application": "GlycoGrit Backend API",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT
        })
        return result

    # Detailed health check with all components
    logger.info("Performing detailed health check...")
    result = HealthCheck.full_health_check(
        db=next(get_db()),
        engine=engine,
        include_resources=True
    )

    # Add application metadata
    result["application"] = {
        "name": "GlycoGrit Backend API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "port": settings.PORT
    }

    # Set appropriate HTTP status code based on health
    if result["status"] == HealthStatus.UNHEALTHY:
        response.status_code = 503  # Service Unavailable
    elif result["status"] == HealthStatus.DEGRADED:
        response.status_code = 200  # Still accessible but with warnings

    return result


@app.get("/api/v1/test", tags=["testing"])
@limiter.limit("50/minute")
async def test_endpoint(request: Request, response: Response) -> Dict[str, str]:
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
        "railway_env": os.getenv("RAILWAY_ENVIRONMENT", "not set")
    }


@app.get("/api/v1/users/me", tags=["testing"])
@limiter.limit("30/minute")
async def get_current_user(request: Request, response: Response) -> Dict[str, Any]:
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
        "message": "This is a test endpoint"
    }


@app.get("/api/v1/db-test", tags=["health"])
@limiter.limit("10/minute")
async def test_database(request: Request, response: Response, db: Session = Depends(get_db)) -> Dict[str, Any]:
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
    logger.info(f"DATABASE_URL environment variables:")
    logger.info(f"  - DATABASE_URL: {'SET' if os.getenv('DATABASE_URL') else 'NOT SET'}")
    logger.info(f"  - DATABASE_PRIVATE_URL: {'SET' if os.getenv('DATABASE_PRIVATE_URL') else 'NOT SET'}")

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
            "database_url": settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "local",
            "env_vars": {
                "DATABASE_URL": "SET" if os.getenv('DATABASE_URL') else "NOT SET",
                "DATABASE_PRIVATE_URL": "SET" if os.getenv('DATABASE_PRIVATE_URL') else "NOT SET"
            }
        }
        logger.info(f"Response: {response}")
        return response
    except Exception as e:
        logger.error(f"❌ Database connection failed!")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Using DATABASE_URL: {settings.DATABASE_URL[:50]}...")
        return {
            "status": "error",
            "message": f"Database connection failed: {str(e)}",
            "error_type": type(e).__name__
        }


# Temporary admin endpoints removed - use manage_db.py CLI for database operations
