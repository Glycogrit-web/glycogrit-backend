# Payment Integration - Implementation Guide

## Overview

This document describes the modular payment gateway integration implemented in GlycoGrit backend. The architecture is designed to be provider-agnostic, allowing easy integration of multiple payment providers (Razorpay, Stripe, PayPal, etc.) with minimal code changes.

## Key Features

✅ **Modular Architecture** - Easy to add new payment providers
✅ **Provider-Agnostic** - Switch between payment gateways without changing business logic
✅ **Payment Flow Control** - Events with physical rewards require payment before confirmation
✅ **E-Certificate Support** - Free registration for e-certificate-only events
✅ **Refund Management** - Full and partial refunds through payment gateways
✅ **Signature Verification** - Secure payment verification using gateway signatures
✅ **Backward Compatible** - Maintains support for existing Razorpay-specific endpoints

---

## Architecture

### 1. Payment Gateway Abstraction Layer

```
app/services/payment_gateway/
├── base.py                 # PaymentGatewayInterface (abstract base class)
├── razorpay_gateway.py     # Razorpay implementation
├── factory.py              # PaymentGatewayFactory for provider selection
└── __init__.py            # Package exports
```

**Key Components:**

- **`PaymentGatewayInterface`**: Abstract base class defining the contract for all payment gateways
- **`RazorpayGateway`**: Concrete implementation for Razorpay
- **`PaymentGatewayFactory`**: Factory pattern to create gateway instances
- **`get_payment_gateway()`**: Convenience function to get gateway instances

### 2. Database Schema Updates

**Events Table:**
```python
certificate_type: String(20) = 'e-certificate'  # e-certificate | physical
requires_payment: Boolean = False               # Payment requirement flag
```

**Payments Table:**
```python
# Generic gateway fields (provider-agnostic)
gateway_order_id: String(100)      # Gateway's order ID
gateway_payment_id: String(100)    # Gateway's payment ID
gateway_signature: String(255)     # Payment signature
gateway_name: String(50)           # Gateway name (razorpay, stripe, etc.)

# Razorpay-specific fields (backward compatibility)
razorpay_order_id: String(100)
razorpay_payment_id: String(100)
razorpay_signature: String(255)

# Refund tracking
refund_id: String(100)
refund_amount: Decimal(10, 2)
refund_status: String(50)          # pending, processed, failed
refunded_at: TIMESTAMP
```

---

## Payment Flow

### Flow 1: Event Registration with Payment Required

```
1. User registers for event (POST /api/v1/events/{id}/register)
   ↓
2. Registration created with status='pending' (if payment required)
   ↓
3. Frontend creates payment order (POST /api/v1/payments/order/create)
   {
     "registration_id": 123,
     "gateway": "razorpay"  // optional
   }
   ↓
4. Backend creates order through payment gateway
   Returns: { order_id, amount, currency, gateway, payment }
   ↓
5. Frontend opens gateway checkout with order_id
   ↓
6. User completes payment on gateway
   ↓
7. Frontend verifies payment (POST /api/v1/payments/verify)
   {
     "order_id": "order_123",
     "payment_id": "pay_456",
     "signature": "abc..."
   }
   ↓
8. Backend verifies signature and updates:
   - Payment status = 'completed'
   - Registration status = 'confirmed'
   ↓
9. User registration confirmed ✓
```

### Flow 2: E-Certificate Event (No Payment Required)

```
1. User registers for event
   ↓
2. Event has certificate_type='e-certificate' OR requires_payment=False
   ↓
3. Registration created with status='confirmed' immediately
   ↓
4. No payment flow needed ✓
```

### Flow 3: Refund Processing

```
1. User/Admin requests refund (POST /api/v1/payments/{id}/refund)
   {
     "amount": null,  // null = full refund
     "reason": "Event cancelled"
   }
   ↓
2. Backend processes refund through payment gateway
   ↓
3. Updates:
   - Payment status = 'refunded'
   - Registration status = 'cancelled'
   ↓
4. Refund processed ✓
```

---

## API Endpoints

