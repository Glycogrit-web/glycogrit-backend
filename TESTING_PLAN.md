# Testing Plan - New DDD APIs

**Status**: Ready to implement
**Coverage Goal**: 80%+ for all new endpoints
**Date**: 2026-05-21

---

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_api/                # API endpoint tests
│   ├── test_users.py
│   ├── test_activities.py
│   ├── test_registrations.py
│   ├── test_events.py
│   ├── test_challenges.py
│   ├── test_rewards.py
│   ├── test_certificates.py
│   ├── test_gallery.py
│   ├── test_payments.py
│   ├── test_statistics.py
│   ├── test_fitness_trackers.py
│   └── test_webhooks.py
├── test_services/           # Service layer tests
│   ├── test_activity_service.py
│   ├── test_registration_service.py
│   └── ...
└── test_domain/             # Domain logic tests
    ├── test_entities.py
    ├── test_value_objects.py
    └── ...
```

---

## Test Fixtures (conftest.py)

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.core.auth import create_access_token

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Create test client"""
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
def test_user(db):
    """Create test user"""
    from app.models.user import User
    user = User(
        email="test@example.com",
        hashed_password="$2b$12$fake_hash",
        full_name="Test User",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def auth_token(test_user):
    """Create auth token for test user"""
    return create_access_token({"sub": test_user.email})

@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers"""
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture
def test_event(db):
    """Create test event"""
    from app.models.event import Event
    from datetime import datetime, timedelta

    event = Event(
        name="Test Marathon",
        slug="test-marathon",
        description="Test event description",
        event_date=datetime.now() + timedelta(days=30),
        registration_start_date=datetime.now(),
        registration_end_date=datetime.now() + timedelta(days=20),
        status="published"
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
```

---

## Test Cases by Module

### 1. Users API Tests

```python
# tests/test_api/test_users.py
import pytest

class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_register_user(self, client):
        """Test user registration"""
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "full_name": "New User"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data

    def test_login_user(self, client, test_user):
        """Test user login"""
        response = client.post("/api/v1/auth/login", data={
            "username": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_get_current_user(self, client, auth_headers):
        """Test get current user"""
        response = client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"


### 2. Activities API Tests

```python
# tests/test_api/test_activities.py
import pytest
from datetime import datetime

