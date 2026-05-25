"""
Webhook Security Utilities

Provides security functions for webhook processing:
- Timestamp validation (replay attack prevention)
- Signature verification helpers
- Webhook event validation

Reference: OWASP Webhook Security Best Practices
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class WebhookSecurityValidator:
    """
    Security validator for webhook requests.

    Implements defense against:
    - Replay attacks (via timestamp validation)
    - Clock skew tolerance
    - Future timestamp detection
    """

    # Default security settings
    DEFAULT_MAX_AGE_SECONDS = 300  # 5 minutes
    DEFAULT_CLOCK_SKEW_SECONDS = 60  # 1 minute tolerance for clock differences

    def __init__(
        self,
        max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
        clock_skew_seconds: int = DEFAULT_CLOCK_SKEW_SECONDS,
    ):
        """
        Initialize webhook security validator.

        Args:
            max_age_seconds: Maximum age of webhook before rejection (default: 300 = 5 minutes)
            clock_skew_seconds: Clock skew tolerance (default: 60 = 1 minute)
        """
        self.max_age_seconds = max_age_seconds
        self.clock_skew_seconds = clock_skew_seconds

    def validate_timestamp(
        self, webhook_timestamp: datetime | None, webhook_id: str = "unknown"
    ) -> tuple[bool, str]:
        """
        Validate webhook timestamp to prevent replay attacks.

        Security Checks:
        1. Timestamp must be present
        2. Timestamp must not be too old (> max_age_seconds)
        3. Timestamp must not be in the future (with clock skew tolerance)

        Args:
            webhook_timestamp: Timestamp from webhook payload
            webhook_id: Webhook identifier for logging

        Returns:
            tuple: (is_valid, error_message)
                - (True, "") if valid
                - (False, "error message") if invalid

        Example:
            >>> validator = WebhookSecurityValidator()
            >>> timestamp = datetime.now(timezone.utc)
            >>> is_valid, error = validator.validate_timestamp(timestamp)
            >>> assert is_valid == True
        """
        # Check 1: Timestamp must be present
        if not webhook_timestamp:
            logger.warning(f"Webhook {webhook_id}: Missing timestamp")
            return False, "Webhook timestamp is required"

        # Ensure timezone-aware datetime
        current_time = datetime.now(timezone.utc)

        # If webhook_timestamp is naive (no timezone), assume UTC
        if webhook_timestamp.tzinfo is None:
            webhook_timestamp = webhook_timestamp.replace(tzinfo=timezone.utc)

        # Calculate age of webhook
        age_seconds = (current_time - webhook_timestamp).total_seconds()

        # Check 2: Webhook must not be too old
        if age_seconds > self.max_age_seconds:
            logger.warning(
                f"Webhook {webhook_id}: Too old ({age_seconds:.1f}s > {self.max_age_seconds}s)"
            )
            return False, (
                f"Webhook is too old ({age_seconds:.0f} seconds). "
                f"Maximum age: {self.max_age_seconds} seconds"
            )

        # Check 3: Webhook must not be from the future (with clock skew tolerance)
        if age_seconds < -self.clock_skew_seconds:
            logger.warning(
                f"Webhook {webhook_id}: From future ({age_seconds:.1f}s ahead, "
                f"tolerance: {self.clock_skew_seconds}s)"
            )
            return False, (
                f"Webhook timestamp is in the future ({abs(age_seconds):.0f} seconds ahead). "
                f"Clock skew tolerance: {self.clock_skew_seconds} seconds"
            )

        # Timestamp is valid
        logger.debug(f"Webhook {webhook_id}: Timestamp valid (age: {age_seconds:.1f}s)")
        return True, ""

    def validate_timestamp_string(
        self, timestamp_str: str | None, webhook_id: str = "unknown", format: str = "iso8601"
    ) -> tuple[bool, str]:
        """
        Validate webhook timestamp from string format.

        Args:
            timestamp_str: Timestamp string from webhook
            webhook_id: Webhook identifier for logging
            format: Timestamp format ("iso8601" or "unix")

        Returns:
            tuple: (is_valid, error_message)

        Example:
            >>> validator = WebhookSecurityValidator()
            >>> is_valid, error = validator.validate_timestamp_string("2026-05-19T10:30:00Z")
        """
        if not timestamp_str:
            return False, "Timestamp string is empty"

        try:
            if format == "unix":
                # Unix timestamp (seconds since epoch)
                timestamp = datetime.fromtimestamp(float(timestamp_str), tz=timezone.utc)
            else:
                # ISO 8601 format
                # Handle various ISO formats
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            return self.validate_timestamp(timestamp, webhook_id)

        except (ValueError, TypeError) as e:
            logger.error(f"Webhook {webhook_id}: Invalid timestamp format '{timestamp_str}': {e}")
            return False, f"Invalid timestamp format: {str(e)}"

    def get_timestamp_info(self, webhook_timestamp: datetime) -> dict:
        """
        Get detailed information about webhook timestamp for debugging.

        Args:
            webhook_timestamp: Timestamp to analyze

        Returns:
            dict: Timestamp analysis information
        """
        current_time = datetime.now(timezone.utc)

        # Ensure timezone-aware
        if webhook_timestamp.tzinfo is None:
            webhook_timestamp = webhook_timestamp.replace(tzinfo=timezone.utc)

        age_seconds = (current_time - webhook_timestamp).total_seconds()

        return {
            "webhook_timestamp": webhook_timestamp.isoformat(),
            "current_time": current_time.isoformat(),
            "age_seconds": age_seconds,
            "age_minutes": age_seconds / 60,
            "is_future": age_seconds < 0,
            "is_too_old": age_seconds > self.max_age_seconds,
            "is_within_tolerance": abs(age_seconds) <= self.max_age_seconds,
            "max_age_seconds": self.max_age_seconds,
            "clock_skew_seconds": self.clock_skew_seconds,
        }


# Convenience functions for common use cases


def validate_webhook_timestamp(
    timestamp: datetime | None, max_age_seconds: int = 300, webhook_id: str = "unknown"
) -> bool:
    """
    Quick validation of webhook timestamp.

    Args:
        timestamp: Webhook timestamp
        max_age_seconds: Maximum age in seconds (default: 300 = 5 minutes)
        webhook_id: Webhook identifier for logging

    Returns:
        bool: True if timestamp is valid

    Example:
        >>> from datetime import datetime, timezone
        >>> timestamp = datetime.now(timezone.utc)
        >>> is_valid = validate_webhook_timestamp(timestamp)
        >>> assert is_valid == True
    """
    validator = WebhookSecurityValidator(max_age_seconds=max_age_seconds)
    is_valid, _ = validator.validate_timestamp(timestamp, webhook_id)
    return is_valid


def validate_webhook_timestamp_string(
    timestamp_str: str | None,
    max_age_seconds: int = 300,
    webhook_id: str = "unknown",
    format: str = "iso8601",
) -> bool:
    """
    Quick validation of webhook timestamp from string.

    Args:
        timestamp_str: Timestamp string
        max_age_seconds: Maximum age in seconds (default: 300 = 5 minutes)
        webhook_id: Webhook identifier for logging
        format: Timestamp format ("iso8601" or "unix")

    Returns:
        bool: True if timestamp is valid

    Example:
        >>> is_valid = validate_webhook_timestamp_string("2026-05-19T10:30:00Z")
    """
    validator = WebhookSecurityValidator(max_age_seconds=max_age_seconds)
    is_valid, _ = validator.validate_timestamp_string(timestamp_str, webhook_id, format)
    return is_valid


def get_webhook_timestamp_from_razorpay(payload: dict) -> datetime | None:
    """
    Extract timestamp from Razorpay webhook payload.

    Razorpay includes timestamp in payload['created_at'] (Unix timestamp).

    Args:
        payload: Razorpay webhook payload

    Returns:
        datetime or None if not found

    Example:
        >>> payload = {"created_at": 1684497000, ...}
        >>> timestamp = get_webhook_timestamp_from_razorpay(payload)
    """
    try:
        # Razorpay sends Unix timestamp in 'created_at'
        if "created_at" in payload:
            unix_timestamp = payload["created_at"]
            return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)

        # Also check in payload['payload'] for nested structure
        if "payload" in payload:
            nested_payload = payload["payload"]
            if isinstance(nested_payload, dict) and "payment" in nested_payload:
                payment = nested_payload["payment"]
                if isinstance(payment, dict) and "created_at" in payment:
                    unix_timestamp = payment["created_at"]
                    return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)

        return None

    except (ValueError, TypeError, KeyError) as e:
        logger.error(f"Error extracting timestamp from Razorpay payload: {e}")
        return None


# Example usage and testing
if __name__ == "__main__":
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    validator = WebhookSecurityValidator(max_age_seconds=300)

    print("=== Webhook Timestamp Validation Tests ===\n")

    # Test 1: Valid timestamp (now)
    print("Test 1: Current timestamp (should PASS)")
    timestamp_now = datetime.now(timezone.utc)
    is_valid, error = validator.validate_timestamp(timestamp_now, "test-webhook-1")
    print(f"Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    if error:
        print(f"Error: {error}")
    print()

    # Test 2: Old timestamp (10 minutes ago - should FAIL)
    print("Test 2: Old timestamp - 10 minutes ago (should FAIL)")
    timestamp_old = datetime.now(timezone.utc) - timedelta(minutes=10)
    is_valid, error = validator.validate_timestamp(timestamp_old, "test-webhook-2")
    print(f"Result: {'✅ PASS' if not is_valid else '❌ FAIL (should have failed)'}")
    if error:
        print(f"Error: {error}")
    print()

    # Test 3: Future timestamp (should FAIL)
    print("Test 3: Future timestamp - 2 minutes ahead (should FAIL)")
    timestamp_future = datetime.now(timezone.utc) + timedelta(minutes=2)
    is_valid, error = validator.validate_timestamp(timestamp_future, "test-webhook-3")
    print(f"Result: {'✅ PASS' if not is_valid else '❌ FAIL (should have failed)'}")
    if error:
        print(f"Error: {error}")
    print()

    # Test 4: Boundary - exactly 5 minutes old (should PASS with default settings)
    print("Test 4: Boundary - exactly 4.9 minutes old (should PASS)")
    timestamp_boundary = datetime.now(timezone.utc) - timedelta(seconds=294)
    is_valid, error = validator.validate_timestamp(timestamp_boundary, "test-webhook-4")
    print(f"Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    if error:
        print(f"Error: {error}")
    print()

    # Test 5: ISO string format
    print("Test 5: ISO string format (should PASS)")
    timestamp_iso = datetime.now(timezone.utc).isoformat()
    is_valid, error = validator.validate_timestamp_string(timestamp_iso, "test-webhook-5")
    print(f"Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    if error:
        print(f"Error: {error}")
    print()

    # Test 6: Get timestamp info
    print("Test 6: Get timestamp information")
    info = validator.get_timestamp_info(timestamp_now)
    print(f"Age: {info['age_seconds']:.2f} seconds")
    print(f"Is too old: {info['is_too_old']}")
    print(f"Is within tolerance: {info['is_within_tolerance']}")
    print()

    print("=== All Tests Complete ===")
    sys.exit(0)