### Create Payment Order
```http
POST /api/v1/payments/order/create
Content-Type: application/json
Authorization: Bearer {token}

{
  "registration_id": 123,
  "gateway": "razorpay",  // Optional: defaults to configured gateway
  "notes": {
    "custom_field": "value"
  }
}

Response:
{
  "order_id": "order_MNhgJKL123456",
  "amount": 50000,  // In smallest unit (paise for INR)
  "currency": "INR",
  "gateway": "razorpay",
  "payment": { ... }
}
```

### Verify Payment
```http
POST /api/v1/payments/verify
Content-Type: application/json
Authorization: Bearer {token}

{
  "order_id": "order_MNhgJKL123456",
  "payment_id": "pay_MNhgJKL654321",
  "signature": "abc123...",
  "gateway": "razorpay"  // Optional
}

Response:
{
  "id": 1,
  "status": "completed",
  "amount": 500.00,
  ...
}
```

### Create Refund
```http
POST /api/v1/payments/{payment_id}/refund
Content-Type: application/json
Authorization: Bearer {token}

{
  "amount": null,  // null for full refund, or specific amount
  "reason": "Event cancelled",
  "notes": {
    "refund_reason": "user_request"
  }
}

Response:
{
  "id": 1,
  "status": "refunded",
  "refund_amount": 500.00,
  "refund_status": "processed",
  ...
}
```

---

## Configuration

### Environment Variables

```bash
# Payment Gateway Configuration
DEFAULT_PAYMENT_GATEWAY=razorpay  # Default gateway to use

# Razorpay
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_secret_key
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Stripe (Future)
# STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxx
# STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxx
# STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

### Database Migrations

```bash
# Apply migrations
alembic upgrade head

# Migrations included:
# 1. add_certificate_type_and_payment_requirement_to_events
# 2. add_razorpay_fields_to_payments
# 3. add_generic_gateway_fields_to_payments
```

---

## Adding a New Payment Gateway

### Step 1: Create Gateway Implementation

Create `app/services/payment_gateway/stripe_gateway.py`:

```python
from app.services.payment_gateway.base import PaymentGatewayInterface

class StripeGateway(PaymentGatewayInterface):
    def __init__(self):
        # Initialize Stripe client
        pass

    def get_gateway_name(self) -> str:
        return "stripe"

    def create_order(self, amount, currency, receipt, notes):
        # Implement Stripe payment intent creation
        pass

    def verify_payment_signature(self, order_id, payment_id, signature):
        # Implement Stripe signature verification
        pass

    # Implement other required methods...
```

### Step 2: Register in Factory

Update `app/services/payment_gateway/factory.py`:

```python
if provider == 'stripe':
    from app.services.payment_gateway.stripe_gateway import StripeGateway
    gateway = StripeGateway()
    cls._instances[provider] = gateway
    return gateway
```

### Step 3: Add Configuration

Update `app/core/config.py`:

```python
# Stripe Configuration
STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
```

### Step 4: Test

```python
# Use Stripe gateway
from app.services.payment_gateway import get_payment_gateway

gateway = get_payment_gateway('stripe')
order = gateway.create_order(amount=Decimal("500"), currency="INR")
```

---

## Event Configuration

### Events with Physical Rewards (Medals, Physical Certificates)

```python
{
  "name": "Mumbai Marathon 2024",
  "registration_fee": 500.00,
  "certificate_type": "physical",    # or set requires_payment=True
  "rewards": ["Medal", "Certificate", "T-shirt"]
}
```

**Behavior:**
- Registration status: `pending` until payment completed
- Payment required before confirmation
- Participant count updated after payment

### Events with E-Certificates Only

```python
{
  "name": "Virtual 5K Challenge",
  "registration_fee": 0,
  "certificate_type": "e-certificate",
  "requires_payment": False,
  "rewards": ["E-Certificate"]
}
```

**Behavior:**
- Registration status: `confirmed` immediately
- No payment required
- Participant count updated on registration

---

## Testing

### Test Payment Flow

```python
# 1. Create registration
POST /api/v1/events/1/register
{
  "participant_name": "John Doe",
  "age": 30
}

