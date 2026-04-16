from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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

# Create database engine with detailed logging
logger.info("")
logger.info("Creating SQLAlchemy engine...")
logger.info(f"  pool_pre_ping: True (test connections before use)")
logger.info(f"  pool_size: 5")
logger.info(f"  max_overflow: 10")

try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,  # Set to True for SQL query logging
        connect_args={
            "connect_timeout": 10,
        }
    )
    logger.info("✅ SQLAlchemy engine created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create engine: {e}")
    raise

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
    """Dependency to get database session"""
    logger.info("📝 Creating new database session...")
    try:
        db = SessionLocal()
        logger.info("✅ Database session created")
        yield db
    except Exception as e:
        logger.error(f"❌ Failed to create database session: {e}")
        raise
    finally:
        logger.info("🔒 Closing database session")
        db.close()
