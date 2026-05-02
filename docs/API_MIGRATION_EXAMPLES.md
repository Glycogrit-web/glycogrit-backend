# API Route Migration Examples

Practical examples of migrating API routes to use the new modular architecture.

---

## 📋 Overview

This guide shows real-world examples of migrating FastAPI route handlers from the old structure to the new modular architecture.

**Key Changes**:
1. Update imports to use new modules
2. Use entities for business logic
3. Use value objects for validation
4. (Optional) Use CQRS commands/queries

---

## 🔄 Payment Routes Migration

### Example 1: Create Payment Order

**Before (Old Structure)**:
```python
# app/api/payments.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.payment import Payment
from app.services.payment_service import PaymentService
from app.core.database import get_db
from app.schemas.payment import PaymentOrderCreate, PaymentOrderResponse

router = APIRouter()

@router.post("/payments/create-order", response_model=PaymentOrderResponse)
def create_payment_order(
    data: PaymentOrderCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Business logic in API route
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    service = PaymentService(db)
    try:
        order = service.create_payment_order(
            registration_id=data.registration_id,
            user_id=current_user.id,
            amount=data.amount,
            currency=data.currency or "INR"
        )
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**After (New Modular Structure)**:
```python
# app/api/payments.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from app.modules.payments import (
    Payment,
    PaymentService,
    Money,  # NEW: Value object
    CreatePaymentOrderCommand  # NEW: CQRS
)
from app.core.database import get_db
from app.schemas.payment import PaymentOrderCreate, PaymentOrderResponse

router = APIRouter()

