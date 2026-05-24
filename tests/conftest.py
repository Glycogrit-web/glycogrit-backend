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
from app.modules.events.domain.event import Event
from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier
from app.modules.registrations.domain.registration import Registration
from app.modules.payments.domain.payment import Payment
from app.modules.fitness_trackers.domain.connection import FitnessConnection
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
    from app.core.auth import get_current_user

    def override_get_db():
        try:
            yield db
        finally:
            pass

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

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


# ============================================================================
# CERTIFICATE SYSTEM FIXTURES
# ============================================================================

@pytest.fixture
def completed_registration(db: Session, test_user: User, test_event: Event, test_tiers: list) -> Registration:
    """Create a completed registration with activity progress."""
    from app.models.activity_progress import ActivityProgress
    from datetime import datetime

    registration = Registration(
        user_id=test_user.id,
        event_id=test_event.id,
        current_tier_id=test_tiers[0].id,
        registration_number=f"EVT{test_event.id}-COMPLETE01",
        participant_name="Completed User",
        status="confirmed",
        uses_tier_system=True
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)

    # Add completed activity progress
    # Get the first activity from test_activities
    from app.modules.events.domain.event import EventActivity
    activity = db.query(EventActivity).filter(EventActivity.event_id == test_event.id).first()

    if activity:
        progress = ActivityProgress(
            registration_id=registration.id,
            user_id=test_user.id,
            event_id=test_event.id,
            activity_id=activity.id,
            target_distance=5.0,
            distance_completed=5.5,
            completed_at=datetime.utcnow()
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)

    return registration


@pytest.fixture
def incomplete_registration(db: Session, test_user: User, test_event: Event, test_tiers: list) -> Registration:
    """Create an incomplete registration (no activity completed)."""
    from app.models.activity_progress import ActivityProgress

    registration = Registration(
        user_id=test_user.id,
        event_id=test_event.id,
        current_tier_id=test_tiers[0].id,
        registration_number=f"EVT{test_event.id}-INCOMPLETE01",
        participant_name="Incomplete User",
        status="confirmed",
        uses_tier_system=True
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)

    # Add incomplete activity progress
    progress = ActivityProgress(
        registration_id=registration.id,
        activity_name="Running 10K",
        target_distance=10.0,
        distance_completed=7.5,
        is_completed=False,
        completed_at=None
    )
    db.add(progress)
    db.commit()

    return registration


@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user."""
    admin = User(
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        is_active=True,
        email_verified=True,
        role="admin"
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def authenticated_admin_client(db: Session, admin_user: User) -> TestClient:
    """Create an authenticated admin client."""
    from app.core.auth import get_current_user

    def override_get_db():
        try:
            yield db
        finally:
            pass

    async def override_get_current_user():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def certificate_reward(db: Session, completed_registration: Registration) -> 'UserReward':
    """Create a certificate reward with download tracking."""
    from app.models.user_reward import UserReward, RewardType, RewardStatus
    from datetime import datetime

    reward = UserReward(
        user_id=completed_registration.user_id,
        event_id=completed_registration.event_id,
        registration_id=completed_registration.id,
        reward_id="certificate-ecert",  # Required field
        reward_type=RewardType.CERTIFICATE,
        reward_name="E-Certificate",
        reward_image_url="https://test.example.com/cert.pdf",
        certificate_url="https://test.example.com/cert.pdf",
        certificate_number="GLCG-2024-0001-00001",
        requires_shipping=False,
        status=RewardStatus.DELIVERED,
        awarded_at=datetime.utcnow(),
        delivered_at=datetime.utcnow(),
        download_count=0,
        download_limit=10,
        last_downloaded_at=None
    )
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward
