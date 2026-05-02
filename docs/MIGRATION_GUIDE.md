# Migration Guide: Legacy to Modular Architecture

## Overview

This guide helps you migrate from the old monolithic structure to the new Domain-Driven Design (DDD) modular architecture.

**Current Status**: All 4 core modules are complete with 100% backward compatibility.

---

## Quick Reference

### Import Changes

| Old Import | New Import |
|------------|------------|
| `from app.models.payment import Payment` | `from app.modules.payments import Payment` |
| `from app.services.payment_service import PaymentService` | `from app.modules.payments import PaymentService` |
| `from app.models.shiprocket_order import ShiprocketOrder` | `from app.modules.shipping import ShiprocketOrder` |
| `from app.services.shiprocket.shiprocket_service import ShiprocketService` | `from app.modules.shipping import ShippingService` |
| `from app.models.registration import Registration` | `from app.modules.registrations import Registration` |
| `from app.services.registration_service import RegistrationService` | `from app.modules.registrations import RegistrationService` |
| `from app.models.event import Event, EventActivity` | `from app.modules.events import Event, EventActivity` |
| `from app.services.event_service import EventService` | `from app.modules.events import EventService` |

---

## Module-by-Module Migration

### 1. Payments Module

**Old Structure:**
```python
from app.models.payment import Payment
from app.services.payment_service import PaymentService
from app.repositories.payment_repository import PaymentRepository
```

**New Structure:**
```python
# All imports from one place
from app.modules.payments import (
    # Models
    Payment,

    # Entities (NEW - business rules)
    PaymentEntity,

    # Value Objects (NEW)
    Money, GatewayOrderId, RefundAmount,

    # Services
    PaymentService,

    # Repository
    PaymentRepository,

    # Commands (NEW - CQRS)
    CreatePaymentOrderCommand,
    VerifyPaymentCommand,

    # Queries (NEW - CQRS)
    GetPaymentByIdQuery,
    GetUserPaymentsQuery
)
```

**Using Business Rules:**
```python
from app.modules.payments import PaymentEntity, Money

# Old way - business logic in service
if payment.status == "completed" and payment.refund_status != "processed":
    # Can refund
    pass

# New way - business logic in entity
payment_entity = PaymentEntity(payment)
if payment_entity.is_refundable:
    # Can refund
    pass

# Old way - manual money calculations
amount_paise = int(amount * 100)

# New way - Money value object
money = Money.from_float(100.50, 'INR')
amount_paise = money.to_smallest_unit()
```

---

### 2. Shipping Module

**Old Structure:**
```python
from app.models.shiprocket_order import ShiprocketOrder
from app.services.shiprocket.shiprocket_service import ShiprocketService
from app.services.shiprocket.reward_fulfillment_service import RewardFulfillmentService
```

**New Structure:**
```python
from app.modules.shipping import (
    # Models
    ShiprocketOrder,

    # Entities (NEW)
    ShipmentEntity,

    # Value Objects (NEW)
    TrackingNumber, ShippingAddress,

    # Services
    ShippingService,

    # Commands (NEW)
    CreateShipmentCommand,

    # Queries (NEW)
    GetShipmentByIdQuery,
    TrackShipmentQuery
)
```

**Using Business Rules:**
```python
from app.modules.shipping import ShipmentEntity, ShippingAddress

# Old way - checking status manually
if shipment.status == "failed" and shipment.shiprocket_order_id is None:
    # Can retry
    pass

# New way - using entity
shipment_entity = ShipmentEntity(shipment)
if shipment_entity.can_retry:
    # Can retry
    pass

# Old way - passing address dict
address_dict = {
    "name": "John Doe",
    "phone": "9876543210",
    ...
}

# New way - validated value object
address = ShippingAddress(
    name="John Doe",
    phone="9876543210",
    address_line1="123 Main St",
    city="Mumbai",
    state="Maharashtra",
    pincode="400001"
)
```

---

### 3. Registrations Module

**Old Structure:**
```python
from app.models.registration import Registration
from app.models.event_registration_tier import EventRegistrationTier
from app.services.registration_service import RegistrationService
```

