from sqlalchemy import create_engine, event, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import Pool
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Log database configuration
logger.info("=" * 60)
logger.info("📊 INITIALIZING DATABASE CONNECTION")
logger.info("=" * 60)

db_url = settings.DATABASE_URL
logger.info(f"Database URL received: {db_url[:20]}...{db_url[-30:]}")

if "@" in db_url:
    # Parse and log connection details
    try:
        protocol = db_url.split("://")[0]
        rest = db_url.split("://")[1]
        user_part = rest.split("@")[0].split(":")[0]
        host_part = rest.split("@")[1] if len(rest.split("@")) > 1 else "unknown"

        logger.info(f"  Protocol: {protocol}")
        logger.info(f"  User: {user_part}")
        logger.info(f"  Host: {host_part}")

        # Extract just the hostname
        hostname = host_part.split(":")[0] if ":" in host_part else host_part.split("/")[0]
        logger.info(f"  Hostname only: {hostname}")

        # Check if it's internal or external
        if "railway.internal" in hostname:
            logger.info(f"  ✅ Using INTERNAL Railway hostname")
        elif "proxy.rlwy.net" in hostname or "railway.app" in hostname:
            logger.warning(f"  ⚠️  Using EXTERNAL hostname - this may not work for internal services!")
        else:
            logger.info(f"  Using custom/local hostname")

    except Exception as e:
        logger.error(f"  ❌ Error parsing DATABASE_URL: {e}")
else:
    logger.warning(f"  ⚠️  DATABASE_URL format unexpected: {db_url[:50]}")


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
    logger.info("Creating SQLAlchemy engine with retry logic...")

    # Check if using SQLite (for testing)
    if settings.DATABASE_URL.startswith('sqlite'):
        logger.info("Detected SQLite database - using simplified engine config")
        from sqlalchemy.pool import StaticPool
        return create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

    # PostgreSQL configuration with connection pooling
    logger.info(f"  pool_pre_ping: True (test connections before use)")
    logger.info(f"  pool_size: 10")
    logger.info(f"  max_overflow: 20")
    logger.info(f"  pool_recycle: 3600 (recycle connections after 1 hour)")

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
    logger.info("✅ SQLAlchemy engine created successfully")
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
logger.info("")
logger.info("Creating session factory...")
try:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("✅ Session factory created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create session factory: {e}")
    raise

# Create base class for models
logger.info("")
logger.info("Creating declarative base...")
Base = declarative_base()
logger.info("✅ Declarative base created")

logger.info("=" * 60)
logger.info("✅ DATABASE MODULE INITIALIZED")
logger.info("=" * 60)


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
