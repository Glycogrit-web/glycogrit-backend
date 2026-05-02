# Module Exports Index

Complete index of all exports from each module for easy reference.

---

## 📦 Payments Module

**Import**: `from app.modules.payments import ...`

### Domain Models
- `Payment` - Payment ORM model

### Domain Entities
- `PaymentEntity` - Payment business rules (15+ rules)

### Value Objects
- `Money` - Currency handling and conversion
- `GatewayOrderId` - Payment gateway order ID validation
- `RefundAmount` - Refund amount calculation and validation

### Services
- `PaymentService` - Main payment orchestration service

### Repositories
- `PaymentRepository` - Payment data access layer

### Commands (Write Operations)
- `CreatePaymentOrderCommand` - Create new payment order
- `VerifyPaymentCommand` - Verify payment signature
- `ProcessRefundCommand` - Process payment refund
- `UpdatePaymentStatusCommand` - Update payment status
- `CancelPaymentCommand` - Cancel pending payment

### Queries (Read Operations)
- `GetPaymentByIdQuery` - Get payment by ID
- `GetPaymentByOrderIdQuery` - Get payment by order ID
- `GetUserPaymentsQuery` - Get all payments for a user
- `GetRegistrationPaymentsQuery` - Get payments for registration
- `GetPaymentHistoryQuery` - Get payment history with filters
- `GetPendingPaymentsQuery` - Get pending payments

---

## 📦 Shipping Module

**Import**: `from app.modules.shipping import ...`

### Domain Models
- `ShiprocketOrder` - Shipment ORM model
- `ShiprocketOrderStatus` - Shipment status ORM model
- `ShiprocketConfig` - Shiprocket configuration model

### Domain Entities
- `ShipmentEntity` - Shipment business rules (20+ rules)

### Value Objects
- `TrackingNumber` - Tracking number validation
- `ShippingAddress` - Complete address with validation
- `AWBNumber` - Air Waybill number validation
- `PickupSchedule` - Pickup scheduling info
- `PackageDimensions` - Package dimensions validation

### Services
- `ShippingService` - Main shipping orchestration service

### Repositories
- `ShipmentRepository` - Shipment data access layer

### Commands (Write Operations)
- `CreateShipmentCommand` - Create new shipment
- `RetryShipmentCommand` - Retry failed shipment
- `CancelShipmentCommand` - Cancel shipment
- `SchedulePickupCommand` - Schedule shipment pickup
- `GenerateManifestCommand` - Generate shipment manifest

### Queries (Read Operations)
- `GetShipmentByIdQuery` - Get shipment by ID
- `GetShipmentByUserRewardQuery` - Get shipment by user reward
- `GetUserShipmentsQuery` - Get all shipments for user
- `GetEventShipmentsQuery` - Get all shipments for event
- `TrackShipmentQuery` - Get tracking information
- `GetStaleShipmentsQuery` - Get stale/old shipments
- `GetShipmentsByStatusQuery` - Get shipments by status

---

## 📦 Registrations Module

**Import**: `from app.modules.registrations import ...`

### Domain Models
- `Registration` - Registration ORM model
- `EventRegistrationTier` - Event tier ORM model
- `RegistrationTier` - Registration-tier junction model

### Domain Entities
- `RegistrationEntity` - Registration business rules (25+ rules)
- `TierEntity` - Tier business rules (15+ rules)

### Value Objects
- `RegistrationNumber` - Registration number (EVT{id}-{code})
- `BibNumber` - Bib/race number validation
- `ParticipantDetails` - Participant personal info
- `UpgradePrice` - Tier upgrade price calculation
- `TierCapacity` - Tier capacity tracking

### Services
- `RegistrationService` - Main registration orchestration service

### Repositories
- `RegistrationRepository` - Registration data access layer

### Commands (Write Operations)
- `RegisterForEventCommand` - Register for non-tier event
- `RegisterForTierCommand` - Register for tier-based event
- `UpgradeTierCommand` - Upgrade to higher tier
- `CancelRegistrationCommand` - Cancel registration
- `ConfirmRegistrationCommand` - Confirm pending registration
- `UpdateRegistrationCommand` - Update participant details
- `AssignBibNumberCommand` - Assign bib number to registration
- `BulkAssignBibNumbersCommand` - Bulk assign bib numbers

### Queries (Read Operations)
- `GetRegistrationByIdQuery` - Get registration by ID
- `GetRegistrationByNumberQuery` - Get by registration number
- `GetUserRegistrationsQuery` - Get user's registrations
- `GetEventRegistrationsQuery` - Get event registrations
- `GetEventRegistrationsWithProgressQuery` - Get with activity progress
- `GetUserRegistrationForEventQuery` - Check if user registered
- `GetTierHistoryQuery` - Get tier upgrade history
- `GetStaleRegistrationsQuery` - Get stale pending registrations
- `GetRegistrationsByStatusQuery` - Get registrations by status
- `GetTierRegistrationCountQuery` - Get count for tier
- `GetEventTierStatisticsQuery` - Get tier statistics
- `SearchRegistrationsQuery` - Search registrations

