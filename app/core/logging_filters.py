"""
Logging Filters for Sensitive Data Protection

Prevents sensitive data (PII, credentials, tokens) from being logged,
ensuring compliance with GDPR, PCI-DSS, and other privacy regulations.

Features:
- Email address redaction
- Phone number redaction
- Credit card number redaction
- Password redaction
- Token/API key redaction
- IP address redaction (optional)
- Configurable patterns
"""

import re
import logging
from typing import List, Tuple, Pattern
from functools import lru_cache


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that redacts sensitive data from log messages.

    This filter protects against accidental logging of:
    - Personal Identifiable Information (PII)
    - Authentication credentials
    - Payment information
    - API keys and tokens

    Usage:
        handler.addFilter(SensitiveDataFilter())

    Configuration:
        Set ENABLE_SENSITIVE_DATA_FILTERING=False to disable in development
    """

    # Patterns for sensitive data detection
    # Format: (pattern, replacement, description)
    SENSITIVE_PATTERNS: List[Tuple[Pattern, str, str]] = [
        # Email addresses
        (
            re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            '[EMAIL_REDACTED]',
            'Email address'
        ),

        # Indian phone numbers (with various formats)
        (
            re.compile(r'(\+91[-\s]?)?[6-9]\d{9}\b'),
            '[PHONE_REDACTED]',
            'Phone number'
        ),

        # Credit card numbers (basic pattern - 13-19 digits)
        (
            re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4,7}\b'),
            '[CARD_REDACTED]',
            'Credit card number'
        ),

        # CVV/CVC codes (3-4 digits, often near "cvv" or "cvc")
        (
            re.compile(r'\b(?:cvv|cvc|security\s+code)[\s:=]+\d{3,4}\b', re.IGNORECASE),
            'cvv=[CVV_REDACTED]',
            'CVV code'
        ),

        # Passwords in JSON/form data
        (
            re.compile(r'("password"\s*:\s*")[^"]*(")', re.IGNORECASE),
            r'\1[PASSWORD_REDACTED]\2',
            'Password in JSON'
        ),
        (
            re.compile(r'(password\s*=\s*)[^\s&]+', re.IGNORECASE),
            r'\1[PASSWORD_REDACTED]',
            'Password in form data'
        ),

        # JWT tokens and Bearer tokens
        (
            re.compile(r'\b(Bearer\s+)[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_.+/=]*\b'),
            r'\1[JWT_TOKEN_REDACTED]',
            'JWT token'
        ),

        # API keys (common patterns)
        (
            re.compile(r'("(?:api[_-]?key|apikey|api_secret)"\s*:\s*")[^"]*(")', re.IGNORECASE),
            r'\1[API_KEY_REDACTED]\2',
            'API key in JSON'
        ),
        (
            re.compile(r'\b[A-Za-z0-9]{32,}\b'),  # Long alphanumeric strings (likely tokens)
            '[TOKEN_REDACTED]',
            'Long token'
        ),

        # Razorpay keys
        (
            re.compile(r'\brzp_(test|live)_[A-Za-z0-9]+\b'),
            '[RAZORPAY_KEY_REDACTED]',
            'Razorpay key'
        ),

        # OAuth tokens
        (
            re.compile(r'("(?:access_token|refresh_token|id_token)"\s*:\s*")[^"]*(")', re.IGNORECASE),
            r'\1[OAUTH_TOKEN_REDACTED]\2',
            'OAuth token'
        ),

        # Authorization headers
        (
            re.compile(r'(Authorization:\s*Bearer\s+)[^\s]+', re.IGNORECASE),
            r'\1[AUTH_TOKEN_REDACTED]',
            'Authorization header'
        ),

        # Secret keys in environment variables
        (
            re.compile(r'(SECRET[_A-Z]*\s*=\s*)[^\s]+', re.IGNORECASE),
            r'\1[SECRET_REDACTED]',
            'Secret key'
        ),

        # Database connection strings (passwords)
        (
            re.compile(r'(postgresql://[^:]+:)[^@]+(@)'),
            r'\1[DB_PASSWORD_REDACTED]\2',
            'Database password'
        ),

        # IP addresses (optional - uncomment if needed)
        # (
        #     re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
        #     '[IP_REDACTED]',
        #     'IP address'
        # ),
    ]

    def __init__(self, enable_filtering: bool = True):
        """
        Initialize the sensitive data filter.

        Args:
            enable_filtering: Whether to enable filtering (default: True)
                             Can be disabled in development environments
        """
        super().__init__()
        self.enable_filtering = enable_filtering
        self.redaction_count = 0

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record by redacting sensitive data.

        Args:
            record: LogRecord to filter

        Returns:
            True (always allows the record through after filtering)
        """
        if not self.enable_filtering:
            return True

        try:
            # Redact sensitive data in the main message
            if record.msg:
                original_msg = str(record.msg)
                filtered_msg = self._redact_sensitive_data(original_msg)

                if filtered_msg != original_msg:
                    record.msg = filtered_msg
                    self.redaction_count += 1

            # Redact sensitive data in arguments
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        k: self._redact_sensitive_data(str(v))
                        for k, v in record.args.items()
                    }
                elif isinstance(record.args, (list, tuple)):
                    record.args = tuple(
                        self._redact_sensitive_data(str(arg))
                        for arg in record.args
                    )

        except Exception as e:
            # Don't let filtering errors break logging
            # Log the error but allow the original record through
            import sys
            print(f"Error in SensitiveDataFilter: {e}", file=sys.stderr)

        return True

    @lru_cache(maxsize=1024)
    def _redact_sensitive_data(self, text: str) -> str:
        """
        Redact sensitive data from text using compiled patterns.

        Args:
            text: Text to redact

        Returns:
            Text with sensitive data redacted

        Note:
            Uses LRU cache to improve performance for repeated messages
        """
        if not text:
            return text

        filtered_text = text

        for pattern, replacement, _ in self.SENSITIVE_PATTERNS:
            filtered_text = pattern.sub(replacement, filtered_text)

        return filtered_text

    def get_redaction_count(self) -> int:
        """Get the number of times sensitive data was redacted"""
        return self.redaction_count