**New Structure:**
```python
from app.modules.registrations import (
    # Models
    Registration,
    EventRegistrationTier,
    RegistrationTier,

    # Entities (NEW)
    RegistrationEntity,
    TierEntity,

    # Value Objects (NEW)
    RegistrationNumber,
    BibNumber,
    ParticipantDetails,
    UpgradePrice,
    TierCapacity,

    # Services
    RegistrationService,

    # Commands (NEW)
    RegisterForTierCommand,
    UpgradeTierCommand,

    # Queries (NEW)
    GetUserRegistrationsQuery,
    GetEventRegistrationsQuery
)
```

**Using Business Rules:**
```python
from app.modules.registrations import RegistrationEntity, TierEntity, UpgradePrice
from decimal import Decimal

# Old way - complex validation logic in service
if registration.status == "pending" and registration.current_tier_id:
    current_tier = get_tier(registration.current_tier_id)
    new_tier = get_tier(new_tier_id)
    if new_tier.tier_order > current_tier.tier_order:
        # Can upgrade
        pass

# New way - using entity
registration_entity = RegistrationEntity(registration)
can_upgrade, reason = registration_entity.can_upgrade_to_tier(new_tier)
if can_upgrade:
    upgrade_price = registration_entity.calculate_upgrade_price(new_tier)

# Old way - manual tier capacity checks
if tier.max_registrations is not None:
    if tier.current_registrations >= tier.max_registrations:
        # Tier is full
        pass

# New way - using tier entity
tier_entity = TierEntity(tier)
if tier_entity.is_sold_out:
    # Tier is full
    pass

# New way - price calculation with value object
upgrade = UpgradePrice.calculate(
    from_tier_price=Decimal("100.00"),
    to_tier_price=Decimal("150.00")
)
print(f"Upgrade cost: {upgrade}")  # "INR 50.00"
```

---

### 4. Events Module

**Old Structure:**
```python
from app.models.event import Event, EventActivity
from app.services.event_service import EventService
from app.repositories.event_repository import EventRepository
```

**New Structure:**
```python
from app.modules.events import (
    # Models
    Event,
    EventActivity,

    # Entities (NEW)
    EventEntity,
    ActivityEntity,

    # Value Objects (NEW)
    EventSlug,
    EventLocation,
    RegistrationPeriod,
    EventCapacity,
    EventDateRange,

    # Services
    EventService,

    # Commands (NEW)
    CreateEventCommand,
    PublishEventCommand,

    # Queries (NEW)
    GetEventByIdQuery,
    ListEventsQuery
)
```

**Using Business Rules:**
```python
from app.modules.events import EventEntity, EventSlug, EventLocation
from datetime import datetime

# Old way - manual date/status checks
now = datetime.now()
if (event.registration_start_date <= now <= event.registration_end_date and
    event.status in ['published', 'upcoming'] and
    event.current_participants < event.max_participants):
    # Can accept registrations
    pass

# New way - using entity
event_entity = EventEntity(event)
can_accept, reason = event_entity.can_accept_registrations()
if can_accept:
    # Can accept registrations
    pass

# Check various event properties
if event_entity.is_registration_open:
    days_left = event_entity.days_until_registration_closes
    print(f"Registration closes in {days_left} days")

if event_entity.is_nearly_full(threshold=0.9):
    print("Event is 90% full!")

# Auto-update status based on dates
new_status = event_entity.should_update_status()
if new_status:
    event.status = new_status

# New way - value objects
slug = EventSlug.from_name("Mumbai Marathon 2026")
print(f"Generated slug: {slug}")  # "mumbai-marathon-2026"

location = EventLocation(
    location_name="MMRDA Grounds",
    city="Mumbai",
    state="Maharashtra",
    country="India"
)
print(f"Location: {location.short_location}")  # "Mumbai, Maharashtra"
```

---

## CQRS Pattern Migration

The new architecture uses Command Query Responsibility Segregation (CQRS).

### Commands (Write Operations)

**Old Way:**
```python
service = PaymentService(db)
payment = service.create_payment_order(
    registration_id=123,
    user_id=456,
    amount=Decimal('100.00'),
    currency='INR'
)
```

**New Way:**
```python
from app.modules.payments import PaymentService, CreatePaymentOrderCommand

command = CreatePaymentOrderCommand(
    registration_id=123,
    user_id=456,
    amount=Decimal('100.00'),
    currency='INR'
)

service = PaymentService(db)
payment = service.create_payment_order(command)
```

**Benefits:**
- Clear intent (this is a command)
- Validated inputs (command validates on creation)
- Easy to test
- Audit trail possible

### Queries (Read Operations)

