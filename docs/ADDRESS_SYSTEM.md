# Address System Documentation

## Overview

The GlycoGrit platform has a unified address system that provides:
- **Standardized schemas** for all address operations
- **Auto-fill functionality** using Shiprocket PIN code lookup
- **Address validation** and normalization
- **Serviceability checks** before order creation

---

## Architecture

### Core Components

1. **Unified Address Schemas** (`app/core/schemas/address.py`)
   - `AddressBase`: Base schema with required fields
   - `ShippingAddressCreate`: For creating shipping addresses
   - `ShippingAddressUpdate`: For updating addresses (all fields optional)
   - `ShippingAddressResponse`: For API responses
   - `UserProfileAddress`: Simplified address for user profiles
   - `PincodeDetails`: PIN code lookup response
   - `AddressAutoFillResponse`: Auto-fill response

2. **Address Service** (`app/core/services/address_service.py`)
   - PIN code lookup via Shiprocket
   - Address auto-fill
   - Address normalization
   - Serviceability checks
   - Legacy address conversion

3. **Address API** (`app/modules/common/api/address.py`)
   - `GET /api/address/pincode/{pincode}` - Lookup PIN code details
   - `GET /api/address/auto-fill/{pincode}` - Auto-fill city/state
   - `GET /api/address/serviceability/{pincode}` - Check delivery availability

---

## Field Standardization

### Standardized Field Names

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `name` | `PersonNameStr` | Full recipient name | Min 2 chars, letters/spaces/hyphens only |
| `phone` | `IndianPhoneStr` | 10-digit Indian mobile | Exactly 10 digits |
| `address_line1` | `str` | Street address | Min 5, max 500 chars |
| `address_line2` | `str` (optional) | Apt/suite/floor | Max 500 chars |
| `city` | `str` | City name | Min 2, max 100 chars, auto-capitalized |
| `state` | `str` | State name | Min 2, max 100 chars, auto-capitalized |
| `pincode` | `IndianPinCodeStr` | 6-digit PIN code | Exactly 6 digits, cannot start with 0 |
| `country` | `str` | Country (default: India) | Max 100 chars |

### Legacy Field Mappings

Old field names are automatically converted:

| Legacy Field | New Field |
|-------------|-----------|
| `postal_code` | `pincode` |
| `shipping_postal_code` | `pincode` |
| `shipping_address_line1` | `address_line1` |
| `shipping_address_line2` | `address_line2` |
| `shipping_city` | `city` |
| `shipping_state` | `state` |
| `shipping_phone` | `phone` |
| `full_name` | `name` |

---

## Usage Examples

### 1. Address Auto-Fill (Frontend)

```typescript
// User enters PIN code
const pincode = "400001";

// Call auto-fill API
const response = await fetch(`/api/address/auto-fill/${pincode}`);
const data = await response.json();

// Auto-populate form fields
setCity(data.city);           // "Mumbai"
setState(data.state);         // "Maharashtra"
setIsServiceable(data.is_serviceable);  // true
```

### 2. Address Validation (Backend)

```python
from app.core.schemas.address import ShippingAddressCreate

# Pydantic automatically validates
address = ShippingAddressCreate(
    name="Rajesh Kumar",
    phone="9876543210",
    address_line1="123, MG Road",
    city="Mumbai",
    state="Maharashtra",
    pincode="400001"
)
```

### 3. Address Normalization

```python
from app.core.services.address_service import AddressService

service = AddressService(db)

# Normalize raw address data
raw_address = {
    "name": "  rajesh kumar  ",
    "phone": "+91-9876-543-210",
    "postal_code": "400001",  # Legacy field
    "city": "mumbai",
    "state": "MAHARASHTRA"
}

normalized = service.normalize_address(raw_address)
# Result:
# {
#     "name": "Rajesh Kumar",
#     "phone": "9876543210",
#     "pincode": "400001",
#     "city": "Mumbai",
#     "state": "Maharashtra"
# }
```

### 4. Legacy Address Conversion

