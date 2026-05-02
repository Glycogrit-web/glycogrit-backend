# Modular Architecture Documentation

## Overview

The glycogrit-backend has been refactored from a monolithic structure to a **Domain-Driven Design (DDD) modular architecture**. This document describes the new architecture, migration patterns, and best practices.

## Architecture Principles

### 1. Domain-Driven Design (DDD)
Each module follows DDD principles:
- **Entities**: Objects with identity that encapsulate business rules
- **Value Objects**: Immutable objects representing domain concepts
- **Services**: Orchestrate domain operations
- **Repositories**: Abstract data access
- **Aggregates**: Clusters of domain objects treated as a unit

### 2. CQRS Pattern
Commands (writes) are separated from Queries (reads):
- **Commands**: Modify state, return void or simple confirmation
- **Queries**: Read state, never modify, return data
- **Benefits**: Clear intent, easier testing, better scalability

### 3. Separation of Concerns
Each layer has a specific responsibility:
- **Domain**: Business logic and rules
- **Services**: Application logic and orchestration
- **Repositories**: Data access
- **Schemas**: Input/output validation
- **API**: HTTP handling and routing

## Module Structure

```
app/modules/<module_name>/
├── __init__.py              # Public API exports
├── domain/
│   ├── __init__.py
│   ├── <model>.py          # SQLAlchemy models
│   ├── entities.py         # Domain entities (business rules)
│   └── value_objects.py    # Immutable value objects
├── services/
│   ├── __init__.py
│   ├── <module>_service.py # Main service
│   ├── commands.py         # Write operations
│   └── queries.py          # Read operations
├── repositories/
│   ├── __init__.py
│   └── <module>_repository.py
├── schemas/
│   ├── __init__.py
│   └── <module>.py         # Pydantic schemas
└── api/
    ├── __init__.py
    └── routes.py           # FastAPI routes
```

## Implemented Modules

### Phase 0: Core Enums ✅
**Location**: `app/core/enums.py`

Centralized enum definitions replacing magic strings:
- `PaymentStatus`, `RefundStatus`, `PaymentMethod`
- `RegistrationStatus`
- `EventStatus`, `EventDifficulty`
- `ShipmentStatus`
- And 12 more enum types

### Phase 1: Payments Module ✅
**Location**: `app/modules/payments/`

Handles all payment operations:
- Payment order creation (Razorpay, Stripe)
- Payment verification and signature validation
- Refund processing
- Payment history tracking

**Key Components**:
- `PaymentEntity`: 15+ business rules
- `Money`, `GatewayOrderId`, `RefundAmount`: Value objects
- 5 Commands, 6 Queries

**Business Rules Examples**:
```python
from app.modules.payments import PaymentEntity, Money

payment_entity = PaymentEntity(payment)

# Check if payment can be refunded
if payment_entity.is_refundable:
    refund = payment_entity.create_refund_amount(amount=100.00)

# Validate payment age
if payment_entity.is_stale(max_age_hours=24):
    # Cancel stale payment
    pass
```

### Phase 2: Shipping Module ✅
**Location**: `app/modules/shipping/`

Handles shipping and fulfillment:
- Shipment order creation
- Shiprocket integration
- Pickup scheduling
- Tracking and manifest generation

**Key Components**:
- `ShipmentEntity`: 20+ business rules
- `TrackingNumber`, `ShippingAddress`, `PickupSchedule`: Value objects
- 5 Commands, 7 Queries

**Business Rules Examples**:
```python
from app.modules.shipping import ShipmentEntity, ShippingAddress

shipment_entity = ShipmentEntity(shipment)

# Check if shipment can be retried
if shipment_entity.can_retry:
    service.retry_failed_shipment(shipment.id)

# Check if pickup needs scheduling
if shipment_entity.requires_pickup:
    # Schedule pickup
    pass

# Validate shipping address
address = ShippingAddress(
    name="John Doe",
    phone="9876543210",
    address_line1="123 Main St",
    address_line2=None,
    city="Mumbai",
    state="Maharashtra",
    pincode="400001"
)
```

## Usage Patterns