**Old Way:**
```python
service = PaymentService(db)
payments = service.get_user_payments(user_id=456, skip=0, limit=10)
```

**New Way:**
```python
from app.modules.payments import PaymentService, GetUserPaymentsQuery

query = GetUserPaymentsQuery(
    user_id=456,
    current_user_id=456,
    skip=0,
    limit=10
)

service = PaymentService(db)
payments = service.get_user_payments(query)
```

**Benefits:**
- Clear intent (this is a read operation)
- Never modifies state
- Can be cached easily
- Validated parameters

---

## Step-by-Step Migration Process

### Phase 1: Update Imports (Low Risk)

1. Find all imports from old locations:
   ```bash
   grep -r "from app.models.payment import" .
   grep -r "from app.services.payment_service import" .
   ```

2. Replace with new imports:
   ```python
   # Old
   from app.models.payment import Payment
   from app.services.payment_service import PaymentService

   # New
   from app.modules.payments import Payment, PaymentService
   ```

3. Test - old imports still work with deprecation warnings!

### Phase 2: Adopt Business Rules (Medium Risk)

1. Find business logic in services
2. Check if entity has equivalent method
3. Replace with entity method:
   ```python
   # Old
   if payment.status == "completed":
       # logic

   # New
   payment_entity = PaymentEntity(payment)
   if payment_entity.is_completed:
       # logic
   ```

### Phase 3: Adopt Value Objects (Low Risk)

1. Find primitive types representing domain concepts
2. Replace with value objects:
   ```python
   # Old
   amount_paise = int(amount * 100)

   # New
   money = Money.from_float(amount)
   amount_paise = money.to_smallest_unit()
   ```

### Phase 4: Adopt CQRS (Optional)

1. Identify write vs read operations
2. Create command/query objects
3. Pass to service methods

---

## Testing Strategy

### 1. Unit Tests

Test entities without database:
```python
def test_payment_is_refundable():
    payment = Payment(status='completed', refund_status=None)
    entity = PaymentEntity(payment)
    assert entity.is_refundable is True
```

### 2. Integration Tests

Test services with mocked repositories:
```python
def test_payment_service_creates_order():
    db = Mock()
    service = PaymentService(db)
    command = CreatePaymentOrderCommand(...)
    result = service.create_payment_order(command)
    assert result is not None
```

### 3. Backward Compatibility Tests

Verify old imports still work:
```python
def test_old_imports_work_with_warnings():
    with pytest.warns(DeprecationWarning):
        from app.models.payment import Payment
```

---

## Common Pitfalls

### 1. Circular Imports

**Problem:**
```python
# entity.py
from app.modules.payments.services import PaymentService  # ❌

# service.py
from app.modules.payments.domain.entities import PaymentEntity  # ❌
```

**Solution:** Use TYPE_CHECKING
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.payments.services import PaymentService  # ✅
```

### 2. Modifying Entity State Directly

**Problem:**
```python
payment_entity.is_refundable = False  # ❌ Property is read-only
```

**Solution:** Entities are wrappers, modify the ORM model
```python
payment = payment_entity._payment
payment.refund_status = RefundStatus.PROCESSED.value  # ✅
```

### 3. Forgetting to Validate

**Problem:**
```python
command = CreatePaymentOrderCommand()  # ❌ Missing required fields
```

**Solution:** Commands validate on creation
```python
command = CreatePaymentOrderCommand(
    registration_id=123,  # ✅ All required fields
    user_id=456,
    amount=Decimal('100.00')
)
```

---

## Timeline Recommendations

- **Immediate**: Update imports (use deprecation warnings)
- **Week 1-2**: Adopt entities for business rules
- **Week 3-4**: Adopt value objects
- **Week 5+**: Optional CQRS migration

---

## Rollback Strategy

If issues arise, old imports still work! Simply revert to:
```python
from app.models.payment import Payment  # Still works
from app.services.payment_service import PaymentService  # Still works
```

Backward compatibility will be maintained until v2.0.

---

## Getting Help

1. Review [MODULAR_ARCHITECTURE.md](MODULAR_ARCHITECTURE.md)
2. Check module `__init__.py` for available exports
3. Look at tests in `tests/unit/modules/`
4. Ask questions in repository issues

---

**Last Updated**: May 2, 2026
**Version**: 1.0
**Applies To**: Phases 0-4 (Complete)