```python
from app.core.services.address_service import AddressService

service = AddressService(db)

# Convert old registration format
legacy = {
    "shipping_address_line1": "123 MG Road",
    "shipping_city": "Mumbai",
    "shipping_state": "Maharashtra",
    "shipping_postal_code": "400001",
    "shipping_phone": "9876543210"
}

converted = service.convert_legacy_address(legacy)
# Result uses standard field names:
# {
#     "address_line1": "123 Mg Road",
#     "city": "Mumbai",
#     "state": "Maharashtra",
#     "pincode": "400001",
#     "phone": "9876543210"
# }
```

---

## Integration Points

### User Profile
- **Storage**: `users.city`, `users.state`, `users.pincode` (simplified)
- **Schema**: `UserProfileAddress`
- **Use Case**: Basic location info for user dashboard

### Event Registration
- **Storage**: `registrations.shipping_*` columns (detailed)
- **Schema**: Uses legacy field names (for backward compatibility)
- **Migration Path**: Use `AddressService.convert_legacy_address()` when processing

### Reward Fulfillment
- **Storage**: `user_rewards.shipping_details` (JSONB)
- **Schema**: `ShippingAddressCreate` / `ShippingAddressResponse`
- **Use Case**: Final shipping address for order creation

### Shiprocket Orders
- **Storage**: Passed as dict to Shiprocket API
- **Conversion**: `AddressService.normalize_address()` before API call
- **Validation**: Automatic via PIN code serviceability check

---

## API Documentation

### GET /api/address/pincode/{pincode}

**Description**: Look up PIN code details from Shiprocket

**Path Parameters**:
- `pincode` (string, required): 6-digit Indian PIN code

**Response** (`PincodeDetails`):
```json
{
  "pincode": "400001",
  "city": "Mumbai",
  "state": "Maharashtra",
  "state_code": "MH",
  "is_serviceable": true,
  "region": "West",
  "delivery_days": "3-5 days"
}
```

**Error Responses**:
- `404 Not Found`: PIN code not found or not serviceable
- `500 Internal Server Error`: Shiprocket API error

---

### GET /api/address/auto-fill/{pincode}

**Description**: Auto-fill city and state based on PIN code

**Path Parameters**:
- `pincode` (string, required): 6-digit Indian PIN code

**Response** (`AddressAutoFillResponse`):
```json
{
  "pincode": "400001",
  "city": "Mumbai",
  "state": "Maharashtra",
  "state_code": "MH",
  "is_serviceable": true,
  "suggested_address": "Mumbai, Maharashtra - 400001"
}
```

**Use Case**: Frontend address forms
1. User enters PIN code
2. Call this endpoint
3. Auto-populate city/state fields
4. Show serviceability status

---

### GET /api/address/serviceability/{pincode}

**Description**: Check if delivery is available to PIN code

**Path Parameters**:
- `pincode` (string, required): 6-digit Indian PIN code

**Query Parameters**:
- `weight` (float, optional): Package weight in kg (default: 0.5)

**Response**:
```json
{
  "is_serviceable": true,
  "pincode": "400001",
  "message": "Delivery available to pincode 400001"
}
```

---

## Validation Rules

### PIN Code Validation
- **Format**: Exactly 6 digits
- **First Digit**: Cannot be 0
- **Type**: `IndianPinCodeStr` (custom Pydantic type)
- **Example Valid**: `400001`, `110001`, `560001`
- **Example Invalid**: `04001` (leading zero), `4001` (too short), `40000A` (non-digit)

### Phone Validation
- **Format**: 10 digits
- **Leading Digits**: Can be 6, 7, 8, or 9
- **Type**: `IndianPhoneStr` (custom Pydantic type)
- **Cleaning**: Auto-removes spaces, hyphens, +91 prefix
- **Example Valid**: `9876543210`, `+91-9876543210`
- **Example Invalid**: `1234567890` (invalid leading digit)

### Name Validation
- **Format**: Letters, spaces, hyphens, apostrophes only
- **Min Length**: 2 characters
- **Type**: `PersonNameStr` (custom Pydantic type)
- **Example Valid**: `Rajesh Kumar`, `O'Neill`, `Mary-Jane`
- **Example Invalid**: `User123` (contains numbers), `@Raj` (special chars)

