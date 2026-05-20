"""
Webhook Events Constants

Centralized constants for webhook event types from various payment gateways
and third-party services.
"""


class RazorpayEvents:
    """Razorpay webhook event types."""

    # Payment Events
    PAYMENT_AUTHORIZED = "payment.authorized"
    PAYMENT_CAPTURED = "payment.captured"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_PENDING = "payment.pending"

    # Order Events
    ORDER_PAID = "order.paid"

    # Refund Events
    REFUND_CREATED = "refund.created"
    REFUND_PROCESSED = "refund.processed"
    REFUND_FAILED = "refund.failed"
    REFUND_SPEED_CHANGED = "refund.speed_changed"

    # Dispute Events
    DISPUTE_CREATED = "dispute.created"
    DISPUTE_WON = "dispute.won"
    DISPUTE_LOST = "dispute.lost"
    DISPUTE_CLOSED = "dispute.closed"


class StripeEvents:
    """Stripe webhook event types."""

    # Payment Intent Events
    PAYMENT_INTENT_CREATED = "payment_intent.created"
    PAYMENT_INTENT_SUCCEEDED = "payment_intent.succeeded"
    PAYMENT_INTENT_FAILED = "payment_intent.failed"
    PAYMENT_INTENT_CANCELED = "payment_intent.canceled"

    # Charge Events
    CHARGE_SUCCEEDED = "charge.succeeded"
    CHARGE_FAILED = "charge.failed"
    CHARGE_REFUNDED = "charge.refunded"
    CHARGE_DISPUTED = "charge.dispute.created"

    # Checkout Events
    CHECKOUT_SESSION_COMPLETED = "checkout.session.completed"
    CHECKOUT_SESSION_EXPIRED = "checkout.session.expired"

    # Refund Events
    REFUND_CREATED = "charge.refund.created"
    REFUND_UPDATED = "charge.refund.updated"


class PayPalEvents:
    """PayPal webhook event types."""

    # Payment Events
    PAYMENT_CAPTURE_COMPLETED = "PAYMENT.CAPTURE.COMPLETED"
    PAYMENT_CAPTURE_DENIED = "PAYMENT.CAPTURE.DENIED"
    PAYMENT_CAPTURE_PENDING = "PAYMENT.CAPTURE.PENDING"
    PAYMENT_CAPTURE_REFUNDED = "PAYMENT.CAPTURE.REFUNDED"

    # Order Events
    CHECKOUT_ORDER_APPROVED = "CHECKOUT.ORDER.APPROVED"
    CHECKOUT_ORDER_COMPLETED = "CHECKOUT.ORDER.COMPLETED"


class StravaWebhookEvents:
    """Strava webhook event types."""

    # Activity Events
    CREATE_ACTIVITY = "create"
    UPDATE_ACTIVITY = "update"
    DELETE_ACTIVITY = "delete"

    # Athlete Events
    UPDATE_ATHLETE = "update"
    DEAUTHORIZE = "deauthorization"


class ShiprocketEvents:
    """Shiprocket webhook event types."""

    # Shipment Events
    SHIPMENT_CREATED = "SHIPMENT_CREATED"
    PICKUP_SCHEDULED = "PICKUP_SCHEDULED"
    PICKUP_COMPLETE = "PICKUP_COMPLETE"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RTO_INITIATED = "RTO_INITIATED"
    RTO_DELIVERED = "RTO_DELIVERED"
    LOST = "LOST"
    DAMAGED = "DAMAGED"


class WebhookEventTypes:
    """General webhook event type categories."""

    PAYMENT = "payment"
    REFUND = "refund"
    ORDER = "order"
    SHIPMENT = "shipment"
    ACTIVITY = "activity"
    USER = "user"
    DISPUTE = "dispute"


class WebhookStatus:
    """Webhook processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    RETRY = "retry"
    IGNORED = "ignored"
