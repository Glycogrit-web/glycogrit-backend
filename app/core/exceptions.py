"""
Custom exception classes for the GlycoGrit backend.

These exceptions provide consistent error handling across the application
with appropriate HTTP status codes and detailed error context.
"""

from typing import Any


class AppException(Exception):
    """Base application exception that all custom exceptions inherit from."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str | None = None,
        details: dict[str, Any] | None = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    """Raised when a requested resource is not found (HTTP 404)."""

    def __init__(self, resource: str, identifier: Any):
        message = f"{resource} with id '{identifier}' not found"
        super().__init__(
            message,
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "identifier": str(identifier)}
        )
        self.resource = resource
        self.identifier = identifier


class PermissionDeniedException(AppException):
    """Raised when a user lacks permission to perform an action (HTTP 403)."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
        resource: str | None = None
    ):
        super().__init__(
            message,
            status_code=403,
            error_code="PERMISSION_DENIED",
            details={"resource": resource} if resource else {}
        )


class AlreadyExistsException(AppException):
    """Raised when attempting to create a resource that already exists (HTTP 409)."""

    def __init__(self, resource: str, field: str, value: Any):
        message = f"{resource} with {field} '{value}' already exists"
        super().__init__(
            message,
            status_code=409,
            error_code="RESOURCE_ALREADY_EXISTS",
            details={"resource": resource, "field": field, "value": str(value)}
        )
        self.resource = resource
        self.field = field
        self.value = value


class ValidationException(AppException):
    """Raised when input validation fails (HTTP 400)."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        validation_errors: dict[str, Any] | None = None
    ):
        details = {}
        if field:
            details["field"] = field
        if validation_errors:
            details["validation_errors"] = validation_errors

        super().__init__(
            message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details
        )
        self.field = field
        self.validation_errors = validation_errors


class DatabaseException(AppException):
    """Raised when a database operation fails (HTTP 500)."""

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: str | None = None
    ):
        super().__init__(
            message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details={"operation": operation} if operation else {}
        )


class AuthenticationException(AppException):
    """Raised when authentication fails (HTTP 401)."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message,
            status_code=401,
            error_code="AUTHENTICATION_FAILED"
        )


# ==================== Payment-Specific Exceptions ====================

class PaymentException(AppException):
    """Base exception for payment-related errors."""

    def __init__(
        self,
        message: str,
        payment_id: int | None = None,
        order_id: str | None = None,
        details: dict[str, Any] | None = None
    ):
        exc_details = details or {}
        if payment_id:
            exc_details["payment_id"] = payment_id
        if order_id:
            exc_details["order_id"] = order_id

        super().__init__(
            message,
            status_code=400,
            error_code="PAYMENT_ERROR",
            details=exc_details
        )


class PaymentVerificationException(PaymentException):
    """Raised when payment signature verification fails."""

    def __init__(
        self,
        message: str = "Payment signature verification failed",
        order_id: str | None = None,
        payment_id: str | None = None
    ):
        super().__init__(
            message,
            order_id=order_id,
            details={"gateway_payment_id": payment_id} if payment_id else None
        )
        self.message = message
        self.status_code = 400
        self.error_code = "PAYMENT_VERIFICATION_FAILED"


class PaymentAlreadyCompletedException(PaymentException):
    """Raised when attempting to process a payment that's already completed."""

    def __init__(self, payment_id: int, registration_id: int):
        super().__init__(
            f"Payment already completed for registration {registration_id}",
            payment_id=payment_id,
            details={"registration_id": registration_id}
        )
        self.status_code = 409
        self.error_code = "PAYMENT_ALREADY_COMPLETED"


class PaymentPendingException(PaymentException):
    """Raised when a payment is pending and another action requires completion."""

    def __init__(
        self,
        message: str = "Payment is pending completion",
        payment_id: int | None = None,
        order_id: str | None = None
    ):
        super().__init__(message, payment_id=payment_id, order_id=order_id)
        self.status_code = 409
        self.error_code = "PAYMENT_PENDING"


