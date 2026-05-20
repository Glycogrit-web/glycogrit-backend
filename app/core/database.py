from sqlalchemy import create_engine, event, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import Pool
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Database configuration will be logged during startup in main.py


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((exc.OperationalError, exc.DBAPIError)),
    reraise=True
)
def create_db_engine():
    """
    Create database engine with retry logic.

    Retry strategy:
    - Max 3 attempts
    - Exponential backoff: 2s, 4s, 8s (capped at 10s)
    - Only retry on connection errors (OperationalError, DBAPIError)

    Raises:
        Exception: If all retry attempts fail
    """
    # Check if using SQLite (for testing)
    if settings.DATABASE_URL.startswith('sqlite'):
        logger.debug("Detected SQLite database - using simplified engine config")
        from sqlalchemy.pool import StaticPool
        return create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

    # PostgreSQL configuration with connection pooling
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,       # Verify connections are alive before using
        pool_size=10,              # Maintain 10 connections in the pool
        max_overflow=20,           # Allow up to 20 additional connections
        pool_recycle=3600,         # Recycle connections after 1 hour
        echo=False,                # Set to True for SQL query logging
        connect_args={
            "connect_timeout": 10,  # Connection timeout in seconds
        }
    )


# Create engine with retry logic
try:
    engine = create_db_engine()
    logger.debug("SQLAlchemy engine created")
except Exception as e:
    logger.error(f"❌ Failed to create engine after retries: {e}")
    logger.error(f"   Error type: {type(e).__name__}")
    raise


# Add connection pool event listeners for better observability
@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when a new connection is established"""
    logger.debug("🔌 New database connection established")


@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool"""
    logger.debug("📤 Connection checked out from pool")


@event.listens_for(Pool, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log when a connection is returned to the pool"""
    logger.debug("📥 Connection returned to pool")


@event.listens_for(Pool, "close")
def receive_close(dbapi_conn, connection_record):
    """Log when a connection is closed"""
    logger.debug("🔒 Database connection closed")


@event.listens_for(Pool, "detach")
def receive_detach(dbapi_conn, connection_record):
    """Log when a connection is detached from the pool"""
    logger.debug("🔓 Connection detached from pool")


@event.listens_for(Pool, "invalidate")
def receive_invalidate(dbapi_conn, connection_record, exception):
    """Log when a connection is invalidated due to an error"""
    logger.warning(f"⚠️  Connection invalidated: {exception}")


# Create session factory
try:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.debug("Session factory created")
except Exception as e:
    logger.error(f"❌ Failed to create session factory: {e}")
    raise

# Create base class for models
Base = declarative_base()
logger.debug("Declarative base created")


def get_db():
    """
    Dependency to get database session.

    This is a FastAPI dependency that provides a database session
    for each request. The session is automatically closed after the
    request is completed.

    Yields:
        Session: SQLAlchemy database session
    """
    logger.debug("📝 Creating new database session...")
    db = SessionLocal()
    try:
        logger.debug("✅ Database session created")
        yield db
    except Exception as e:
        logger.error(f"❌ Database session error: {e}")
        db.rollback()
        raise
    finally:
        logger.debug("🔒 Closing database session")
        db.close()