---

## Migration Guide

### For Existing Code

#### Step 1: Import Unified Schemas
```python
from app.core.schemas.address import (
    ShippingAddressCreate,
    ShippingAddressResponse,
    UserProfileAddress
)
```

#### Step 2: Replace Legacy Schemas
**Before**:
```python
class ShippingAddress(BaseModel):
    shipping_address_line1: str
    shipping_city: str
    shipping_postal_code: str
```

**After**:
```python
from app.core.schemas.address import ShippingAddressCreate
# Use ShippingAddressCreate directly
```

#### Step 3: Convert Legacy Data
```python
from app.core.services.address_service import AddressService

service = AddressService(db)
standardized_address = service.convert_legacy_address(legacy_address_dict)
```

---

## Best Practices

### 1. Always Use Unified Schemas
```python
# ✅ Good
from app.core.schemas.address import ShippingAddressCreate
address = ShippingAddressCreate(**address_data)

# ❌ Avoid
class CustomAddressSchema(BaseModel):
    postal_code: str  # Use pincode instead
```

### 2. Normalize Before Storage
```python
# ✅ Good
normalized = service.normalize_address(user_input)
reward.shipping_details = normalized

# ❌ Avoid
reward.shipping_details = user_input  # No normalization
```

### 3. Check Serviceability Early
```python
# ✅ Good
is_serviceable = await service.check_serviceability(pincode)
if not is_serviceable:
    raise HTTPException(400, "Delivery not available to this PIN code")

# ❌ Avoid creating orders without checking first
```

### 4. Use Auto-Fill in Forms
```python
# ✅ Good
# Frontend: When PIN code changes, fetch auto-fill data
onChange = async (pincode) => {
    const data = await fetch(`/api/address/auto-fill/${pincode}`);
    setCityAndState(data.city, data.state);
}

# ❌ Avoid making users type city/state manually
```

---

## Testing

### Unit Tests

```python
def test_address_normalization():
    service = AddressService(db)

    raw = {
        "name": "  rajesh  ",
        "phone": "+91-9876543210",
        "city": "mumbai"
    }

    normalized = service.normalize_address(raw)

    assert normalized["name"] == "Rajesh"
    assert normalized["phone"] == "9876543210"
    assert normalized["city"] == "Mumbai"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_pincode_lookup(client, db):
    response = await client.get("/api/address/pincode/400001")

    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Mumbai"
    assert data["state"] == "Maharashtra"
    assert data["is_serviceable"] is True
```

---

## Troubleshooting

### Issue: PIN Code Not Found
**Symptom**: 404 error from `/api/address/pincode/{pincode}`
**Cause**: PIN code doesn't exist in Shiprocket database
**Solution**: User should enter city/state manually

### Issue: Serviceability Returns False
**Symptom**: `is_serviceable: false` in response
**Cause**: Shiprocket doesn't deliver to that area
**Solution**: Show error to user, suggest alternative addresses

### Issue: Legacy Field Names in Response
**Symptom**: Response has `postal_code` instead of `pincode`
**Cause**: Using old schema/model
**Solution**: Use `ShippingAddressResponse` from unified schemas

### Issue: Phone Validation Fails
**Symptom**: "Phone must be 10 digits" error
**Cause**: Phone includes +91, spaces, or hyphens
**Solution**: Use `IndianPhoneStr` type - it auto-cleans input

---

## Future Enhancements

1. **Multiple Address Storage**: Allow users to save multiple shipping addresses
2. **Address Book**: User can select from saved addresses during checkout
3. **International Addresses**: Support for non-Indian addresses
4. **Address Verification**: Real-time verification using Google Maps API
5. **Geocoding**: Lat/long coordinates for precise location

---

## Related Documentation

- [Shiprocket API Documentation](https://apidocs.shiprocket.in/)
- [Core Validators](../app/core/validators.py)
- [Shipping Module](../app/modules/shipping/)
- [Rewards Module](../app/modules/rewards/)

---

**Last Updated**: 2026-06-09
**Version**: 1.0.0
**Maintainer**: Backend Team