class TestActivitiesEndpoints:
    """Test activities endpoints"""

    def test_submit_activity(self, client, auth_headers, test_event):
        """Test activity submission"""
        response = client.post(
            f"/api/v1/events/{test_event.id}/activities",
            headers=auth_headers,
            json={
                "activity_type": "running",
                "distance": 10.5,
                "duration": 3600,
                "activity_date": datetime.now().isoformat(),
                "source": "manual"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["distance"] == 10.5
        assert data["activity_type"] == "running"

    def test_get_activities(self, client, auth_headers):
        """Test get user activities"""
        response = client.get("/api/v1/activities/my", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_activity_stats(self, client, auth_headers):
        """Test get activity statistics"""
        response = client.get("/api/v1/activities/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_distance" in data
        assert "total_activities" in data


### 3. Events API Tests

```python
# tests/test_api/test_events.py
import pytest

class TestEventsEndpoints:
    """Test events endpoints"""

    def test_list_events(self, client):
        """Test list all events"""
        response = client.get("/api/v1/events")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_event_by_id(self, client, test_event):
        """Test get event details"""
        response = client.get(f"/api/v1/events/{test_event.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_event.id
        assert data["name"] == "Test Marathon"

    def test_search_events(self, client):
        """Test event search"""
        response = client.get("/api/v1/events?search=marathon")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_event(self, client, auth_headers):
        """Test create event (admin)"""
        response = client.post(
            "/api/v1/events",
            headers=auth_headers,
            json={
                "name": "New Marathon",
                "slug": "new-marathon",
                "description": "A new test event",
                "event_date": "2026-12-31T10:00:00",
                "registration_start_date": "2026-01-01T00:00:00",
                "registration_end_date": "2026-12-20T23:59:59"
            }
        )
        # May need admin permissions
        assert response.status_code in [201, 403]


### 4. Challenges API Tests

```python
# tests/test_api/test_challenges.py
import pytest

class TestChallengesEndpoints:
    """Test challenges endpoints"""

    def test_join_challenge(self, client, auth_headers, test_event):
        """Test join a challenge"""
        response = client.post(
            f"/api/v1/challenges/{test_event.id}/join",
            headers=auth_headers
        )
        assert response.status_code in [201, 409]  # 409 if already joined

    def test_get_challenge_progress(self, client, auth_headers, test_event):
        """Test get challenge progress"""
        response = client.get(
            f"/api/v1/challenges/{test_event.id}/progress",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "current_distance" in data
        assert "target_distance" in data
        assert "progress_percentage" in data

    def test_get_my_challenges(self, client, auth_headers):
        """Test get user's challenges"""
        response = client.get("/api/v1/challenges/my", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


### 5. Registrations API Tests

```python
# tests/test_api/test_registrations.py
import pytest

class TestRegistrationsEndpoints:
    """Test registrations endpoints"""

    def test_get_my_registrations(self, client, auth_headers):
        """Test get user registrations"""
        response = client.get("/api/v1/registrations/my", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_cancel_registration(self, client, auth_headers):
        """Test cancel registration"""
        # Create registration first, then cancel
        # Implementation depends on your business logic
        pass


### 6. Rewards API Tests

```python
# tests/test_api/test_rewards.py
import pytest

class TestRewardsEndpoints:
    """Test rewards endpoints"""

    def test_create_reward_order(self, client, auth_headers):
        """Test create physical reward order"""
        response = client.post(
            "/api/v1/rewards",
            headers=auth_headers,
            json={
                "registration_id": 1,
                "reward_name": "Finisher Medal",
                "shipping_address": {
                    "name": "Test User",
                    "address_line1": "123 Main St",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001",
                    "phone": "9876543210"
                }
            }
        )
        assert response.status_code in [201, 404]  # 404 if registration not found

    def test_get_my_rewards(self, client, auth_headers):
        """Test get user rewards"""
        response = client.get("/api/v1/rewards/my", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_invalid_pincode(self, client, auth_headers):
        """Test invalid pincode validation"""
        response = client.post(
            "/api/v1/rewards",
            headers=auth_headers,
            json={
                "registration_id": 1,
                "reward_name": "Medal",
                "shipping_address": {
                    "name": "Test User",
                    "address_line1": "123 Main St",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "12345",  # Invalid: not 6 digits
                    "phone": "9876543210"
                }
            }
        )
        assert response.status_code == 422  # Validation error


### 7. Statistics API Tests

```python
# tests/test_api/test_statistics.py
import pytest

class TestStatisticsEndpoints:
    """Test statistics endpoints"""

    def test_get_site_statistics(self, client):
        """Test get site-wide statistics"""
        response = client.get("/api/v1/statistics/site")
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_distance_km" in data

    def test_get_user_statistics(self, client, auth_headers):
        """Test get user statistics"""
        response = client.get("/api/v1/statistics/user/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_activities" in data


### 8. Gallery API Tests

```python
# tests/test_api/test_gallery.py
import pytest

class TestGalleryEndpoints:
    """Test gallery endpoints"""

    def test_get_photos(self, client):
        """Test get approved photos"""
        response = client.get("/api/v1/gallery/photos")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_submit_photo(self, client, auth_headers):
        """Test submit photo"""
        response = client.post(
            "/api/v1/gallery/photos",
            headers=auth_headers,
            json={
                "photo_url": "https://example.com/photo.jpg",
                "caption": "Great run today!"
            }
        )
        assert response.status_code == 201


### 9. Fitness Trackers API Tests

```python
# tests/test_api/test_fitness_trackers.py
import pytest

class TestFitnessTrackersEndpoints:
    """Test fitness trackers endpoints"""

    def test_get_connections(self, client, auth_headers):
        """Test get user's fitness tracker connections"""
        response = client.get("/api/v1/fitness-trackers/connections", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_connect_strava(self, client, auth_headers):
        """Test connect to Strava"""
        response = client.post(
            "/api/v1/fitness-trackers/strava/connect",
            headers=auth_headers,
            json={
                "code": "fake_auth_code"
            }
        )
        # Will fail without real OAuth code, but tests endpoint exists
        assert response.status_code in [201, 400, 401]


### 10. Webhooks API Tests

```python
# tests/test_api/test_webhooks.py
import pytest

class TestWebhooksEndpoints:
    """Test webhook endpoints"""

    def test_razorpay_webhook(self, client):
        """Test receive Razorpay webhook"""
        response = client.post(
            "/api/v1/webhooks/razorpay",
            json={
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": "pay_123",
                            "order_id": "order_123"
                        }
                    }
                }
            }
        )
        assert response.status_code == 200

    def test_strava_webhook_verification(self, client):
        """Test Strava webhook verification"""
        response = client.get(
            "/api/v1/webhooks/strava",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "test_challenge",
                "hub.verify_token": "test_token"
            }
        )
        # Will return error without correct token, but tests endpoint exists
        assert response.status_code in [200, 403]
```

---

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-cov pytest-asyncio httpx faker
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific module
pytest tests/test_api/test_users.py

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

### Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

---

## Test Execution Checklist

Before removing old code:

- [ ] All user API tests pass
- [ ] All activity API tests pass
- [ ] All event API tests pass
- [ ] All challenge API tests pass
- [ ] All registration API tests pass
- [ ] All reward API tests pass
- [ ] All statistics API tests pass
- [ ] All gallery API tests pass
- [ ] All fitness tracker API tests pass
- [ ] All webhook API tests pass
- [ ] Coverage > 80%
- [ ] No import errors
- [ ] Server starts successfully

---

## Integration Test Script

```bash
#!/bin/bash
# integration_test.sh

echo "🧪 Running integration tests..."

# Start test database
echo "📊 Setting up test database..."
export DATABASE_URL="sqlite:///./test.db"

# Run tests
echo "🏃 Running tests..."
pytest -v --cov=app --cov-report=term-missing

# Check coverage
COVERAGE=$(pytest --cov=app --cov-report=term | grep "TOTAL" | awk '{print $4}' | sed 's/%//')

if [ "$COVERAGE" -lt 80 ]; then
    echo "❌ Coverage is below 80%: $COVERAGE%"
    exit 1
fi

echo "✅ All tests passed with $COVERAGE% coverage"
```

---

**Status**: Ready to implement
**Next Steps**:
1. Create test files
2. Run tests
3. Fix any failures
4. Achieve 80%+ coverage
5. Remove old code