### 1. Importing from Modules

**Recommended (New Way)**:
```python
# Import from module (clean, semantic)
from app.modules.payments import PaymentService, Payment, PaymentEntity
from app.modules.payments import Money, CreatePaymentOrderCommand

from app.modules.shipping import ShippingService, ShipmentEntity
from app.modules.shipping import TrackingNumber, ShippingAddress
```

**Deprecated (Old Way - Still Works)**:
```python
# Old imports (backward compatible, with deprecation warnings)
from app.models.payment import Payment
from app.services.payment_service import PaymentService
# These will be removed in v2.0
```

### 2. Using Domain Entities

Domain entities encapsulate business rules:

```python
from app.modules.payments import PaymentEntity

# Create entity from ORM model
payment_entity = PaymentEntity(payment)

# Use business rule methods
if payment_entity.is_refundable:
    # Business logic ensures payment can be refunded
    refund_amount = payment_entity.create_refund_amount()

    # Validate refund amount
    is_valid, error = payment_entity.validate_refund_amount(amount)
    if not is_valid:
        raise ValueError(error)

# Check payment age
if payment_entity.is_stale(max_age_hours=48):
    # Handle stale payments
    pass
```

### 3. Using Value Objects

Value objects are immutable and validated:

```python
from app.modules.payments import Money
from app.modules.shipping import ShippingAddress

# Create Money value object
money = Money.from_float(100.50, 'INR')
print(money)  # "100.5 INR"

# Convert to smallest unit
paise = money.to_smallest_unit()  # 10050

# Money arithmetic
total = money.add(Money(Decimal('50.00'), 'INR'))

# Create ShippingAddress (validates on creation)
try:
    address = ShippingAddress(
        name="J",  # Too short!
        phone="123",  # Too short!
        address_line1="",  # Empty!
        city="Mumbai",
        state="Maharashtra",
        pincode="400001"
    )
except ValueError as e:
    print(f"Validation error: {e}")
```

### 4. Using Commands and Queries (CQRS)

**Commands** (write operations):
```python
from app.modules.payments import CreatePaymentOrderCommand, PaymentService

command = CreatePaymentOrderCommand(
    registration_id=123,
    user_id=456,
    amount=Decimal('100.00'),
    currency='INR',
    tier_id=1,
    is_tier_upgrade=False
)

service = PaymentService(db)
result = service.create_payment_order(command)
```

**Queries** (read operations):
```python
from app.modules.payments import GetUserPaymentsQuery, PaymentService

query = GetUserPaymentsQuery(
    user_id=456,
    current_user_id=456,
    skip=0,
    limit=10
)

service = PaymentService(db)
payments = service.get_user_payments(query)
```

### 5. Service Layer Usage

Services orchestrate domain operations:

```python
from app.modules.shipping import ShippingService
from app.modules.shipping import CreateShipmentCommand, ShippingAddress

service = ShippingService(db)

# Create shipment
address = ShippingAddress(
    name="John Doe",
    phone="9876543210",
    address_line1="123 Main St",
    address_line2=None,
    city="Mumbai",
    state="Maharashtra",
    pincode="400001"
)

shipment = service.create_shipment(
    user_reward_id="uuid-here",
    event_id=123,
    user_id=456,
    shipping_address=address,
    product_details={
        "name": "Event Medal",
        "sku": "MEDAL-GOLD",
        "price": 0
    }
)

# Get tracking information
tracking = service.track_shipment(shipment.id)
print(f"Tracking: {tracking['tracking_number']}")
```

### 6. Registrations Service Usage

Registrations service orchestrates event registrations:

