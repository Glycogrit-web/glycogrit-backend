"""
Security Headers Middleware

Adds security headers to all HTTP responses to protect against common web vulnerabilities:
- XSS (Cross-Site Scripting)
- Clickjacking
- MIME-type sniffing
- Man-in-the-middle attacks

Reference: https://owasp.org/www-project-secure-headers/
"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.constants import HeaderValues, HTTPHeaders

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Applied headers:
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable browser XSS filter
    - Content-Security-Policy: Control resource loading
    - Strict-Transport-Security: Force HTTPS (production only)
    - Cache-Control: Prevent sensitive data caching
    - Referrer-Policy: Control referrer information
    """

    def __init__(self, app):
        super().__init__(app)
        self.is_production = settings.ENVIRONMENT == "production"
        # Logging moved to startup event to avoid duplicate logs per worker
        logger.debug(f"SecurityHeadersMiddleware initialized (production={self.is_production})")

    async def dispatch(self, request: Request, call_next):
        """Process request and add security headers to response"""

        response: Response = await call_next(request)

        # ========================================
        # Universal Security Headers (All Environments)
        # ========================================

        # Prevent MIME-type sniffing
        # Protects against: Drive-by downloads, MIME confusion attacks
        response.headers[HTTPHeaders.X_CONTENT_TYPE_OPTIONS] = HeaderValues.NOSNIFF

        # Prevent page from being displayed in iframe
        # Protects against: Clickjacking attacks
        response.headers[HTTPHeaders.X_FRAME_OPTIONS] = HeaderValues.DENY

        # Enable browser XSS protection
        # Protects against: Reflected XSS attacks
        response.headers[HTTPHeaders.X_XSS_PROTECTION] = "1; mode=block"

        # Control referrer information sent to other sites
        # Protects against: Information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (CSP)
        # Protects against: XSS, data injection attacks
        # Note: For API-only backend, we use restrictive CSP
        csp_directives = [
            "default-src 'self'",
            "frame-ancestors 'none'",  # Same as X-Frame-Options: DENY
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Permissions Policy (formerly Feature-Policy)
        # Disable unnecessary browser features
        permissions_policy = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)

        # ========================================
        # Production-Only Security Headers
        # ========================================

        if self.is_production:
            # Force HTTPS for all future connections (1 year)
            # Protects against: Man-in-the-middle attacks, protocol downgrade attacks
            # Only enable in production after confirming HTTPS works
            response.headers[HTTPHeaders.STRICT_TRANSPORT_SECURITY] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # ========================================
        # API-Specific Headers
        # ========================================

        # Prevent caching of API responses containing sensitive data
        if request.url.path.startswith("/api/v1/"):
            # Exclude public endpoints that can be cached
            cacheable_paths = [
                "/api/v1/events",  # Public event listings
                "/api/v1/statistics",  # Public statistics
                "/api/v1/test",  # Test endpoints
            ]

            # Check if path should be cached
            is_cacheable = any(
                request.url.path.startswith(path) and request.method == "GET"
                for path in cacheable_paths
            )

            if not is_cacheable:
                # Disable caching for sensitive endpoints
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

        # ========================================
        # Remove Sensitive Headers
        # ========================================

        # Remove server identification headers (security through obscurity)
        # Makes it harder for attackers to identify vulnerabilities
        headers_to_remove = ["Server", "X-Powered-By"]
        for header in headers_to_remove:
            if header in response.headers:
                del response.headers[header]

        return response
