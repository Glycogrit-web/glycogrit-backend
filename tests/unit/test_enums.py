"""
Unit tests for core enums.

This test ensures that enum values match the expected string values
that are stored in the database, ensuring backward compatibility.
"""
import pytest

from app.core.enums import (
    ActivityType,
    CertificateType,
    ChallengeStatus,
    EventDifficulty,
    EventStatus,
    FitnessTrackerProvider,
    Gender,
    OAuthProvider,
    PaymentGateway,
    PaymentMethod,
    PaymentStatus,
    RefundStatus,
    RegistrationStatus,
    ShipmentStatus,
    TShirtSize,
    UserRole,
)


class TestPaymentEnums:
    """Test payment-related enums"""

    def test_payment_status_values(self):
        """Test PaymentStatus enum values"""
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.COMPLETED.value == "completed"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.REFUNDED.value == "refunded"

    def test_payment_method_values(self):
        """Test PaymentMethod enum values"""
        assert PaymentMethod.CREDIT_CARD.value == "credit_card"
        assert PaymentMethod.DEBIT_CARD.value == "debit_card"
        assert PaymentMethod.UPI.value == "upi"
        assert PaymentMethod.NET_BANKING.value == "net_banking"
        assert PaymentMethod.WALLET.value == "wallet"

    def test_payment_gateway_values(self):
        """Test PaymentGateway enum values"""
        assert PaymentGateway.RAZORPAY.value == "razorpay"
        assert PaymentGateway.STRIPE.value == "stripe"
        assert PaymentGateway.PAYPAL.value == "paypal"

    def test_refund_status_values(self):
        """Test RefundStatus enum values"""
        assert RefundStatus.PENDING.value == "pending"
        assert RefundStatus.PROCESSED.value == "processed"
        assert RefundStatus.FAILED.value == "failed"


class TestRegistrationEnums:
    """Test registration-related enums"""

    def test_registration_status_values(self):
        """Test RegistrationStatus enum values"""
        assert RegistrationStatus.PENDING.value == "pending"
        assert RegistrationStatus.CONFIRMED.value == "confirmed"
        assert RegistrationStatus.PAYMENT_COMPLETED.value == "payment_completed"
        assert RegistrationStatus.CANCELLED.value == "cancelled"


class TestEventEnums:
    """Test event-related enums"""

    def test_event_status_values(self):
        """Test EventStatus enum values"""
        assert EventStatus.DRAFT.value == "draft"
        assert EventStatus.PUBLISHED.value == "published"
        assert EventStatus.UPCOMING.value == "upcoming"
        assert EventStatus.ONGOING.value == "ongoing"
        assert EventStatus.COMPLETED.value == "completed"
        assert EventStatus.CANCELLED.value == "cancelled"

    def test_event_difficulty_values(self):
        """Test EventDifficulty enum values"""
        assert EventDifficulty.BEGINNER.value == "beginner"
        assert EventDifficulty.INTERMEDIATE.value == "intermediate"
        assert EventDifficulty.ADVANCED.value == "advanced"


class TestActivityEnums:
    """Test activity-related enums"""

    def test_activity_type_values(self):
        """Test ActivityType enum values"""
        assert ActivityType.RUNNING.value == "running"
        assert ActivityType.CYCLING.value == "cycling"
        assert ActivityType.WALKING.value == "walking"
        assert ActivityType.MIXED.value == "mixed"
        assert ActivityType.STRENGTH.value == "strength"
        assert ActivityType.SWIMMING.value == "swimming"
        assert ActivityType.HIKING.value == "hiking"


