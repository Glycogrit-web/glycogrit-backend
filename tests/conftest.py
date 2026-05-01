"""
Pytest configuration and shared fixtures for all tests.
"""
import pytest
import os
from typing import Generator
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


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_event(db: Session) -> Event:
    """Create a test event with tier system."""
    event = Event(
        title="Test Event",
        description="Test Description",
        event_type="virtual",
        start_date="2026-06-01",
        end_date="2026-06-30",
        uses_tier_system=True,
        is_active=True
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture
def test_tiers(db: Session, test_event: Event) -> list[EventRegistrationTier]:
    """Create test tiers for an event."""
    tiers = [
        EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Free Tier",
            tier_order=0,
            price=Decimal("0.00"),
            currency="INR",
            max_registrations=100
        ),
        EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Basic Tier",
            tier_order=1,
            price=Decimal("500.00"),
            currency="INR",
            max_registrations=50
        ),
        EventRegistrationTier(
            event_id=test_event.id,
            tier_name="Premium Tier",
            tier_order=2,
            price=Decimal("1000.00"),
            currency="INR",
            max_registrations=20
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
        participant_name="Test User",
        status="confirmed"
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