@router.post("/payments/create-order", response_model=PaymentOrderResponse)
def create_payment_order(
    data: PaymentOrderCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # NEW: Validate with value object
    try:
        money = Money.from_float(data.amount, data.currency or "INR")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # NEW: Create command object
    command = CreatePaymentOrderCommand(
        registration_id=data.registration_id,
        user_id=current_user.id,
        amount=money.amount,
        currency=money.currency
    )

    service = PaymentService(db)
    try:
        order = service.create_payment_order(command)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Example 2: Process Refund

**Before**:
```python
@router.post("/payments/{payment_id}/refund")
def process_refund(
    payment_id: int,
    refund_amount: float,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    service = PaymentService(db)
    payment = service.get_payment_by_id(payment_id)

    # Business logic in route
    if payment.status != "completed":
        raise HTTPException(status_code=400, detail="Cannot refund incomplete payment")

    if payment.refund_status == "processed":
        raise HTTPException(status_code=400, detail="Payment already refunded")

    if refund_amount > payment.amount:
        raise HTTPException(status_code=400, detail="Refund amount exceeds payment amount")

    result = service.process_refund(payment_id, refund_amount)
    return result
```

**After**:
```python
from app.modules.payments import PaymentEntity, RefundAmount, ProcessRefundCommand

@router.post("/payments/{payment_id}/refund")
def process_refund(
    payment_id: int,
    refund_amount: float,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    service = PaymentService(db)
    payment = service.get_payment_by_id(payment_id)

    # NEW: Business logic in entity
    payment_entity = PaymentEntity(payment)

    if not payment_entity.is_refundable:
        raise HTTPException(status_code=400, detail="Payment cannot be refunded")

    # NEW: Create and validate refund amount
    try:
        refund = RefundAmount(Decimal(str(refund_amount)), payment.currency)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # NEW: Validate refund amount with entity
    is_valid, error = payment_entity.validate_refund_amount(refund.amount)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # NEW: Use command
    command = ProcessRefundCommand(
        payment_id=payment_id,
        refund_amount=refund.amount
    )

    result = service.process_refund(command)
    return result
```

---

## 🚚 Shipping Routes Migration

### Example 3: Create Shipment

**Before**:
```python
# app/api/shipping.py
from app.services.shiprocket.reward_fulfillment_service import RewardFulfillmentService

@router.post("/shipments/create")
def create_shipment(
    data: ShipmentCreate,
    db: Session = Depends(get_db)
):
    # Manual address validation
    if not data.name or len(data.name) < 2:
        raise HTTPException(status_code=400, detail="Name too short")

    if not data.phone or len(data.phone) != 10:
        raise HTTPException(status_code=400, detail="Invalid phone")

    # Create address dict
    address_dict = {
        "name": data.name,
        "phone": data.phone,
        "address": data.address,
        "city": data.city,
        "state": data.state,
        "pincode": data.pincode
    }

    service = RewardFulfillmentService(db)
    shipment = service.fulfill_reward(
        user_reward_id=data.user_reward_id,
        shipping_address=address_dict,
        product_details=data.product_details
    )
    return shipment
```

**After**:
```python
from app.modules.shipping import (
    ShippingService,
    ShippingAddress,  # NEW: Value object
    CreateShipmentCommand  # NEW: CQRS
)

@router.post("/shipments/create")
def create_shipment(
    data: ShipmentCreate,
    db: Session = Depends(get_db)
):
    # NEW: Validate with value object (automatic validation)
    try:
        address = ShippingAddress(
            name=data.name,
            phone=data.phone,
            address_line1=data.address,
            address_line2=data.address_line2,
            city=data.city,
            state=data.state,
            pincode=data.pincode
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # NEW: Use command
    command = CreateShipmentCommand(
        user_reward_id=data.user_reward_id,
        event_id=data.event_id,
        user_id=data.user_id,
        shipping_address=address.to_dict(),
        product_details=data.product_details
    )

    service = ShippingService(db)
    shipment = service.create_shipment(command)
    return shipment
```

### Example 4: Check Shipment Retry Eligibility

**Before**:
```python
@router.get("/shipments/{shipment_id}/can-retry")
def check_can_retry(shipment_id: int, db: Session = Depends(get_db)):
    shipment = db.query(ShiprocketOrder).filter(ShiprocketOrder.id == shipment_id).first()

    # Business logic in route
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    if shipment.status != "failed":
        return {"can_retry": False, "reason": "Shipment not in failed status"}

    if shipment.shiprocket_order_id:
        return {"can_retry": False, "reason": "Already created in Shiprocket"}

    from datetime import datetime, timedelta
    age = datetime.now() - shipment.created_at
    if age > timedelta(days=7):
        return {"can_retry": False, "reason": "Shipment too old"}

    return {"can_retry": True}
```

**After**:
```python
from app.modules.shipping import ShipmentEntity

@router.get("/shipments/{shipment_id}/can-retry")
def check_can_retry(shipment_id: int, db: Session = Depends(get_db)):
    shipment = db.query(ShiprocketOrder).filter(ShiprocketOrder.id == shipment_id).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # NEW: Business logic in entity
    shipment_entity = ShipmentEntity(shipment)

    can_retry = shipment_entity.can_retry
    reason = None if can_retry else "Cannot retry shipment"

    return {"can_retry": can_retry, "reason": reason}
```

---

## 📝 Registration Routes Migration

### Example 5: Register for Event Tier

**Before**:
```python
# app/api/registrations.py
from app.services.registration_service import RegistrationService

@router.post("/registrations/register-tier")
def register_for_tier(
    data: RegisterForTierRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Validation in route
    if not data.participant_name or len(data.participant_name) < 2:
        raise HTTPException(status_code=400, detail="Participant name too short")

    if data.age and (data.age < 0 or data.age > 150):
        raise HTTPException(status_code=400, detail="Invalid age")

    service = RegistrationService(db)
    result = service.register_for_event_tier(
        event_id=data.event_id,
        tier_id=data.tier_id,
        user_id=current_user.id,
        participant_name=data.participant_name,
        age=data.age,
        gender=data.gender,
        t_shirt_size=data.t_shirt_size
    )
    return result
```

**After**:
```python
from app.modules.registrations import (
    RegistrationService,
    ParticipantDetails,  # NEW: Value object
    RegisterForTierCommand  # NEW: CQRS
)

@router.post("/registrations/register-tier")
def register_for_tier(
    data: RegisterForTierRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # NEW: Validate with value object
    try:
        participant = ParticipantDetails(
            name=data.participant_name,
            age=data.age,
            gender=data.gender,
            t_shirt_size=data.t_shirt_size
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # NEW: Use command
    command = RegisterForTierCommand(
        user_id=current_user.id,
        event_id=data.event_id,
        tier_id=data.tier_id,
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
    return result
```

### Example 6: Check Tier Upgrade Eligibility

**Before**:
```python
@router.get("/registrations/{registration_id}/can-upgrade/{tier_id}")
def check_upgrade_eligibility(
    registration_id: int,
    tier_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    reg = db.query(Registration).filter(Registration.id == registration_id).first()
    new_tier = db.query(EventRegistrationTier).filter(EventRegistrationTier.id == tier_id).first()
    current_tier = reg.current_tier

    # Complex business logic in route
    if reg.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your registration")

    if not reg.uses_tier_system:
        return {"can_upgrade": False, "reason": "Event doesn't use tier system"}

    if new_tier.event_id != current_tier.event_id:
        return {"can_upgrade": False, "reason": "Tier doesn't belong to event"}

    if new_tier.tier_order <= current_tier.tier_order:
        return {"can_upgrade": False, "reason": "Can only upgrade to higher tier"}

    if not new_tier.is_active:
        return {"can_upgrade": False, "reason": "Tier is not active"}

    if new_tier.current_registrations >= new_tier.max_registrations:
        return {"can_upgrade": False, "reason": "Tier is sold out"}

    upgrade_price = new_tier.price - current_tier.price

    return {
        "can_upgrade": True,
        "upgrade_price": upgrade_price,
        "currency": new_tier.currency
    }
```

**After**:
```python
from app.modules.registrations import (
    RegistrationEntity,
    TierEntity,
    UpgradePrice
)

@router.get("/registrations/{registration_id}/can-upgrade/{tier_id}")
def check_upgrade_eligibility(
    registration_id: int,
    tier_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    reg = db.query(Registration).filter(Registration.id == registration_id).first()
    new_tier = db.query(EventRegistrationTier).filter(EventRegistrationTier.id == tier_id).first()

    if reg.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your registration")

    # NEW: Business logic in entity
    reg_entity = RegistrationEntity(reg)
    can_upgrade, reason = reg_entity.can_upgrade_to_tier(new_tier)

    if not can_upgrade:
        return {"can_upgrade": False, "reason": reason}

    # NEW: Calculate price with entity and value object
    upgrade_price_decimal = reg_entity.calculate_upgrade_price(new_tier)
    upgrade = UpgradePrice.calculate(
        from_tier_price=reg.current_tier.price,
        to_tier_price=new_tier.price,
        currency=new_tier.currency
    )

    return {
        "can_upgrade": True,
        "upgrade_price": float(upgrade.amount),
        "currency": upgrade.currency,
        "requires_payment": upgrade.requires_payment
    }
```

---

## 🎪 Event Routes Migration

### Example 7: Create Event

**Before**:
```python
# app/api/events.py
from app.services.event_service import EventService

@router.post("/events/create")
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Validation in route
    if not data.name or len(data.name) < 3:
        raise HTTPException(status_code=400, detail="Event name too short")

    # Manual slug generation
    slug = data.name.lower().replace(" ", "-")

    if data.registration_end_date <= data.registration_start_date:
        raise HTTPException(status_code=400, detail="Invalid registration dates")

    event_data = {
        "name": data.name,
        "slug": slug,
        "description": data.description,
        "event_date": data.event_date,
        ...
    }

    service = EventService(db)
    event = service.create_event(event_data, current_user.id)
    return event
```

**After**:
```python
from app.modules.events import (
    EventService,
    EventSlug,  # NEW: Value object
    EventLocation,  # NEW: Value object
    RegistrationPeriod,  # NEW: Value object
    CreateEventCommand  # NEW: CQRS
)

@router.post("/events/create")
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # NEW: Generate slug with value object
    try:
        slug = EventSlug.from_name(data.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # NEW: Validate location with value object
    try:
        location = EventLocation(
            location_name=data.location_name,
            city=data.city,
            state=data.state,
            country=data.country
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # NEW: Validate registration period
    try:
        reg_period = RegistrationPeriod(
            start_date=data.registration_start_date,
            end_date=data.registration_end_date
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # NEW: Use command
    command = CreateEventCommand(
        organizer_id=current_user.id,
        name=data.name,
        slug=slug.value,
        description=data.description,
        event_date=data.event_date,
        registration_start_date=reg_period.start_date,
        registration_end_date=reg_period.end_date,
        location_name=location.location_name,
        city=location.city,
        state=location.state,
        country=location.country,
        max_participants=data.max_participants
    )

    service = EventService(db)
    event = service.create_event(command.__dict__, command.organizer_id)
    return event
```

### Example 8: Check Event Registration Status

**Before**:
```python
@router.get("/events/{event_id}/can-register")
def check_can_register(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()

    # Business logic in route
    from datetime import datetime
    now = datetime.now()

    if event.status not in ['published', 'upcoming']:
        return {"can_register": False, "reason": "Event not open"}

    if now < event.registration_start_date:
        return {"can_register": False, "reason": "Registration not started"}

    if now > event.registration_end_date:
        return {"can_register": False, "reason": "Registration closed"}

    if event.max_participants and event.current_participants >= event.max_participants:
        return {"can_register": False, "reason": "Event full"}

    return {"can_register": True}
```

**After**:
```python
from app.modules.events import EventEntity

@router.get("/events/{event_id}/can-register")
def check_can_register(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()

    # NEW: Business logic in entity
    event_entity = EventEntity(event)
    can_accept, reason = event_entity.can_accept_registrations()

    # NEW: Additional helpful info
    response = {
        "can_register": can_accept,
        "reason": reason
    }

    if event_entity.is_registration_open:
        response["days_until_closes"] = event_entity.days_until_registration_closes

    if event_entity.has_capacity_limit:
        response["spots_remaining"] = event_entity.capacity_remaining
        response["is_nearly_full"] = event_entity.is_nearly_full()

    return response
```

---

## 📊 Summary of Benefits

### Code Reduction
- **Before**: 20-30 lines per route with validation/logic
- **After**: 10-15 lines per route (50% reduction)

### Error Handling
- **Before**: Manual validation, easy to miss cases
- **After**: Automatic validation via value objects

### Testability
- **Before**: Must test entire route with HTTP
- **After**: Test entities/value objects separately

### Maintainability
- **Before**: Business logic duplicated across routes
- **After**: Single source of truth in entities

---

## 🎯 Migration Checklist

For each API route:

- [ ] Update imports to new modules
- [ ] Extract validation to value objects
- [ ] Move business logic to entities
- [ ] Create command/query objects (optional)
- [ ] Simplify route handler
- [ ] Update tests
- [ ] Test manually

---

**Version**: 1.0
**Last Updated**: May 2, 2026
**Status**: Complete Examples