class TestUserEnums:
    """Test user-related enums"""

    def test_user_role_values(self):
        """Test UserRole enum values"""
        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.SUPER_ADMIN.value == "super_admin"
        assert UserRole.ORGANIZER.value == "organizer"

    def test_gender_values(self):
        """Test Gender enum values"""
        assert Gender.MALE.value == "male"
        assert Gender.FEMALE.value == "female"
        assert Gender.OTHER.value == "other"
        assert Gender.PREFER_NOT_TO_SAY.value == "prefer_not_to_say"

    def test_tshirt_size_values(self):
        """Test TShirtSize enum values"""
        assert TShirtSize.XS.value == "XS"
        assert TShirtSize.S.value == "S"
        assert TShirtSize.M.value == "M"
        assert TShirtSize.L.value == "L"
        assert TShirtSize.XL.value == "XL"
        assert TShirtSize.XXL.value == "XXL"
        assert TShirtSize.XXXL.value == "XXXL"


class TestShippingEnums:
    """Test shipping-related enums"""

    def test_shipment_status_values(self):
        """Test ShipmentStatus enum values"""
        assert ShipmentStatus.NEW.value == "NEW"
        assert ShipmentStatus.PENDING.value == "PENDING"
        assert ShipmentStatus.PICKUP_SCHEDULED.value == "PICKUP_SCHEDULED"
        assert ShipmentStatus.IN_TRANSIT.value == "IN_TRANSIT"
        assert ShipmentStatus.OUT_FOR_DELIVERY.value == "OUT_FOR_DELIVERY"
        assert ShipmentStatus.DELIVERED.value == "DELIVERED"
        assert ShipmentStatus.CANCELLED.value == "CANCELLED"
        assert ShipmentStatus.RTO_INITIATED.value == "RTO_INITIATED"
        assert ShipmentStatus.RTO_DELIVERED.value == "RTO_DELIVERED"


class TestOtherEnums:
    """Test other enums"""

    def test_certificate_type_values(self):
        """Test CertificateType enum values"""
        assert CertificateType.E_CERTIFICATE.value == "e-certificate"
        assert CertificateType.PHYSICAL.value == "physical"

    def test_challenge_status_values(self):
        """Test ChallengeStatus enum values"""
        assert ChallengeStatus.UPCOMING.value == "upcoming"
        assert ChallengeStatus.ONGOING.value == "ongoing"
        assert ChallengeStatus.COMPLETED.value == "completed"

    def test_fitness_tracker_provider_values(self):
        """Test FitnessTrackerProvider enum values"""
        assert FitnessTrackerProvider.STRAVA.value == "strava"
        assert FitnessTrackerProvider.APPLE_HEALTH.value == "apple_health"
        assert FitnessTrackerProvider.GOOGLE_FIT.value == "google_fit"
        assert FitnessTrackerProvider.NIKE_RUN_CLUB.value == "nike_run_club"

    def test_oauth_provider_values(self):
        """Test OAuthProvider enum values"""
        assert OAuthProvider.GOOGLE.value == "google"
        assert OAuthProvider.FACEBOOK.value == "facebook"
        assert OAuthProvider.APPLE.value == "apple"


class TestEnumStringInheritance:
    """Test that enums inherit from str for JSON serialization"""

    def test_payment_status_is_string(self):
        """Test that PaymentStatus enum values are strings"""
        assert isinstance(PaymentStatus.PENDING, str)
        assert isinstance(PaymentStatus.COMPLETED, str)

    def test_registration_status_is_string(self):
        """Test that RegistrationStatus enum values are strings"""
        assert isinstance(RegistrationStatus.PENDING, str)
        assert isinstance(RegistrationStatus.CONFIRMED, str)

    def test_event_status_is_string(self):
        """Test that EventStatus enum values are strings"""
        assert isinstance(EventStatus.DRAFT, str)
        assert isinstance(EventStatus.PUBLISHED, str)


class TestEnumComparison:
    """Test enum comparison with strings (for backward compatibility)"""

    def test_payment_status_string_comparison(self):
        """Test that enum values can be compared with strings"""
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.COMPLETED.value == "completed"
        # This is the pattern used in code:
        status = PaymentStatus.PENDING.value
        assert status == "pending"

    def test_registration_status_string_comparison(self):
        """Test that enum values can be compared with strings"""
        assert RegistrationStatus.CONFIRMED.value == "confirmed"
        status = RegistrationStatus.CONFIRMED.value
        assert status == "confirmed"
