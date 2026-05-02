# GlycoGrit Modules

Domain-Driven Design (DDD) modular architecture for glycogrit-backend.

## Quick Start

```python
# Import everything you need from one place
from app.modules.payments import Payment, PaymentEntity, Money, PaymentService
from app.modules.shipping import ShipmentEntity, ShippingAddress, ShippingService
from app.modules.registrations import Registration, RegistrationEntity, TierEntity
from app.modules.events import Event, EventEntity, EventService
```

## Available Modules

### 1. Payments (`app.modules.payments`)
Handles payment processing, verification, and refunds.

**Key Exports**:
- Models: `Payment`
- Entities: `PaymentEntity`
- Value Objects: `Money`, `GatewayOrderId`, `RefundAmount`
- Service: `PaymentService`
- Commands: `CreatePaymentOrderCommand`, `VerifyPaymentCommand`, ...
- Queries: `GetPaymentByIdQuery`, `GetUserPaymentsQuery`, ...

### 2. Shipping (`app.modules.shipping`)
Handles shipment management and Shiprocket integration.

**Key Exports**:
- Models: `ShiprocketOrder`, `ShiprocketOrderStatus`
- Entities: `ShipmentEntity`
- Value Objects: `TrackingNumber`, `ShippingAddress`, `AWBNumber`
- Service: `ShippingService`
- Commands: `CreateShipmentCommand`, `RetryShipmentCommand`, ...
- Queries: `GetShipmentByIdQuery`, `TrackShipmentQuery`, ...

### 3. Registrations (`app.modules.registrations`)
Handles event registrations and tier management.

**Key Exports**:
- Models: `Registration`, `EventRegistrationTier`, `RegistrationTier`
- Entities: `RegistrationEntity`, `TierEntity`
- Value Objects: `RegistrationNumber`, `BibNumber`, `ParticipantDetails`, `UpgradePrice`
- Service: `RegistrationService`
- Commands: `RegisterForTierCommand`, `UpgradeTierCommand`, ...
- Queries: `GetUserRegistrationsQuery`, `GetEventRegistrationsQuery`, ...

### 4. Events (`app.modules.events`)
Handles event lifecycle and activity management.

**Key Exports**:
- Models: `Event`, `EventActivity`
- Entities: `EventEntity`, `ActivityEntity`
- Value Objects: `EventSlug`, `EventLocation`, `RegistrationPeriod`, `EventCapacity`
- Service: `EventService`
- Commands: `CreateEventCommand`, `PublishEventCommand`, ...
- Queries: `GetEventByIdQuery`, `ListEventsQuery`, ...

## Module Structure

Each module follows this standard structure:

```
module_name/
├── __init__.py              # Public API exports
├── domain/
│   ├── __init__.py
│   ├── {model}.py          # SQLAlchemy models
│   ├── entities.py         # Domain entities (business rules)
│   └── value_objects.py    # Immutable value objects
├── services/
│   ├── __init__.py
│   ├── {module}_service.py # Main service
│   ├── commands.py         # Write operations
│   └── queries.py          # Read operations
├── repositories/
│   ├── __init__.py
│   └── {module}_repository.py
├── schemas/
│   ├── __init__.py
│   └── {module}.py         # Pydantic schemas
└── api/
    ├── __init__.py
    └── routes.py           # FastAPI routes
```

## Usage Examples

### Using Entities (Business Rules)

```python
from app.modules.payments import PaymentEntity

payment_entity = PaymentEntity(payment)

# Check business rules
if payment_entity.is_refundable:
    refund_amount = payment_entity.create_refund_amount(100.00)
    is_valid, error = payment_entity.validate_refund_amount(refund_amount)
```

### Using Value Objects

```python
from app.modules.payments import Money
from decimal import Decimal

# Create validated money object
money = Money.from_float(100.50, 'INR')
print(money)  # "100.5 INR"

# Convert to smallest unit
paise = money.to_smallest_unit()  # 10050

# Money arithmetic
total = money.add(Money(Decimal('50.00'), 'INR'))
```

### Using Commands (Write Operations)

```python
from app.modules.payments import PaymentService, CreatePaymentOrderCommand
from decimal import Decimal

command = CreatePaymentOrderCommand(
    registration_id=123,
    user_id=456,
    amount=Decimal('100.00'),
    currency='INR'
)

service = PaymentService(db)
result = service.create_payment_order(command)
```

### Using Queries (Read Operations)

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

## Architecture Patterns

### 1. Domain-Driven Design (DDD)
- **Entities**: Business rules and domain logic
- **Value Objects**: Immutable, validated concepts
- **Aggregates**: Cluster of domain objects
- **Repositories**: Abstract data access

### 2. CQRS (Command Query Responsibility Segregation)
- **Commands**: Modify state (write operations)
- **Queries**: Read state (read operations)
- **Benefits**: Clear intent, easier testing, better scalability

### 3. Separation of Concerns
- **Domain**: Business logic
- **Services**: Application orchestration
- **Repositories**: Data access
- **Schemas**: Input/output validation
- **API**: HTTP handling

## Testing

### Unit Tests (Entities)
```python
def test_payment_is_refundable():
    payment = Payment(status='completed', refund_status=None)
    entity = PaymentEntity(payment)
    assert entity.is_refundable is True
```

### Integration Tests (Services)
```python
def test_create_payment_order():
    db = Mock()
    service = PaymentService(db)
    command = CreatePaymentOrderCommand(...)
    result = service.create_payment_order(command)
    assert result is not None
```

## Documentation

- **Architecture Overview**: [../../../docs/ARCHITECTURE_SUMMARY.md](../../../docs/ARCHITECTURE_SUMMARY.md)
- **Module Documentation**: [../../../docs/MODULAR_ARCHITECTURE.md](../../../docs/MODULAR_ARCHITECTURE.md)
- **Migration Guide**: [../../../docs/MIGRATION_GUIDE.md](../../../docs/MIGRATION_GUIDE.md)

## Backward Compatibility

Old imports still work with deprecation warnings:

```python
# Old (still works)
from app.models.payment import Payment
from app.services.payment_service import PaymentService

# New (recommended)
from app.modules.payments import Payment, PaymentService
```

Backward compatibility will be maintained until v2.0.

---

**Version**: 1.0
**Status**: 4/4 Modules Complete
**Last Updated**: May 2, 2026
