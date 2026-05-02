# Quick Reference: Modular Architecture

## 🚀 Quick Import Guide

### Payments Module
```python
from app.modules.payments import (
    # Models
    Payment,

    # Entities
    PaymentEntity,

    # Value Objects
    Money, GatewayOrderId, RefundAmount,

    # Service
    PaymentService,

    # Commands
    CreatePaymentOrderCommand,
    VerifyPaymentCommand,
    ProcessRefundCommand,

    # Queries
    GetPaymentByIdQuery,
    GetUserPaymentsQuery,
)
```

### Shipping Module
```python
from app.modules.shipping import (
    # Models
    ShiprocketOrder, ShiprocketConfig,

    # Entities
    ShipmentEntity,

    # Value Objects
    TrackingNumber, ShippingAddress, AWBNumber,

    # Service
    ShippingService,

    # Commands
    CreateShipmentCommand,
    RetryShipmentCommand,

    # Queries
    GetShipmentByIdQuery,
    TrackShipmentQuery,
)
```

### Registrations Module
```python
from app.modules.registrations import (
    # Models
    Registration, EventRegistrationTier, RegistrationTier,

    # Entities
    RegistrationEntity, TierEntity,

    # Value Objects
    RegistrationNumber, BibNumber, ParticipantDetails,
    UpgradePrice, TierCapacity,

    # Service
    RegistrationService,

    # Commands
    RegisterForTierCommand,
    UpgradeTierCommand,
    CancelRegistrationCommand,

    # Queries
    GetUserRegistrationsQuery,
    GetEventRegistrationsQuery,
)
```

### Events Module
```python
from app.modules.events import (
    # Models
    Event, EventActivity,

    # Entities
    EventEntity, ActivityEntity,

    # Value Objects
    EventSlug, EventLocation, RegistrationPeriod,
    EventCapacity, EventDateRange,

    # Service
    EventService,

    # Commands
    CreateEventCommand,
    PublishEventCommand,
    UpdateEventCommand,

    # Queries
    GetEventByIdQuery,
    ListEventsQuery,
    GetUpcomingEventsQuery,
)
```

---

## 📖 Common Patterns

### Pattern 1: Check Business Rules

```python
# Payments
payment_entity = PaymentEntity(payment)
if payment_entity.is_refundable:
    # Can refund

# Registrations
registration_entity = RegistrationEntity(registration)
can_upgrade, reason = registration_entity.can_upgrade_to_tier(new_tier)

# Events
event_entity = EventEntity(event)
can_accept, reason = event_entity.can_accept_registrations()

# Shipping
shipment_entity = ShipmentEntity(shipment)
if shipment_entity.can_retry:
    # Can retry
```

### Pattern 2: Validate with Value Objects

```python
# Money validation
money = Money.from_float(100.50, 'INR')
paise = money.to_smallest_unit()

# Address validation
address = ShippingAddress(
    name="John Doe",
    phone="9876543210",
    address_line1="123 Main St",
    city="Mumbai",
    state="Maharashtra",
    pincode="400001"
)

# Registration number validation
reg_num = RegistrationNumber("EVT123-ABC123")
event_id = reg_num.event_id

# Event slug generation
slug = EventSlug.from_name("Mumbai Marathon 2026")
```

### Pattern 3: Execute Commands (Write)

```python
# Create payment
command = CreatePaymentOrderCommand(
    registration_id=123,
    user_id=456,
    amount=Decimal('100.00')
)
service = PaymentService(db)
result = service.create_payment_order(command)

# Create shipment
command = CreateShipmentCommand(
    user_reward_id="uuid",
    event_id=123,
    user_id=456,
    shipping_address=address.to_dict(),
    product_details={...}
)
service = ShippingService(db)
shipment = service.create_shipment(command)
```

### Pattern 4: Execute Queries (Read)

```python
# Get user payments
query = GetUserPaymentsQuery(
    user_id=456,
    current_user_id=456,
    skip=0,
    limit=10
)
service = PaymentService(db)
payments = service.get_user_payments(query)

# Get event registrations
query = GetEventRegistrationsQuery(
    event_id=123,
    skip=0,
    limit=100
)
service = RegistrationService(db)
registrations = service.get_registrations_by_event(query)
```

---

## 🔍 Entity Properties Cheat Sheet

### PaymentEntity
```python
# Status
.is_pending
.is_completed
.is_failed
.is_refunded

# Validation
.is_refundable
.is_stale(max_age_hours)
.validate_refund_amount(amount)

# Calculations
.create_refund_amount(amount)
.get_gateway_order_id()
```