---

## 📦 Events Module

**Import**: `from app.modules.events import ...`

### Domain Models
- `Event` - Event ORM model
- `EventActivity` - Event activity ORM model

### Domain Entities
- `EventEntity` - Event business rules (30+ rules)
- `ActivityEntity` - Activity business rules (8+ rules)

### Value Objects
- `EventSlug` - URL-friendly event identifier
- `EventLocation` - Complete location with validation
- `RegistrationPeriod` - Registration date range
- `EventCapacity` - Event capacity tracking
- `EventDateRange` - Event date range validation

### Services
- `EventService` - Main event orchestration service

### Repositories
- `EventRepository` - Event data access layer
- `EventActivityRepository` - Event activity data access layer

### Commands (Write Operations)
- `CreateEventCommand` - Create new event
- `UpdateEventCommand` - Update event details
- `PublishEventCommand` - Publish draft event
- `CancelEventCommand` - Cancel event
- `DeleteEventCommand` - Delete event
- `CreateActivityCommand` - Create event activity
- `UpdateActivityCommand` - Update activity details
- `DeleteActivityCommand` - Delete activity

### Queries (Read Operations)
- `GetEventByIdQuery` - Get event by ID
- `GetEventBySlugQuery` - Get event by slug
- `ListEventsQuery` - List events with filters
- `GetUpcomingEventsQuery` - Get upcoming events
- `GetFeaturedEventsQuery` - Get featured events
- `GetEventsByOrganizerQuery` - Get organizer's events
- `GetEventActivitiesQuery` - Get event activities
- `GetActivityByIdQuery` - Get activity by ID
- `SearchEventsQuery` - Search events by keyword
- `GetEventsRequiringStatusUpdateQuery` - Get events needing status update
- `GetEventStatisticsQuery` - Get event statistics

---

## 📊 Summary Statistics

### Total Exports by Category

| Category | Count |
|----------|-------|
| **Domain Models** | 8 |
| **Domain Entities** | 8 |
| **Value Objects** | 19 |
| **Services** | 5 |
| **Repositories** | 6 |
| **Commands** | 28 |
| **Queries** | 42 |
| **TOTAL** | **116** |

### Exports by Module

| Module | Total Exports |
|--------|---------------|
| Payments | 15 |
| Shipping | 19 |
| Registrations | 32 |
| Events | 30 |
| **TOTAL** | **96** |

---

## 🔍 Quick Search

### By Functionality

**Payment Related:**
- Payment processing: `PaymentService`, `CreatePaymentOrderCommand`
- Payment verification: `VerifyPaymentCommand`
- Refunds: `ProcessRefundCommand`, `RefundAmount`
- Payment history: `GetUserPaymentsQuery`, `GetPaymentHistoryQuery`

**Shipping Related:**
- Shipment creation: `ShippingService`, `CreateShipmentCommand`
- Tracking: `TrackingNumber`, `TrackShipmentQuery`
- Address validation: `ShippingAddress`
- Retry logic: `RetryShipmentCommand`

**Registration Related:**
- User registration: `RegistrationService`, `RegisterForTierCommand`
- Tier management: `TierEntity`, `UpgradeTierCommand`
- Bib assignment: `AssignBibNumberCommand`
- Capacity tracking: `TierCapacity`

**Event Related:**
- Event creation: `EventService`, `CreateEventCommand`
- Event lifecycle: `EventEntity`, `PublishEventCommand`
- Activities: `EventActivity`, `CreateActivityCommand`
- Registration periods: `RegistrationPeriod`

### By Type

**Validation:**
- `Money`, `ShippingAddress`, `RegistrationNumber`, `BibNumber`
- `EventSlug`, `EventLocation`, `TrackingNumber`, `AWBNumber`

**Business Rules:**
- `PaymentEntity`, `ShipmentEntity`, `RegistrationEntity`
- `TierEntity`, `EventEntity`, `ActivityEntity`

**Write Operations:**
- All `*Command` classes (28 total)

**Read Operations:**
- All `*Query` classes (42 total)

---

## 📖 Usage Examples

### Import Multiple Items
```python
from app.modules.payments import (
    Payment,
    PaymentEntity,
    Money,
    PaymentService,
    CreatePaymentOrderCommand,
    GetUserPaymentsQuery
)
```

### Import All Entity Rules
```python
from app.modules.registrations import (
    RegistrationEntity,
    TierEntity
)

registration_entity = RegistrationEntity(registration)
tier_entity = TierEntity(tier)
```

### Import All Value Objects for a Module
```python
from app.modules.shipping import (
    TrackingNumber,
    ShippingAddress,
    AWBNumber,
    PickupSchedule,
    PackageDimensions
)
```

---

## 🔗 Related Documentation

- **Quick Reference**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Architecture Guide**: [MODULAR_ARCHITECTURE.md](MODULAR_ARCHITECTURE.md)
- **Migration Guide**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

---

**Version**: 1.0
**Last Updated**: May 2, 2026
**Total Exports**: 116 items across 4 modules
