"""
Error Messages Constants

Centralized constants for all error messages used throughout the application.
This ensures consistency in error messages and makes them easy to update.
"""


class ErrorMessages:
    """Standard error messages used across the application."""

    # Generic Errors
    INTERNAL_SERVER_ERROR = "An internal server error occurred"
    INVALID_REQUEST = "Invalid request"
    UNAUTHORIZED = "Not authorized"
    FORBIDDEN = "Access forbidden"
    BAD_REQUEST = "Bad request"

    # Authentication & Authorization
    INVALID_CREDENTIALS = "Invalid email or password"
    TOKEN_EXPIRED = "Authentication token has expired"
    TOKEN_INVALID = "Invalid authentication token"
    TOKEN_MISSING = "Authentication token is required"
    INSUFFICIENT_PERMISSIONS = "You do not have permission to perform this action"

    # Resource Not Found
    RESOURCE_NOT_FOUND = "{resource} not found"
    USER_NOT_FOUND = "User not found"
    EVENT_NOT_FOUND = "Event not found"
    REGISTRATION_NOT_FOUND = "Registration not found"
    ACTIVITY_NOT_FOUND = "Activity not found"
    CHALLENGE_NOT_FOUND = "Challenge not found"
    PAYMENT_NOT_FOUND = "Payment not found"
    CERTIFICATE_NOT_FOUND = "Certificate not found"
    REWARD_NOT_FOUND = "Reward not found"
    ORDER_NOT_FOUND = "Order not found"

    # Resource Already Exists
    RESOURCE_ALREADY_EXISTS = "{resource} already exists"
    USER_ALREADY_EXISTS = "User with this email already exists"
    EMAIL_ALREADY_REGISTERED = "Email is already registered"
    USERNAME_ALREADY_TAKEN = "Username is already taken"
    ALREADY_REGISTERED = "You are already registered for this event"

    # Validation Errors
    INVALID_EMAIL = "Invalid email format"
    INVALID_PASSWORD = "Password does not meet requirements"
    INVALID_PHONE_NUMBER = "Invalid phone number format"
    INVALID_DATE_FORMAT = "Invalid date format"
    INVALID_DATE_RANGE = "Invalid date range"
    FIELD_REQUIRED = "{field} is required"
    FIELD_INVALID = "Invalid {field}"
    FIELD_TOO_LONG = "{field} exceeds maximum length"
    FIELD_TOO_SHORT = "{field} is below minimum length"

    # Payment Errors
    PAYMENT_FAILED = "Payment processing failed"
    PAYMENT_ALREADY_PROCESSED = "Payment has already been processed"
    PAYMENT_EXPIRED = "Payment has expired"
    PAYMENT_CANCELLED = "Payment was cancelled"
    INVALID_PAYMENT_METHOD = "Invalid payment method"
    REFUND_FAILED = "Refund processing failed"
    INSUFFICIENT_FUNDS = "Insufficient funds"

    # Registration Errors
    REGISTRATION_CLOSED = "Registration is closed for this event"
    REGISTRATION_FULL = "Event registration is full"
    REGISTRATION_EXPIRED = "Registration has expired"
    REGISTRATION_CANCELLED = "Registration has been cancelled"
    INVALID_REGISTRATION_STATUS = "Invalid registration status"

    # Event Errors
    EVENT_NOT_PUBLISHED = "Event is not published"
    EVENT_ALREADY_STARTED = "Event has already started"
    EVENT_ENDED = "Event has ended"
    EVENT_CANCELLED = "Event has been cancelled"
    INVALID_EVENT_STATUS = "Invalid event status"
    EVENT_DATES_INVALID = "Event start date must be before end date"

    # Activity & Tracking Errors
    ACTIVITY_SYNC_FAILED = "Failed to sync activities from {provider}"
    TRACKER_NOT_CONNECTED = "{tracker} is not connected"
    TRACKER_AUTH_FAILED = "Failed to authenticate with {tracker}"
    INVALID_ACTIVITY_TYPE = "Invalid activity type"
    ACTIVITY_ALREADY_EXISTS = "Activity already exists"

    # File Upload Errors
    FILE_TOO_LARGE = "File size exceeds maximum allowed size"
    INVALID_FILE_TYPE = "Invalid file type. Allowed types: {types}"
    FILE_UPLOAD_FAILED = "File upload failed"
    FILE_NOT_FOUND = "File not found"
    IMAGE_PROCESSING_FAILED = "Image processing failed"

    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "Too many requests. Please try again later"
    TOO_MANY_ATTEMPTS = "Too many attempts. Please try again after {time}"

    # Certificate Errors
    CERTIFICATE_NOT_ELIGIBLE = "You are not eligible for a certificate"
    CERTIFICATE_GENERATION_FAILED = "Certificate generation failed"
    CERTIFICATE_ALREADY_GENERATED = "Certificate has already been generated"

    # Reward & Shipment Errors
    REWARD_NOT_ELIGIBLE = "You are not eligible for this reward"
    REWARD_ALREADY_CLAIMED = "Reward has already been claimed"
    SHIPMENT_FAILED = "Shipment creation failed"
    INVALID_SHIPMENT_STATUS = "Invalid shipment status"
    SHIPPING_ADDRESS_REQUIRED = "Shipping address is required"

    # Webhook Errors
    WEBHOOK_SIGNATURE_INVALID = "Invalid webhook signature"
    WEBHOOK_EVENT_INVALID = "Invalid webhook event"
    WEBHOOK_PROCESSING_FAILED = "Webhook processing failed"

    # Database Errors
    DATABASE_ERROR = "Database operation failed"
    DUPLICATE_ENTRY = "Duplicate entry detected"
    FOREIGN_KEY_CONSTRAINT = "Cannot complete operation due to related records"
    INTEGRITY_ERROR = "Data integrity constraint violated"

    # Organizer/Admin Errors
    ORGANIZER_ONLY = "Only event organizer can perform this action"
    ADMIN_ONLY = "Only administrators can perform this action"
    ORGANIZER_OR_ADMIN_ONLY = "Only event organizer or admin can perform this action"

    # Challenge Errors
    CHALLENGE_NOT_STARTED = "Challenge has not started yet"
    CHALLENGE_ENDED = "Challenge has ended"
    INVALID_CHALLENGE_STATUS = "Invalid challenge status"
    ALREADY_JOINED_CHALLENGE = "You have already joined this challenge"

    # Statistics & Leaderboard
    STATS_NOT_AVAILABLE = "Statistics are not available"
    LEADERBOARD_NOT_AVAILABLE = "Leaderboard is not available"

    # Feature Flags
    FEATURE_DISABLED = "This feature is currently disabled"
    FEATURE_NOT_AVAILABLE = "This feature is not available for your plan"

    # Configuration Errors
    MISSING_CONFIGURATION = "Missing required configuration: {config}"
    INVALID_CONFIGURATION = "Invalid configuration: {config}"

    @staticmethod
    def format_message(template: str, **kwargs) -> str:
        """
        Format error message with provided parameters.

        Args:
            template: Error message template with placeholders
            **kwargs: Values to format into the template

        Returns:
            Formatted error message
        """
        return template.format(**kwargs)