### ShipmentEntity
```python
# Status
.is_pending
.is_shipped
.is_delivered
.is_failed
.is_cancelled

# Validation
.can_retry
.can_cancel
.requires_pickup
.is_stale(max_age_days)

# Checks
.has_tracking
.has_label
.is_created_in_shiprocket
```

### RegistrationEntity
```python
# Status
.is_pending
.is_confirmed
.is_active
.is_cancelled

# Payment
.has_paid
.has_outstanding_balance
.balance_owed
.total_amount_paid

# Tier
.uses_tier_system
.has_tier
.current_tier

# Validation
.can_upgrade_to_tier(tier)
.can_switch_tier(tier)
.can_be_cancelled()
.is_stale(max_age_hours)

# Calculations
.calculate_upgrade_price(tier)
```

### TierEntity
```python
# Capacity
.has_capacity_limit
.is_sold_out
.is_available
.capacity_remaining

# Pricing
.is_free
.requires_payment
.price

# Validation
.can_accept_registration()
.is_higher_than(other_tier)
.is_same_tier(other_tier)
```

### EventEntity
```python
# Status
.is_draft
.is_published
.is_upcoming
.is_ongoing
.is_completed
.is_cancelled

# Time
.has_started
.has_ended
.is_active
.days_until_start
.days_since_end

# Registration
.is_registration_open
.registration_opens_soon(days)
.registration_closes_soon(hours)
.days_until_registration_opens
.days_until_registration_closes

# Capacity
.has_capacity_limit
.is_full
.capacity_remaining
.is_nearly_full(threshold)

# Validation
.can_accept_registrations()
.can_be_published()
.can_be_cancelled()
.can_be_deleted()
.should_update_status()
```

### ActivityEntity
```python
# Capacity
.has_capacity_limit
.is_full
.capacity_remaining
.is_available

# Pricing
.is_free
.registration_fee

# Validation
.can_accept_registration()
```

---

## 💰 Value Object Usage

### Money
```python
# Creation
money = Money(Decimal('100.50'), 'INR')
money = Money.from_float(100.50, 'INR')
money = Money.from_smallest_unit(10050, 'INR')

# Operations
paise = money.to_smallest_unit()
new_money = money.add(other_money)
new_money = money.subtract(other_money)

# Properties
money.amount      # Decimal('100.50')
money.currency    # 'INR'
money.is_zero     # False
```

### ShippingAddress
```python
# Creation
address = ShippingAddress(
    name="John Doe",
    phone="9876543210",
    address_line1="123 Main St",
    address_line2="Apt 4",
    city="Mumbai",
    state="Maharashtra",
    pincode="400001"
)

# Usage
address_dict = address.to_dict()
is_valid = address.validate()
```

### RegistrationNumber
```python
# Creation
reg_num = RegistrationNumber("EVT123-ABC123")

# Properties
reg_num.value      # "EVT123-ABC123"
reg_num.event_id   # 123
str(reg_num)       # "EVT123-ABC123"
```

### UpgradePrice
```python
# Creation
upgrade = UpgradePrice.calculate(
    from_tier_price=Decimal("100.00"),
    to_tier_price=Decimal("150.00"),
    currency="INR"
)

# Properties
upgrade.amount              # Decimal('50.00')
upgrade.is_free            # False
upgrade.requires_payment   # True
str(upgrade)               # "INR 50.00"
```

### EventSlug
```python
# Creation
slug = EventSlug("mumbai-marathon-2026")
slug = EventSlug.from_name("Mumbai Marathon 2026")

# Properties
slug.value        # "mumbai-marathon-2026"
str(slug)         # "mumbai-marathon-2026"
```

### EventLocation
```python
# Creation
location = EventLocation(
    location_name="MMRDA Grounds",
    city="Mumbai",
    state="Maharashtra",
    country="India",
    full_address="MMRDA Grounds, BKC, Mumbai"
)

# Properties
location.short_location    # "Mumbai, Maharashtra"
str(location)             # "MMRDA Grounds, Mumbai, Maharashtra, India"
location_dict = location.to_dict()
```

---

## 🎯 When to Use What

| Scenario | Use |
|----------|-----|
| Check if payment can be refunded | `PaymentEntity.is_refundable` |
| Validate money amount | `Money` value object |
| Check if tier has capacity | `TierEntity.is_available` |
| Calculate upgrade cost | `RegistrationEntity.calculate_upgrade_price()` |
| Check if event accepts registrations | `EventEntity.can_accept_registrations()` |
| Validate shipping address | `ShippingAddress` value object |
| Create payment order | `CreatePaymentOrderCommand` |
| Get user's registrations | `GetUserRegistrationsQuery` |
| Generate event slug | `EventSlug.from_name()` |
| Check shipment retry eligibility | `ShipmentEntity.can_retry` |