```python
from app.modules.registrations import RegistrationService
from app.modules.registrations import RegisterForTierCommand, UpgradeTierCommand
from app.modules.registrations import ParticipantDetails

service = RegistrationService(db)

# Register for tier-based event
participant = ParticipantDetails(
    name="John Doe",
    age=30,
    gender="male",
    t_shirt_size="L"
)

command = RegisterForTierCommand(
    user_id=456,
    event_id=123,
    tier_id=1,
    participant_name=participant.name,
    age=participant.age,
    gender=participant.gender,
    t_shirt_size=participant.t_shirt_size
)

result = service.register_for_event_tier(
    event_id=command.event_id,
    tier_id=command.tier_id,
    user_id=command.user_id,
    participant_name=command.participant_name,
    age=command.age,
    gender=command.gender,
    t_shirt_size=command.t_shirt_size
)

# Upgrade to higher tier
upgrade_cmd = UpgradeTierCommand(
    registration_id=result["registration"]["id"],
    new_tier_id=2,
    user_id=456
)

upgrade_result = service.upgrade_tier(
    registration_id=upgrade_cmd.registration_id,
    new_tier_id=upgrade_cmd.new_tier_id,
    user_id=upgrade_cmd.user_id
)

print(f"Upgrade price: {upgrade_result['upgrade_price']}")
```

## Migration Guide

### Step 1: Update Imports

Replace old imports with new module imports:

```python
# Before
from app.models.payment import Payment
from app.services.payment_service import PaymentService
from app.repositories.payment_repository import PaymentRepository

# After
from app.modules.payments import Payment, PaymentService, PaymentRepository
```

### Step 2: Use Domain Entities

Extract business logic to domain entities:

```python
# Before (business logic in service)
def can_refund_payment(payment):
    if payment.status != "completed":
        return False
    if payment.refund_status == "processed":
        return False
    return True

# After (business logic in entity)
from app.modules.payments import PaymentEntity

payment_entity = PaymentEntity(payment)
if payment_entity.is_refundable:
    # Refund the payment
    pass
```

### Step 3: Use Value Objects

Replace primitive types with value objects:

```python
# Before
amount = Decimal('100.50')
currency = 'INR'
paise = int(amount * 100)

# After
from app.modules.payments import Money

money = Money.from_float(100.50, 'INR')
paise = money.to_smallest_unit()
```

### Step 4: Adopt CQRS

Separate commands from queries:

```python
# Before
def create_payment(registration_id, user_id, amount, ...):
    # Create payment
    pass

# After
from app.modules.payments import CreatePaymentOrderCommand

command = CreatePaymentOrderCommand(
    registration_id=registration_id,
    user_id=user_id,
    amount=amount,
    ...
)
result = service.execute_command(command)
```

## Testing Patterns

### 1. Testing Domain Entities

Domain entities can be tested without database:

```python
import pytest
from app.modules.payments.domain.entities import PaymentEntity
from app.models.payment import Payment

def test_payment_is_refundable():
    # Create mock payment
    payment = Payment(
        status='completed',
        refund_status=None
    )

    entity = PaymentEntity(payment)
    assert entity.is_refundable is True

def test_payment_not_refundable_when_already_refunded():
    payment = Payment(
        status='completed',
        refund_status='processed'
    )

    entity = PaymentEntity(payment)
    assert entity.is_refundable is False
```

### 2. Testing Value Objects

Value objects validate on creation:

```python
import pytest
from decimal import Decimal
from app.modules.payments.domain.value_objects import Money

def test_money_creation():
    money = Money(Decimal('100.50'), 'INR')
    assert money.amount == Decimal('100.50')
    assert money.currency == 'INR'

def test_money_negative_amount_raises_error():
    with pytest.raises(ValueError, match="Amount cannot be negative"):
        Money(Decimal('-10.00'), 'INR')

def test_money_to_smallest_unit():
    money = Money(Decimal('100.50'), 'INR')
    assert money.to_smallest_unit() == 10050
```

### 3. Testing Services

Services can be tested with mocked repositories:

```python
from unittest.mock import Mock
from app.modules.payments import PaymentService, CreatePaymentOrderCommand

def test_create_payment_order():
    # Mock database
    db = Mock()

    # Create service
    service = PaymentService(db)

    # Execute command
    command = CreatePaymentOrderCommand(
        registration_id=123,
        user_id=456,
        amount=Decimal('100.00')
    )

    # Test service method
    # ... test logic
```

## Best Practices

### 1. Keep Entities Focused
- One entity per aggregate root
- Encapsulate related business rules
- Keep entities < 200 lines