# 2. Create payment order
POST /api/v1/payments/order/create
{
  "registration_id": 1,
  "gateway": "razorpay"
}

# 3. Use Razorpay test credentials
# Test Card: 4111 1111 1111 1111
# CVV: Any 3 digits
# Expiry: Any future date

# 4. Verify payment
POST /api/v1/payments/verify
{
  "order_id": "order_...",
  "payment_id": "pay_...",
  "signature": "..."
}
```

### Test Refund

```python
POST /api/v1/payments/1/refund
{
  "amount": null,  # Full refund
  "reason": "Testing refund flow"
}
```

---

## Security Considerations

1. **Signature Verification**: All payments are verified using gateway-specific signatures
2. **Ownership Checks**: Users can only create/verify payments for their own registrations
3. **Rate Limiting**: API endpoints are rate-limited to prevent abuse
4. **Webhook Security**: Webhook signatures are verified before processing
5. **Environment Secrets**: All API keys stored in environment variables (Doppler)

---

## Backward Compatibility

### Deprecated Endpoints (Still Working)

```http
# Old Razorpay-specific endpoints (marked as deprecated)
POST /api/v1/payments/razorpay/create-order
POST /api/v1/payments/razorpay/verify

# New generic endpoints (recommended)
POST /api/v1/payments/order/create
POST /api/v1/payments/verify
```

### Migration Path

1. Frontend should start using new generic endpoints
2. Old endpoints will continue working for 6 months
3. Gradual migration of existing code
4. Remove deprecated endpoints in future release

---

## Frontend Integration Example

### React/Vue Example

```javascript
// 1. Create payment order
const createPaymentOrder = async (registrationId) => {
  const response = await fetch('/api/v1/payments/order/create', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      registration_id: registrationId,
      gateway: 'razorpay'  // or let backend use default
    })
  });

  const { order_id, amount, currency, gateway } = await response.json();

  // 2. Open Razorpay checkout
  if (gateway === 'razorpay') {
    const options = {
      key: RAZORPAY_KEY_ID,
      amount: amount,
      currency: currency,
      order_id: order_id,
      handler: async function (response) {
        // 3. Verify payment
        await verifyPayment(
          response.razorpay_order_id,
          response.razorpay_payment_id,
          response.razorpay_signature
        );
      }
    };
    const rzp = new Razorpay(options);
    rzp.open();
  }
};

// 3. Verify payment
const verifyPayment = async (orderId, paymentId, signature) => {
  const response = await fetch('/api/v1/payments/verify', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      order_id: orderId,
      payment_id: paymentId,
      signature: signature,
      gateway: 'razorpay'
    })
  });

  if (response.ok) {
    // Payment successful! Registration confirmed
    showSuccess('Payment successful! Registration confirmed.');
  }
};
```

---

## Troubleshooting

### Issue: Payment verification fails

**Solution:**
- Check that Razorpay webhook secret is correct
- Verify signature is being passed correctly from frontend
- Check logs for signature mismatch errors

### Issue: Registration not confirming after payment

**Solution:**
- Verify payment status is being updated to 'completed'
- Check registration service is updating status correctly
- Review database transaction logs

### Issue: Refund not processing

**Solution:**
- Ensure payment is in 'completed' status
- Verify gateway API credentials are correct
- Check payment has `gateway_payment_id` populated

---

## Future Enhancements

- [ ] Webhook endpoint for async payment updates
- [ ] Partial refund UI in admin panel
- [ ] Payment analytics dashboard
- [ ] Multiple currency support
- [ ] Stripe gateway implementation
- [ ] PayPal gateway implementation
- [ ] Subscription/recurring payments
- [ ] Payment installments

---

## Support

For questions or issues:
- Backend Issues: Check logs in `/logs` directory
- Payment Gateway Issues: Refer to gateway documentation (Razorpay, Stripe, etc.)
- Configuration: Review `.env.example` for required variables

---

**Last Updated:** April 21, 2026
**Version:** 1.0.0
**Author:** GlycoGrit Team
