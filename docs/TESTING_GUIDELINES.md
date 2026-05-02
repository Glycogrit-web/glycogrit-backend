# Testing Guidelines: Modular Architecture

Complete guide for testing the new modular architecture with examples, patterns, and best practices.

---

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Structure](#test-structure)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [E2E Testing](#e2e-testing)
6. [Test Patterns](#test-patterns)
7. [Fixtures and Factories](#fixtures-and-factories)
8. [Mock Strategies](#mock-strategies)
9. [Common Scenarios](#common-scenarios)

---

## Testing Philosophy

### Test Pyramid

```
              /\
             /  \      E2E Tests (10%)
            /____\     - Full workflows
           /      \    - Real database
          /        \   - API endpoints
         /          \
        /____________\  Integration Tests (30%)
       /              \ - Module interactions
      /                \- Mock externals
     /                  \
    /____________________\ Unit Tests (60%)
    - Entities, VOs       - Fast
    - Pure logic          - Isolated
```

### Guiding Principles

1. **Test Behavior, Not Implementation**: Focus on what the code does, not how
2. **AAA Pattern**: Arrange, Act, Assert
3. **One Assertion Per Test**: Keep tests focused
4. **Fast Feedback**: Unit tests < 1ms, Integration < 100ms
5. **Deterministic**: No flaky tests
6. **Readable**: Tests are documentation

---

## Test Structure

### Directory Layout

```
tests/
├── unit/
│   ├── modules/
│   │   ├── payments/
│   │   │   ├── test_payment_entity.py
│   │   │   ├── test_value_objects.py
│   │   │   ├── test_commands.py
│   │   │   └── test_queries.py
│   │   ├── shipping/
│   │   ├── registrations/
│   │   └── events/
│   └── core/
│       └── test_enums.py
│
├── integration/
│   ├── test_payment_service.py
│   ├── test_shipping_service.py
│   ├── test_registration_service.py
│   └── test_event_service.py
│
├── e2e/
│   ├── test_payment_workflows.py
│   ├── test_registration_workflows.py
│   └── test_event_lifecycle.py
│
├── fixtures/
│   ├── __init__.py
│   ├── db_fixtures.py
│   ├── user_fixtures.py
│   └── factory.py
│
└── conftest.py
```

---

## Unit Testing

### Testing Domain Entities

**File**: `tests/unit/modules/payments/test_payment_entity.py`

```python
import pytest
from datetime import datetime, timedelta
from app.modules.payments import Payment, PaymentEntity
from app.core.enums import PaymentStatus, RefundStatus


class TestPaymentEntity:
    """Test PaymentEntity business rules."""

    def test_is_refundable_when_completed_and_not_refunded(self):
        # Arrange
        payment = Payment(
            id=1,
            status=PaymentStatus.COMPLETED.value,
            refund_status=None,
            amount=10000,
            created_at=datetime.now()
        )
        entity = PaymentEntity(payment)

        # Act & Assert
        assert entity.is_refundable is True

    def test_is_not_refundable_when_already_refunded(self):
        # Arrange
        payment = Payment(
            id=1,
            status=PaymentStatus.COMPLETED.value,
            refund_status=RefundStatus.PROCESSED.value,
            amount=10000,
            created_at=datetime.now()
        )
        entity = PaymentEntity(payment)

        # Act & Assert
        assert entity.is_refundable is False

    def test_is_not_refundable_when_pending(self):
        # Arrange
        payment = Payment(
            id=1,
            status=PaymentStatus.PENDING.value,
            refund_status=None,
            amount=10000,
            created_at=datetime.now()
        )
        entity = PaymentEntity(payment)

        # Act & Assert
        assert entity.is_refundable is False

    def test_is_stale_after_max_age(self):
        # Arrange
        old_date = datetime.now() - timedelta(hours=25)
        payment = Payment(
            id=1,
            status=PaymentStatus.PENDING.value,
            amount=10000,
            created_at=old_date
        )
        entity = PaymentEntity(payment)

        # Act & Assert
        assert entity.is_stale(max_age_hours=24) is True

    def test_validate_refund_amount_success(self):
        # Arrange
        payment = Payment(
            id=1,
            status=PaymentStatus.COMPLETED.value,
            amount=10000,
            created_at=datetime.now()
        )
        entity = PaymentEntity(payment)

        # Act
        is_valid, error = entity.validate_refund_amount(5000)

        # Assert
        assert is_valid is True
        assert error is None

    def test_validate_refund_amount_exceeds_payment(self):
        # Arrange
        payment = Payment(
            id=1,
            status=PaymentStatus.COMPLETED.value,
            amount=10000,
            created_at=datetime.now()
        )
        entity = PaymentEntity(payment)

        # Act
        is_valid, error = entity.validate_refund_amount(15000)

        # Assert
        assert is_valid is False
        assert "exceeds payment amount" in error.lower()


class TestPaymentEntityStatuses:
    """Test payment status properties."""

    @pytest.mark.parametrize("status,expected", [
        (PaymentStatus.PENDING.value, True),
        (PaymentStatus.COMPLETED.value, False),
        (PaymentStatus.FAILED.value, False),
    ])
    def test_is_pending(self, status, expected):
        payment = Payment(id=1, status=status, amount=10000)
        entity = PaymentEntity(payment)
        assert entity.is_pending is expected
```

### Testing Value Objects

**File**: `tests/unit/modules/payments/test_value_objects.py`

```python
import pytest
from decimal import Decimal
from app.modules.payments import Money


class TestMoney:
    """Test Money value object."""

    def test_create_from_decimal(self):
        # Arrange & Act
        money = Money(Decimal("100.50"), "INR")

        # Assert
        assert money.amount == Decimal("100.50")
        assert money.currency == "INR"

    def test_create_from_float(self):
        # Arrange & Act
        money = Money.from_float(100.50, "INR")

        # Assert
        assert money.amount == Decimal("100.50")
        assert money.currency == "INR"

    def test_create_from_smallest_unit(self):
        # Arrange & Act
        money = Money.from_smallest_unit(10050, "INR")

        # Assert
        assert money.amount == Decimal("100.50")
        assert money.currency == "INR"

    def test_to_smallest_unit(self):
        # Arrange
        money = Money(Decimal("100.50"), "INR")

        # Act
        paise = money.to_smallest_unit()

        # Assert
        assert paise == 10050

    def test_add_money(self):
        # Arrange
        money1 = Money(Decimal("100.00"), "INR")
        money2 = Money(Decimal("50.50"), "INR")

        # Act
        result = money1.add(money2)

        # Assert
        assert result.amount == Decimal("150.50")
        assert result.currency == "INR"

    def test_subtract_money(self):
        # Arrange
        money1 = Money(Decimal("100.00"), "INR")
        money2 = Money(Decimal("30.00"), "INR")

        # Act
        result = money1.subtract(money2)

        # Assert
        assert result.amount == Decimal("70.00")

    def test_is_zero(self):
        # Arrange
        money = Money(Decimal("0.00"), "INR")

        # Act & Assert
        assert money.is_zero is True

    def test_cannot_add_different_currencies(self):
        # Arrange
        money1 = Money(Decimal("100.00"), "INR")
        money2 = Money(Decimal("50.00"), "USD")

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot perform operations on different currencies"):
            money1.add(money2)

    def test_string_representation(self):
        # Arrange
        money = Money(Decimal("100.50"), "INR")

        # Act
        result = str(money)

        # Assert
        assert result == "100.5 INR"

    def test_immutability(self):
        # Arrange
        money = Money(Decimal("100.00"), "INR")

        # Act & Assert
        with pytest.raises(AttributeError):
            money.amount = Decimal("200.00")
```

### Testing Entities with Complex Logic

**File**: `tests/unit/modules/registrations/test_registration_entity.py`

```python
import pytest
from decimal import Decimal
from datetime import datetime
from app.modules.registrations import (
    Registration,
    EventRegistrationTier,
    RegistrationEntity,
    TierEntity
)
from app.core.enums import RegistrationStatus


class TestRegistrationEntityTierUpgrade:
    """Test tier upgrade business rules."""

    def test_can_upgrade_to_higher_tier(self):
        # Arrange
        current_tier = EventRegistrationTier(
            id=1, tier_number=1, price=100.00, max_participants=100
        )
        new_tier = EventRegistrationTier(
            id=2, tier_number=2, price=150.00, max_participants=50
        )
        registration = Registration(
            id=1,
            event_id=1,
            user_id=1,
            status=RegistrationStatus.CONFIRMED.value,
            current_tier_id=1,
            current_tier=current_tier
        )
        entity = RegistrationEntity(registration)

        # Act
        can_upgrade, reason = entity.can_upgrade_to_tier(new_tier)

        # Assert
        assert can_upgrade is True
        assert reason is None

    def test_cannot_upgrade_to_same_tier(self):
        # Arrange
        tier = EventRegistrationTier(
            id=1, tier_number=1, price=100.00
        )
        registration = Registration(
            id=1,
            event_id=1,
            user_id=1,
            status=RegistrationStatus.CONFIRMED.value,
            current_tier_id=1,
            current_tier=tier
        )
        entity = RegistrationEntity(registration)

        # Act
        can_upgrade, reason = entity.can_upgrade_to_tier(tier)

        # Assert
        assert can_upgrade is False
        assert "already registered" in reason.lower()

    def test_cannot_upgrade_cancelled_registration(self):
        # Arrange
        current_tier = EventRegistrationTier(id=1, tier_number=1, price=100.00)
        new_tier = EventRegistrationTier(id=2, tier_number=2, price=150.00)
        registration = Registration(
            id=1,
            event_id=1,
            user_id=1,
            status=RegistrationStatus.CANCELLED.value,
            current_tier_id=1,
            current_tier=current_tier
        )
        entity = RegistrationEntity(registration)

        # Act
        can_upgrade, reason = entity.can_upgrade_to_tier(new_tier)

        # Assert
        assert can_upgrade is False
        assert "cancelled" in reason.lower()

    def test_calculate_upgrade_price(self):
        # Arrange
        current_tier = EventRegistrationTier(
            id=1, tier_number=1, price=100.00
        )
        new_tier = EventRegistrationTier(
            id=2, tier_number=2, price=175.50
        )
        registration = Registration(
            id=1,
            current_tier=current_tier
        )
        entity = RegistrationEntity(registration)

        # Act
        upgrade_price = entity.calculate_upgrade_price(new_tier)

        # Assert
        assert upgrade_price == Decimal("75.50")

    def test_calculate_upgrade_price_returns_zero_for_lower_tier(self):
        # Arrange
        current_tier = EventRegistrationTier(
            id=1, tier_number=1, price=150.00
        )
        new_tier = EventRegistrationTier(
            id=2, tier_number=2, price=100.00
        )
        registration = Registration(
            id=1,
            current_tier=current_tier
        )
        entity = RegistrationEntity(registration)

        # Act
        upgrade_price = entity.calculate_upgrade_price(new_tier)

        # Assert
        assert upgrade_price == Decimal("0.00")
```

---

## Integration Testing

### Testing Services with Database

**File**: `tests/integration/test_payment_service.py`

```python
import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from app.modules.payments import (
    PaymentService,
    CreatePaymentOrderCommand,
    VerifyPaymentCommand
)
from app.core.database import get_db


@pytest.fixture
def db_session():
    """Create test database session."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def payment_service(db_session):
    """Create payment service with test database."""
    return PaymentService(db_session)


@pytest.fixture
def test_user(db_session):
    """Create test user."""
    from app.models.user import User
    user = User(
        id=999,
        email="test@example.com",
        username="testuser"
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_registration(db_session, test_user):
    """Create test registration."""
    from app.modules.registrations import Registration
    from app.core.enums import RegistrationStatus

    registration = Registration(
        id=999,
        event_id=1,
        user_id=test_user.id,
        status=RegistrationStatus.PENDING.value,
        participant_name="Test User",
        amount=Decimal("100.00")
    )
    db_session.add(registration)
    db_session.commit()
    return registration


class TestPaymentServiceIntegration:
    """Integration tests for PaymentService."""

    def test_create_payment_order(self, payment_service, test_registration, test_user):
        # Arrange
        command = CreatePaymentOrderCommand(
            registration_id=test_registration.id,
            user_id=test_user.id,
            amount=Decimal("100.00"),
            currency="INR"
        )

        # Act
        result = payment_service.create_payment_order(command)

        # Assert
        assert result is not None
        assert "order_id" in result
        assert "amount" in result
        assert result["amount"] == 10000  # In paise

    def test_create_payment_order_invalid_registration(self, payment_service, test_user):
        # Arrange
        command = CreatePaymentOrderCommand(
            registration_id=99999,  # Non-existent
            user_id=test_user.id,
            amount=Decimal("100.00")
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Registration not found"):
            payment_service.create_payment_order(command)

    def test_verify_payment_updates_status(
        self,
        payment_service,
        test_registration,
        test_user,
        db_session
    ):
        # Arrange
        # First create payment order
        create_cmd = CreatePaymentOrderCommand(
            registration_id=test_registration.id,
            user_id=test_user.id,
            amount=Decimal("100.00")
        )
        order = payment_service.create_payment_order(create_cmd)

        # Mock successful payment verification
        verify_cmd = VerifyPaymentCommand(
            order_id=order["order_id"],
            payment_id="pay_test123",
            signature="valid_signature"
        )

        # Act
        result = payment_service.verify_payment(verify_cmd)

        # Assert
        assert result is not None
        assert result.status == "completed"

        # Verify in database
        db_session.refresh(test_registration)
        assert test_registration.status == "payment_completed"
```

### Testing Service Interactions

**File**: `tests/integration/test_registration_payment_flow.py`

```python
import pytest
from decimal import Decimal
from app.modules.registrations import RegistrationService
from app.modules.payments import PaymentService
from app.modules.events import Event, EventService


@pytest.fixture
def services(db_session):
    """Create all services."""
    return {
        'registration': RegistrationService(db_session),
        'payment': PaymentService(db_session),
        'event': EventService(db_session)
    }


@pytest.fixture
def test_event_with_tier(db_session):
    """Create test event with tier."""
    from datetime import datetime, timedelta
    from app.modules.events import EventRegistrationTier

    event = Event(
        id=1,
        name="Test Marathon",
        event_date=datetime.now() + timedelta(days=30),
        registration_start_date=datetime.now(),
        registration_end_date=datetime.now() + timedelta(days=20),
        uses_tier_system=True
    )
    tier = EventRegistrationTier(
        event_id=1,
        tier_number=1,
        tier_name="Early Bird",
        price=100.00,
        max_participants=100
    )
    db_session.add(event)
    db_session.add(tier)
    db_session.commit()
    return event, tier


class TestRegistrationPaymentFlow:
    """Test complete registration + payment workflow."""

    def test_complete_registration_flow(
        self,
        services,
        test_event_with_tier,
        test_user,
        db_session
    ):
        # Arrange
        event, tier = test_event_with_tier
        reg_service = services['registration']
        pay_service = services['payment']

        # Act - Step 1: Register for event
        registration = reg_service.register_for_event_tier(
            event_id=event.id,
            tier_id=tier.id,
            user_id=test_user.id,
            participant_name="Test User",
            age=30,
            gender="male"
        )
        assert registration.status == "pending"

        # Act - Step 2: Create payment order
        from app.modules.payments import CreatePaymentOrderCommand
        payment_cmd = CreatePaymentOrderCommand(
            registration_id=registration.id,
            user_id=test_user.id,
            amount=Decimal(str(tier.price))
        )
        payment_order = pay_service.create_payment_order(payment_cmd)
        assert payment_order is not None

        # Act - Step 3: Simulate payment verification
        from app.modules.payments import VerifyPaymentCommand
        verify_cmd = VerifyPaymentCommand(
            order_id=payment_order["order_id"],
            payment_id="pay_test123",
            signature="valid_sig"
        )
        verified_payment = pay_service.verify_payment(verify_cmd)

        # Assert - Final state
        db_session.refresh(registration)
        assert registration.status == "payment_completed"
        assert verified_payment.status == "completed"
```

---

## E2E Testing

### Testing Complete API Workflows

**File**: `tests/e2e/test_registration_workflows.py`

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers."""
    response = client.post("/api/auth/login", json={
        "email": test_user.email,
        "password": "testpassword"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestRegistrationE2E:
    """End-to-end registration workflow tests."""

    def test_complete_registration_workflow(
        self,
        client,
        auth_headers,
        test_event_with_tier
    ):
        event, tier = test_event_with_tier

        # Step 1: Get event details
        response = client.get(f"/api/events/{event.id}")
        assert response.status_code == 200
        event_data = response.json()
        assert event_data["uses_tier_system"] is True

        # Step 2: Register for event
        reg_response = client.post(
            f"/api/registrations/events/{event.id}/tiers/{tier.id}",
            headers=auth_headers,
            json={
                "participant_name": "John Doe",
                "age": 30,
                "gender": "male",
                "t_shirt_size": "L"
            }
        )
        assert reg_response.status_code == 201
        registration = reg_response.json()
        assert registration["status"] == "pending"
        registration_id = registration["id"]

        # Step 3: Create payment order
        payment_response = client.post(
            f"/api/payments/registrations/{registration_id}/create-order",
            headers=auth_headers
        )
        assert payment_response.status_code == 200
        payment_order = payment_response.json()
        assert "order_id" in payment_order

        # Step 4: Verify payment (simulated)
        verify_response = client.post(
            "/api/payments/verify",
            headers=auth_headers,
            json={
                "order_id": payment_order["order_id"],
                "payment_id": "pay_test123",
                "signature": "test_signature"
            }
        )
        assert verify_response.status_code == 200

        # Step 5: Verify registration is confirmed
        check_response = client.get(
            f"/api/registrations/{registration_id}",
            headers=auth_headers
        )
        assert check_response.status_code == 200
        updated_reg = check_response.json()
        assert updated_reg["status"] == "payment_completed"
```

---

## Test Patterns

### Pattern 1: Parameterized Tests

```python
import pytest


@pytest.mark.parametrize("status,expected_result", [
    ("pending", False),
    ("completed", True),
    ("failed", False),
    ("refunded", False),
])
def test_payment_completion_status(status, expected_result):
    payment = Payment(id=1, status=status, amount=10000)
    entity = PaymentEntity(payment)
    assert entity.is_completed == expected_result
```

### Pattern 2: Fixture Factories

```python
import pytest
from datetime import datetime, timedelta


@pytest.fixture
def payment_factory():
    """Factory for creating test payments."""
    def _create_payment(**kwargs):
        defaults = {
            "id": 1,
            "status": "completed",
            "amount": 10000,
            "created_at": datetime.now(),
            "user_id": 1,
            "registration_id": 1
        }
        defaults.update(kwargs)
        return Payment(**defaults)
    return _create_payment


def test_with_factory(payment_factory):
    # Create completed payment
    payment1 = payment_factory()
    assert payment1.status == "completed"

    # Create pending payment
    payment2 = payment_factory(status="pending")
    assert payment2.status == "pending"
```

### Pattern 3: Context Managers for Setup/Teardown

```python
from contextlib import contextmanager


@contextmanager
def temp_registration(db_session, **kwargs):
    """Temporary registration that gets cleaned up."""
    registration = Registration(**kwargs)
    db_session.add(registration)
    db_session.commit()
    try:
        yield registration
    finally:
        db_session.delete(registration)
        db_session.commit()


def test_with_context_manager(db_session):
    with temp_registration(db_session, event_id=1, user_id=1) as reg:
        # Test with registration
        assert reg.id is not None
    # Registration automatically cleaned up
```

---

## Fixtures and Factories

### Complete Factory Implementation

**File**: `tests/fixtures/factory.py`

```python
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from app.modules.payments import Payment
from app.modules.registrations import Registration, EventRegistrationTier
from app.modules.events import Event
from app.core.enums import PaymentStatus, RegistrationStatus, EventStatus


class PaymentFactory:
    """Factory for creating test payments."""

    @staticmethod
    def create(
        id: int = 1,
        status: str = PaymentStatus.COMPLETED.value,
        amount: int = 10000,
        user_id: int = 1,
        registration_id: int = 1,
        **kwargs
    ) -> Payment:
        defaults = {
            "id": id,
            "status": status,
            "amount": amount,
            "user_id": user_id,
            "registration_id": registration_id,
            "created_at": datetime.now(),
            "currency": "INR"
        }
        defaults.update(kwargs)
        return Payment(**defaults)


class RegistrationFactory:
    """Factory for creating test registrations."""

    @staticmethod
    def create(
        id: int = 1,
        event_id: int = 1,
        user_id: int = 1,
        status: str = RegistrationStatus.CONFIRMED.value,
        **kwargs
    ) -> Registration:
        defaults = {
            "id": id,
            "event_id": event_id,
            "user_id": user_id,
            "status": status,
            "participant_name": "Test User",
            "amount": Decimal("100.00"),
            "created_at": datetime.now()
        }
        defaults.update(kwargs)
        return Registration(**defaults)


class EventFactory:
    """Factory for creating test events."""

    @staticmethod
    def create(
        id: int = 1,
        name: str = "Test Event",
        status: str = EventStatus.PUBLISHED.value,
        **kwargs
    ) -> Event:
        now = datetime.now()
        defaults = {
            "id": id,
            "name": name,
            "status": status,
            "event_date": now + timedelta(days=30),
            "registration_start_date": now,
            "registration_end_date": now + timedelta(days=20),
            "created_at": now
        }
        defaults.update(kwargs)
        return Event(**defaults)


class TierFactory:
    """Factory for creating test tiers."""

    @staticmethod
    def create(
        id: int = 1,
        event_id: int = 1,
        tier_number: int = 1,
        price: float = 100.00,
        **kwargs
    ) -> EventRegistrationTier:
        defaults = {
            "id": id,
            "event_id": event_id,
            "tier_number": tier_number,
            "tier_name": f"Tier {tier_number}",
            "price": price,
            "max_participants": 100,
            "is_active": True
        }
        defaults.update(kwargs)
        return EventRegistrationTier(**defaults)
```

---

## Mock Strategies

### Mocking External Services

```python
from unittest.mock import Mock, patch, MagicMock


def test_shiprocket_order_creation(payment_service):
    # Mock Shiprocket API client
    with patch('app.modules.shipping.integrations.shiprocket.client.ShiprocketClient') as mock_client:
        # Setup mock
        mock_instance = mock_client.return_value
        mock_instance.create_order.return_value = {
            "order_id": "SR123",
            "shipment_id": "SHIP456"
        }

        # Test
        from app.modules.shipping import CreateShipmentCommand
        command = CreateShipmentCommand(...)
        result = shipping_service.create_shipment(command)

        # Verify
        assert result.shiprocket_order_id == "SR123"
        mock_instance.create_order.assert_called_once()
```

### Mocking Database Queries

```python
def test_get_payment_by_id(payment_service):
    # Mock repository
    with patch.object(payment_service._repository, 'get_by_id') as mock_get:
        # Setup mock
        mock_payment = PaymentFactory.create(id=123)
        mock_get.return_value = mock_payment

        # Test
        from app.modules.payments import GetPaymentByIdQuery
        query = GetPaymentByIdQuery(payment_id=123, user_id=1)
        result = payment_service.get_payment_by_id(query)

        # Verify
        assert result.id == 123
        mock_get.assert_called_once_with(123)
```

---

## Common Scenarios

### Testing Error Handling

```python
def test_payment_service_handles_invalid_amount():
    # Arrange
    command = CreatePaymentOrderCommand(
        registration_id=1,
        user_id=1,
        amount=Decimal("-100.00")  # Invalid negative amount
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Amount must be positive"):
        service.create_payment_order(command)


def test_registration_service_handles_sold_out_tier():
    # Arrange
    sold_out_tier = TierFactory.create(
        max_participants=10,
        current_participants=10
    )
    command = RegisterForTierCommand(
        user_id=1,
        event_id=1,
        tier_id=sold_out_tier.id
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Tier is sold out"):
        service.register_for_tier(command)
```

### Testing Async Operations

```python
import pytest
import asyncio


@pytest.mark.asyncio
async def test_async_payment_webhook():
    # Arrange
    webhook_data = {...}

    # Act
    result = await payment_service.process_webhook_async(webhook_data)

    # Assert
    assert result.status == "processed"
```

---

## Running Tests

### Command Reference

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/modules/payments/test_payment_entity.py

# Run tests by marker
pytest -m unit
pytest -m integration
pytest -m e2e

# Run with coverage
pytest --cov=app --cov-report=html

# Run with verbose output
pytest -v

# Run specific test
pytest tests/unit/modules/payments/test_payment_entity.py::TestPaymentEntity::test_is_refundable

# Run in parallel
pytest -n auto

# Stop on first failure
pytest -x

# Show print statements
pytest -s
```

### Pytest Configuration

**File**: `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (database required)
    e2e: End-to-end tests (full API)
    slow: Slow-running tests

addopts =
    -v
    --strict-markers
    --tb=short
    --disable-warnings
```

---

## Best Practices

1. **Keep Tests Fast**: Unit tests < 1ms, Integration < 100ms
2. **Use Factories**: Don't repeat test data setup
3. **One Assertion Per Test**: Focus on single behavior
4. **Descriptive Names**: `test_cannot_upgrade_cancelled_registration`
5. **AAA Pattern**: Arrange, Act, Assert with comments
6. **Clean Up**: Use fixtures and context managers
7. **Mock External Services**: Don't hit real APIs in tests
8. **Test Edge Cases**: Boundary conditions, null values
9. **Use Parametrize**: Test multiple inputs efficiently
10. **Maintain Test Coverage**: Aim for 80%+ coverage

---

**Version**: 1.0
**Last Updated**: May 2, 2026
**Status**: Complete Testing Guide