class RefundException(PaymentException):
    """Raised when refund operation fails."""

    def __init__(
        self,
        message: str,
        payment_id: int | None = None,
        reason: str | None = None
    ):
        super().__init__(
            message,
            payment_id=payment_id,
            details={"reason": reason} if reason else None
        )
        self.error_code = "REFUND_ERROR"


class PaymentGatewayException(PaymentException):
    """Raised when payment gateway API fails."""

    def __init__(
        self,
        message: str,
        gateway: str,
        gateway_error: str | None = None,
        is_retryable: bool = False
    ):
        super().__init__(
            message,
            details={
                "gateway": gateway,
                "gateway_error": gateway_error,
                "is_retryable": is_retryable
            }
        )
        self.status_code = 502
        self.error_code = "PAYMENT_GATEWAY_ERROR"
        self.is_retryable = is_retryable


# ==================== Registration-Specific Exceptions ====================

class RegistrationException(AppException):
    """Base exception for registration-related errors."""

    def __init__(
        self,
        message: str,
        registration_id: int | None = None,
        event_id: int | None = None,
        details: dict[str, Any] | None = None
    ):
        exc_details = details or {}
        if registration_id:
            exc_details["registration_id"] = registration_id
        if event_id:
            exc_details["event_id"] = event_id

        super().__init__(
            message,
            status_code=400,
            error_code="REGISTRATION_ERROR",
            details=exc_details
        )


class EventFullException(RegistrationException):
    """Raised when attempting to register for a sold-out event."""

    def __init__(
        self,
        event_id: int,
        current_count: int,
        max_capacity: int
    ):
        super().__init__(
            f"Event is sold out. {current_count}/{max_capacity} spots filled.",
            event_id=event_id,
            details={
                "current_participants": current_count,
                "max_participants": max_capacity
            }
        )
        self.status_code = 409
        self.error_code = "EVENT_FULL"


class EventNotOpenException(RegistrationException):
    """Raised when attempting to register for an event that's not open."""

    def __init__(self, event_id: int, event_status: str):
        super().__init__(
            f"Event is not open for registration. Current status: {event_status}",
            event_id=event_id,
            details={"event_status": event_status}
        )
        self.error_code = "EVENT_NOT_OPEN"


class DuplicateRegistrationException(RegistrationException):
    """Raised when user attempts duplicate registration."""

    def __init__(
        self,
        user_id: int,
        event_id: int,
        existing_registration_id: int,
        registration_status: str
    ):
        super().__init__(
            f"User already registered for this event (status: {registration_status})",
            registration_id=existing_registration_id,
            event_id=event_id,
            details={
                "user_id": user_id,
                "existing_status": registration_status
            }
        )
        self.status_code = 409
        self.error_code = "DUPLICATE_REGISTRATION"


# ==================== Tier-Specific Exceptions ====================

class TierException(AppException):
    """Base exception for tier-related errors."""

    def __init__(
        self,
        message: str,
        tier_id: int | None = None,
        details: dict[str, Any] | None = None
    ):
        exc_details = details or {}
        if tier_id:
            exc_details["tier_id"] = tier_id

        super().__init__(
            message,
            status_code=400,
            error_code="TIER_ERROR",
            details=exc_details
        )


class TierSoldOutException(TierException):
    """Raised when attempting to register for a sold-out tier."""

    def __init__(
        self,
        tier_id: int,
        tier_name: str,
        current_count: int,
        max_capacity: int
    ):
        super().__init__(
            f"Tier '{tier_name}' is sold out. {current_count}/{max_capacity} spots filled.",
            tier_id=tier_id,
            details={
                "tier_name": tier_name,
                "current_registrations": current_count,
                "max_registrations": max_capacity
            }
        )
        self.status_code = 409
        self.error_code = "TIER_SOLD_OUT"


class TierInactiveException(TierException):
    """Raised when attempting to use an inactive tier."""

    def __init__(self, tier_id: int, tier_name: str):
        super().__init__(
            f"Tier '{tier_name}' is not currently active",
            tier_id=tier_id,
            details={"tier_name": tier_name}
        )
        self.error_code = "TIER_INACTIVE"