### 2. Use Value Objects for Concepts
- Currency amounts → `Money`
- Addresses → `ShippingAddress`
- Tracking numbers → `TrackingNumber`
- Any validated concept → Value Object

### 3. Command/Query Naming
- Commands: Verb + Noun (e.g., `CreatePaymentOrder`)
- Queries: Get + Description (e.g., `GetUserPayments`)

### 4. Service Methods
- Keep services thin
- Delegate to domain entities
- One method = one responsibility

### 5. Backward Compatibility
- Always provide re-exports during migration
- Use deprecation warnings
- Remove after 2-3 release cycles

### Phase 3: Registrations Module ✅
**Location**: `app/modules/registrations/`

Handles event registrations and tier-based registration system:
- Event registration (with and without tiers)
- Tier upgrades and downgrades
- Payment tracking
- Participant management
- Bib number assignment

**Key Components**:
- `RegistrationEntity`: 25+ business rules
- `TierEntity`: 15+ business rules
- `RegistrationNumber`, `BibNumber`, `ParticipantDetails`, `UpgradePrice`, `TierCapacity`: Value objects
- 8 Commands, 12 Queries

**Business Rules Examples**:
```python
from app.modules.registrations import RegistrationEntity, TierEntity, UpgradePrice

registration_entity = RegistrationEntity(registration)

# Check if can upgrade to tier
can_upgrade, reason = registration_entity.can_upgrade_to_tier(new_tier)
if can_upgrade:
    upgrade_price = registration_entity.calculate_upgrade_price(new_tier)

# Check tier availability
tier_entity = TierEntity(tier)
if tier_entity.is_available:
    # Tier is active and has capacity
    pass

# Create and validate value objects
from app.modules.registrations import RegistrationNumber, UpgradePrice
from decimal import Decimal

reg_num = RegistrationNumber("EVT123-ABC123")
print(f"Event ID: {reg_num.event_id}")

upgrade = UpgradePrice.calculate(Decimal("100.00"), Decimal("150.00"))
print(f"Upgrade cost: {upgrade}")
```

### Phase 4: Events Module ✅
**Location**: `app/modules/events/`

Handles event lifecycle, registration periods, and capacity management:
- Event creation and management
- Status lifecycle (draft → published → upcoming → ongoing → completed)
- Registration period validation
- Capacity tracking
- Activity management

**Key Components**:
- `EventEntity`: 30+ business rules
- `ActivityEntity`: 8+ business rules
- `EventSlug`, `EventLocation`, `RegistrationPeriod`, `EventCapacity`, `EventDateRange`: Value objects
- 8 Commands, 11 Queries

**Business Rules Examples**:
```python
from app.modules.events import EventEntity, ActivityEntity

event_entity = EventEntity(event)

# Check if event can accept registrations
can_accept, reason = event_entity.can_accept_registrations()
if can_accept:
    # Allow registration
    pass

# Check registration period
if event_entity.is_registration_open:
    days_left = event_entity.days_until_registration_closes
    print(f"Registration closes in {days_left} days")

# Check capacity
if event_entity.is_nearly_full(threshold=0.9):
    print("Event is 90% full!")

# Use value objects
from app.modules.events import EventSlug, EventLocation

slug = EventSlug.from_name("Mumbai Marathon 2026")
location = EventLocation("MMRDA Grounds", "Mumbai", "Maharashtra", "India")
```

## Future Modules

### Phase 5: Integration & Cleanup (Pending)
- Remove backward compatibility layers
- Update main.py imports
- Comprehensive documentation

## Resources

- **Plan File**: `.claude/plans/ethereal-weaving-hamming.md`
- **Test Files**: `tests/unit/modules/`
- **Enum Tests**: `tests/unit/test_enums.py`

## Support

For questions or issues with the modular architecture:
1. Review this documentation
2. Check the plan file for detailed implementation steps
3. Examine existing modules (payments, shipping) as examples
4. Create an issue in the repository

---

**Last Updated**: May 2, 2026
**Version**: 1.2
**Status**: Phases 0-4 Complete, Phase 5 Pending