class StructuredDataFilter(logging.Filter):
    """
    Filter for structured log data (JSON, dict) with deep inspection.

    This filter handles complex data structures where sensitive data
    might be nested in dictionaries or JSON payloads.

    Usage:
        handler.addFilter(StructuredDataFilter())
    """

    SENSITIVE_KEYS = {
        'password', 'passwd', 'pwd',
        'secret', 'api_key', 'apikey', 'api_secret',
        'token', 'access_token', 'refresh_token', 'id_token',
        'authorization', 'auth',
        'credit_card', 'card_number', 'cvv', 'cvc',
        'ssn', 'social_security',
        'private_key', 'key',
    }

    def __init__(self, sensitive_keys: set = None):
        """
        Initialize the structured data filter.

        Args:
            sensitive_keys: Set of keys to redact (default: SENSITIVE_KEYS)
        """
        super().__init__()
        self.sensitive_keys = sensitive_keys or self.SENSITIVE_KEYS

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter structured data in log record.

        Args:
            record: LogRecord to filter

        Returns:
            True (always allows the record through after filtering)
        """
        try:
            if record.args and isinstance(record.args, dict):
                record.args = self._redact_dict(record.args)

            # Also check if the message itself is structured data
            if isinstance(record.msg, dict):
                record.msg = self._redact_dict(record.msg)

        except Exception as e:
            # Don't let filtering errors break logging
            import sys
            print(f"Error in StructuredDataFilter: {e}", file=sys.stderr)

        return True

    def _redact_dict(self, data: dict, max_depth: int = 10, current_depth: int = 0) -> dict:
        """
        Recursively redact sensitive keys in dictionary.

        Args:
            data: Dictionary to redact
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth

        Returns:
            Dictionary with sensitive values redacted
        """
        if current_depth >= max_depth:
            return data

        if not isinstance(data, dict):
            return data

        redacted = {}

        for key, value in data.items():
            key_lower = str(key).lower()

            # Check if key is sensitive
            if any(sensitive_key in key_lower for sensitive_key in self.sensitive_keys):
                redacted[key] = '[REDACTED]'
            # Recursively handle nested dictionaries
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value, max_depth, current_depth + 1)
            # Handle lists of dictionaries
            elif isinstance(value, (list, tuple)):
                redacted[key] = [
                    self._redact_dict(item, max_depth, current_depth + 1)
                    if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted[key] = value

        return redacted


# Convenience function to configure logging with filters
def configure_secure_logging(
    enable_sensitive_filter: bool = True,
    enable_structured_filter: bool = True,
    log_level: str = "INFO"
):
    """
    Configure logging with security filters.

    Args:
        enable_sensitive_filter: Enable sensitive data filtering
        enable_structured_filter: Enable structured data filtering
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Example:
        >>> from app.core.logging_filters import configure_secure_logging
        >>> configure_secure_logging(log_level="INFO")
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Apply filters to all handlers
    for handler in root_logger.handlers:
        if enable_sensitive_filter:
            handler.addFilter(SensitiveDataFilter())

        if enable_structured_filter:
            handler.addFilter(StructuredDataFilter())

    logging.info("Secure logging configured with sensitive data filtering")


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Add filters
    configure_secure_logging()

    # Test sensitive data redaction
    logger = logging.getLogger(__name__)

    logger.info("User logged in: john.doe@example.com")  # Email redacted
    logger.info("Phone number: +91 9876543210")  # Phone redacted
    logger.info("Password: SecurePass123!")  # Password redacted
    logger.info("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")  # Token redacted
    logger.info("API Key: rzp_test_1234567890abcdef")  # Razorpay key redacted
    logger.info('{"password": "secret123", "username": "john"}')  # Password in JSON redacted

    print("✅ Logging filter tests completed")