class InvalidTierUpgradeException(TierException):
    """Raised when tier upgrade validation fails."""

    def __init__(
        self,
        message: str,
        current_tier_id: int,
        new_tier_id: int,
        reason: str
    ):
        super().__init__(
            message,
            details={
                "current_tier_id": current_tier_id,
                "new_tier_id": new_tier_id,
                "reason": reason
            }
        )
        self.error_code = "INVALID_TIER_UPGRADE"


# ==================== Race Condition / Concurrency Exceptions ====================

class ConcurrencyException(AppException):
    """Raised when a race condition or concurrent modification is detected."""

    def __init__(
        self,
        message: str,
        resource: str,
        resource_id: int | None = None
    ):
        super().__init__(
            message,
            status_code=409,
            error_code="CONCURRENCY_ERROR",
            details={
                "resource": resource,
                "resource_id": resource_id
            }
        )


class CapacityRaceConditionException(ConcurrencyException):
    """Raised when capacity check fails due to concurrent registrations."""

    def __init__(self, resource: str, resource_id: int):
        super().__init__(
            f"{resource} capacity reached due to concurrent registrations. Please try again.",
            resource=resource,
            resource_id=resource_id
        )
        self.error_code = "CAPACITY_RACE_CONDITION"


# ==================== External Service Exceptions ====================

class ExternalServiceException(AppException):
    """Raised when external service call fails."""

    def __init__(
        self,
        message: str,
        service_name: str,
        is_retryable: bool = True,
        details: dict[str, Any] | None = None
    ):
        exc_details = details or {}
        exc_details["service_name"] = service_name
        exc_details["is_retryable"] = is_retryable

        super().__init__(
            message,
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=exc_details
        )
        self.is_retryable = is_retryable


class ShippingServiceException(ExternalServiceException):
    """Raised when shipping service (Shiprocket) fails."""

    def __init__(
        self,
        message: str,
        operation: str,
        is_retryable: bool = True
    ):
        super().__init__(
            message,
            service_name="Shiprocket",
            is_retryable=is_retryable,
            details={"operation": operation}
        )
        self.error_code = "SHIPPING_SERVICE_ERROR"


# ==================== Idempotency Exceptions ====================

class IdempotencyException(AppException):
    """Raised when idempotency key conflicts are detected."""

    def __init__(
        self,
        message: str = "Duplicate request detected",
        idempotency_key: str | None = None
    ):
        super().__init__(
            message,
            status_code=409,
            error_code="IDEMPOTENCY_CONFLICT",
            details={"idempotency_key": idempotency_key} if idempotency_key else {}
        )


# ==================== Business Logic Exceptions ====================

class BusinessLogicException(AppException):
    """Raised when business logic validation fails."""

    def __init__(
        self,
        message: str,
        rule: str,
        details: dict[str, Any] | None = None
    ):
        exc_details = details or {}
        exc_details["violated_rule"] = rule

        super().__init__(
            message,
            status_code=422,
            error_code="BUSINESS_LOGIC_ERROR",
            details=exc_details
        )


class InsufficientFundsException(BusinessLogicException):
    """Raised when payment amount is insufficient."""

    def __init__(self, required_amount: float, provided_amount: float):
        super().__init__(
            f"Insufficient payment amount. Required: {required_amount}, Provided: {provided_amount}",
            rule="payment_amount_validation",
            details={
                "required_amount": required_amount,
                "provided_amount": provided_amount,
                "shortfall": required_amount - provided_amount
            }
        )
        self.error_code = "INSUFFICIENT_FUNDS"


class InvalidStateTransitionException(BusinessLogicException):
    """Raised when attempting invalid state transition."""

    def __init__(
        self,
        resource: str,
        current_state: str,
        attempted_state: str
    ):
        super().__init__(
            f"Cannot transition {resource} from '{current_state}' to '{attempted_state}'",
            rule="state_transition_validation",
            details={
                "resource": resource,
                "current_state": current_state,
                "attempted_state": attempted_state
            }
        )
        self.error_code = "INVALID_STATE_TRANSITION"
