"""
Pytest configuration and shared fixtures for all tests.

IMPORTANT: This file patches JSONB before importing models to ensure SQLite compatibility.
"""
import pytest
import os
from typing import Generator

# CRITICAL: Set test database URL BEFORE any imports
# This prevents the app from trying to connect to PostgreSQL during import
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "testing"

# CRITICAL: Patch JSONB BEFORE importing any models
# SQLite doesn't support PostgreSQL's JSONB type, so we replace it with JSON
from sqlalchemy import JSON
from sqlalchemy.dialects import postgresql

# Store original JSONB
_original_JSONB = postgresql.JSONB

# Create a new JSONB class that uses JSON as implementation
class JSONB(JSON):
    """JSONB that works with both PostgreSQL and SQLite."""
    __visit_name__ = 'JSON'  # Use JSON visitor for SQLite

# Replace JSONB in the postgresql dialect module
postgresql.JSONB = JSONB

# Now safe to import everything else
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.models.event import Event
from app.models.event_registration_tier import EventRegistrationTier
from app.models.registration import Registration
from app.models.payment import Payment
from decimal import Decimal


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Create a fresh database for each test.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> TestClient:
    """
    Create a test client with database dependency override.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_client(db: Session, test_user: User) -> TestClient:
    """
    Create an authenticated test client for integration tests.
    Overrides both database and authentication dependencies.
    """
    from app.core.auth import get_current_active_user

    def override_get_db():
        try:
            yield db
        finally:
            pass

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        is_active=True,
        email_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_event(db: Session, test_user: User) -> Event:
    """Create a test event with tier system."""
    from datetime import datetime, timedelta

    now = datetime.now()
    event = Event(
        name="Test Event",
        slug="test-event",
        description="Test Description",
        status="published",
        event_date=now + timedelta(days=30),
        event_end_date=now + timedelta(days=60),
        registration_start_date=now - timedelta(days=7),
        registration_end_date=now + timedelta(days=25),
        location_name="Virtual Event",
        city="Mumbai",
        state="Maharashtra",
        country="India",
        is_virtual=True,
        uses_tier_system=True,
        organizer_id=test_user.id
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture
def test_activities(db: Session, test_event: Event):
    """Create test activities for an event."""
    from app.modules.events.domain.event import EventActivity

    activities = [
        EventActivity(
            event_id=test_event.id,
            name="Running 5K",
            description="5 kilometer run",
            distance=5.0,
            activity_type="running"
        ),
        EventActivity(
            event_id=test_event.id,
            name="Running 10K",
            description="10 kilometer run",
            distance=10.0,
            activity_type="running"
        ),
    ]

    for activity in activities:
        db.add(activity)
    db.commit()

    for activity in activities:
        db.refresh(activity)

    return activities


@pytest.fixture
def test_tiers(db: Session, test_event: Event) -> list[EventRegistrationTier]:
    """Create test tiers for an event."""
    tiers = [
        EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Free Tier",
            tier_slug="free-tier",
            tier_order=0,
            price=Decimal("0.00"),
            currency="INR",
            max_registrations=100,
            requires_payment=False
        ),
        EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Basic Tier",
            tier_slug="basic-tier",
            tier_order=1,
            price=Decimal("500.00"),
            currency="INR",
            max_registrations=50,
            requires_payment=True
        ),
        EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Premium Tier",
            tier_slug="premium-tier",
            tier_order=2,
            price=Decimal("1000.00"),
            currency="INR",
            max_registrations=20,
            requires_payment=True
        ),
    ]

    for tier in tiers:
        db.add(tier)
    db.commit()

    for tier in tiers:
        db.refresh(tier)

    return tiers


@pytest.fixture
def test_registration(db: Session, test_user: User, test_event: Event, test_tiers: list) -> Registration:
    """Create a test registration at free tier."""
    registration = Registration(
        user_id=test_user.id,
        event_id=test_event.id,
        current_tier_id=test_tiers[0].id,  # Free tier
        registration_number=f"EVT{test_event.id}-TEST01",
        participant_name="Test User",
        status="confirmed",
        uses_tier_system=True
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


@pytest.fixture
def mock_razorpay_order():
    """Mock Razorpay order response."""
    return {
        "id": "order_test123",
        "entity": "order",
        "amount": 2000,  # ₹20 in paise
        "currency": "INR",
        "status": "created"
    }


@pytest.fixture
def mock_razorpay_payment():
    """Mock Razorpay payment response."""
    return {
        "id": "pay_test123",
        "entity": "payment",
        "amount": 2000,
        "currency": "INR",
        "status": "captured",
        "order_id": "order_test123",
        "method": "upi"
    }
