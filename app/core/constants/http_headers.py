"""
HTTP Headers Constants

Centralized constants for all HTTP headers used throughout the application.
"""


class HTTPHeaders:
    """HTTP header names used across the application."""

    # Custom Headers
    X_REQUEST_ID = "X-Request-ID"
    X_PROCESS_TIME = "X-Process-Time"

    # Rate Limiting Headers
    X_RATELIMIT_LIMIT = "X-RateLimit-Limit"
    X_RATELIMIT_REMAINING = "X-RateLimit-Remaining"
    X_RATELIMIT_RESET = "X-RateLimit-Reset"

    # Security Headers
    X_CONTENT_TYPE_OPTIONS = "X-Content-Type-Options"
    X_FRAME_OPTIONS = "X-Frame-Options"
    X_XSS_PROTECTION = "X-XSS-Protection"
    STRICT_TRANSPORT_SECURITY = "Strict-Transport-Security"
    CONTENT_SECURITY_POLICY = "Content-Security-Policy"

    # Standard Headers
    AUTHORIZATION = "Authorization"
    CONTENT_TYPE = "Content-Type"
    ACCEPT = "Accept"
    USER_AGENT = "User-Agent"
    ORIGIN = "Origin"
    REFERER = "Referer"

    # Payment Gateway Headers
    X_RAZORPAY_SIGNATURE = "X-Razorpay-Signature"
    X_STRIPE_SIGNATURE = "Stripe-Signature"

    # CORS Headers
    ACCESS_CONTROL_ALLOW_ORIGIN = "Access-Control-Allow-Origin"
    ACCESS_CONTROL_ALLOW_METHODS = "Access-Control-Allow-Methods"
    ACCESS_CONTROL_ALLOW_HEADERS = "Access-Control-Allow-Headers"
    ACCESS_CONTROL_ALLOW_CREDENTIALS = "Access-Control-Allow-Credentials"


class HeaderValues:
    """Common header values."""

    # Authorization
    BEARER_PREFIX = "Bearer"

    # Content-Type
    APPLICATION_JSON = "application/json"
    APPLICATION_FORM_URLENCODED = "application/x-www-form-urlencoded"
    MULTIPART_FORM_DATA = "multipart/form-data"
    TEXT_HTML = "text/html"
    TEXT_PLAIN = "text/plain"

    # Security Header Values
    NOSNIFF = "nosniff"
    DENY = "DENY"
    SAMEORIGIN = "SAMEORIGIN"