---

## ⚡ Code Snippets

### Create and Verify Payment
```python
from app.modules.payments import PaymentService, CreatePaymentOrderCommand, VerifyPaymentCommand
from decimal import Decimal

# Create payment
create_cmd = CreatePaymentOrderCommand(
    registration_id=123,
    user_id=456,
    amount=Decimal('100.00'),
    currency='INR'
)
service = PaymentService(db)
payment_order = service.create_payment_order(create_cmd)

# Verify payment
verify_cmd = VerifyPaymentCommand(
    order_id=payment_order["order_id"],
    payment_id="pay_xyz",
    signature="signature_hash"
)
verified = service.verify_payment(verify_cmd)
```

### Register User for Event Tier
```python
from app.modules.registrations import RegistrationService, RegisterForTierCommand, ParticipantDetails

# Create participant details
participant = ParticipantDetails(
    name="John Doe",
    age=30,
    gender="male",
    t_shirt_size="L"
)

# Register
command = RegisterForTierCommand(
    user_id=456,
    event_id=123,
    tier_id=1,
    participant_name=participant.name,
    age=participant.age,
    gender=participant.gender,
    t_shirt_size=participant.t_shirt_size
)
service = RegistrationService(db)
result = service.register_for_event_tier(
    event_id=command.event_id,
    tier_id=command.tier_id,
    user_id=command.user_id,
    participant_name=command.participant_name,
    age=command.age,
    gender=command.gender,
    t_shirt_size=command.t_shirt_size
)
```

### Create and Track Shipment
```python
from app.modules.shipping import ShippingService, CreateShipmentCommand, ShippingAddress, TrackShipmentQuery

# Create shipment
address = ShippingAddress(
    name="John Doe",
    phone="9876543210",
    address_line1="123 Main St",
    city="Mumbai",
    state="Maharashtra",
    pincode="400001"
)

command = CreateShipmentCommand(
    user_reward_id="reward-uuid",
    event_id=123,
    user_id=456,
    shipping_address=address.to_dict(),
    product_details={
        "name": "Event Medal",
        "sku": "MEDAL-001",
        "price": 0
    }
)
service = ShippingService(db)
shipment = service.create_shipment(command)

# Track shipment
track_query = TrackShipmentQuery(shipment_id=shipment.id)
tracking_info = service.track_shipment(track_query)
```

### Create Event with Validation
```python
from app.modules.events import EventService, CreateEventCommand, EventSlug, EventLocation
from datetime import datetime, timedelta

# Generate slug
slug = EventSlug.from_name("Mumbai Marathon 2026")

# Create location
location = EventLocation(
    location_name="MMRDA Grounds",
    city="Mumbai",
    state="Maharashtra",
    country="India"
)

# Create event
now = datetime.now()
command = CreateEventCommand(
    organizer_id=789,
    name="Mumbai Marathon 2026",
    slug=slug.value,
    description="Annual marathon event in Mumbai",
    event_date=now + timedelta(days=90),
    registration_start_date=now,
    registration_end_date=now + timedelta(days=80),
    location_name=location.location_name,
    city=location.city,
    state=location.state,
    country=location.country,
    max_participants=1000,
    is_virtual=False
)
service = EventService(db)
event = service.create_event(command.dict(), command.organizer_id)
```

---

## 🔧 Troubleshooting

### Import Error
```python
# ❌ Wrong
from app.modules.payments.domain.payment import Payment

# ✅ Correct
from app.modules.payments import Payment
```

### Circular Import
```python
# ❌ Wrong - causes circular import
from app.modules.payments.services import PaymentService

# ✅ Correct - use TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.modules.payments.services import PaymentService
```

### Entity Modification
```python
# ❌ Wrong - entities are read-only wrappers
payment_entity.is_refundable = False

# ✅ Correct - modify the ORM model
payment = payment_entity._payment
payment.refund_status = RefundStatus.PROCESSED.value
db.commit()
```

---

## 📚 Documentation Links

- **Full Architecture**: [MODULAR_ARCHITECTURE.md](MODULAR_ARCHITECTURE.md)
- **Migration Guide**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **Architecture Summary**: [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md)
- **Modules README**: [../app/modules/README.md](../app/modules/README.md)

---

**Version**: 1.0
**Last Updated**: May 2, 2026
**Status**: Complete Reference for Phases 0-4
