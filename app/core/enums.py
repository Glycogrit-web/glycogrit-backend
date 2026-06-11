"""
Centralized enums for the GlycoGrit Backend.

This module contains all enum definitions used throughout the application
to replace magic strings and provide type safety.
"""

from enum import Enum


# Payment Related Enums
class PaymentStatus(str, Enum):
    """Payment transaction status"""

    PENDING = "pending"
    AUTHORIZED = "authorized"  # Payment authorized but not yet captured
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    VOIDED = "voided"  # Authorization voided/released without capturing


class PaymentMethod(str, Enum):
    """Payment method types"""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    UPI = "upi"
    NET_BANKING = "net_banking"
    WALLET = "wallet"


class PaymentGateway(str, Enum):
    """Payment gateway providers"""

    RAZORPAY = "razorpay"
    STRIPE = "stripe"
    PAYPAL = "paypal"


class RefundStatus(str, Enum):
    """Refund processing status"""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


# Registration Related Enums
class RegistrationStatus(str, Enum):
    """Event registration status"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAYMENT_COMPLETED = "payment_completed"
    CANCELLED = "cancelled"


# Event Related Enums
class EventStatus(str, Enum):
    """Event status - simplified to 2 states

    DRAFT: Event is being created/configured by admin, not visible to public
    PUBLISHED: Event is published and visible to all users

    Registration state (open/closed) is automatically determined by
    registration_start_date and registration_end_date, not by status.
    """

    DRAFT = "draft"
    PUBLISHED = "published"


class EventDifficulty(str, Enum):
    """Event difficulty levels"""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# Activity Related Enums
class ActivityType(str, Enum):
    """Type of physical activity"""

    RUNNING = "running"
    CYCLING = "cycling"
    WALKING = "walking"
    MIXED = "mixed"
    STRENGTH = "strength"
    SWIMMING = "swimming"
    HIKING = "hiking"


# User Related Enums
class UserRole(str, Enum):
    """User role in the system"""

    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    ORGANIZER = "organizer"


class Gender(str, Enum):
    """Gender options"""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class TShirtSize(str, Enum):
    """T-shirt size options"""

    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    XXL = "XXL"
    XXXL = "XXXL"


# Shipping/Shiprocket Related Enums
class ShipmentStatus(str, Enum):
    """Shipment order status"""

    NEW = "NEW"
    PENDING = "PENDING"
    PICKUP_SCHEDULED = "PICKUP_SCHEDULED"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RTO_INITIATED = "RTO_INITIATED"
    RTO_DELIVERED = "RTO_DELIVERED"


# Certificate Related Enums
class CertificateType(str, Enum):
    """Certificate delivery type"""

    E_CERTIFICATE = "e-certificate"
    PHYSICAL = "physical"


# Challenge Related Enums
class ChallengeStatus(str, Enum):
    """Challenge status"""

    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"


# Fitness Tracker Related Enums
class FitnessTrackerProvider(str, Enum):
    """Fitness tracker provider"""

    STRAVA = "strava"
    APPLE_HEALTH = "apple_health"
    GOOGLE_FIT = "google_fit"
    GOOGLE_HEALTH = "google_health"
    NIKE_RUN_CLUB = "nike_run_club"
    GARMIN = "garmin"
    WAHOO = "wahoo"
    FITBIT = "fitbit"


# OAuth Provider Enums
class OAuthProvider(str, Enum):
    """OAuth provider"""

    GOOGLE = "google"
    FACEBOOK = "facebook"
    APPLE = "apple"


# Reward Related Enums
class RewardType(str, Enum):
    """Reward types"""

    MEDAL = "medal"
    TSHIRT = "tshirt"
    CERTIFICATE = "certificate"
    TROPHY = "trophy"
    CUSTOM = "custom"


class RewardStatus(str, Enum):
    """
    DEPRECATED: Reward status enum no longer used.

    The reward system has been SIMPLIFIED to use boolean flags instead of this complex status enum:
    - is_verified: Admin has verified shipping details (eligible for Excel export)
    - is_unlocked: Reward is unlocked for user access
    - tracking_visible_to_user: User can see tracking URL

    This enum is kept for backward compatibility only. New code should NOT use this.

    Old workflow (DEPRECATED):
    LOCKED → READY_TO_SHIP → TRACKING_ORDER → DELIVERED

    New workflow (CURRENT):
    Unverified (is_verified=false) → Verified (is_verified=true) → Tracking Added (tracking_visible_to_user=true)
    """

    LOCKED = "locked"  # DEPRECATED - Use is_verified=false instead
    READY_TO_SHIP = "ready_to_ship"  # DEPRECATED - Use is_verified=true instead
    TRACKING_ORDER = "tracking_order"  # DEPRECATED - Use tracking_visible_to_user=true instead
    DELIVERED = "delivered"  # DEPRECATED - Not our concern (Shiprocket handles delivery)
    CANCELLED = "cancelled"  # DEPRECATED - Not used


# Completion Status Enum
class CompletionStatus(str, Enum):
    """Activity or challenge completion status"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# Feature Type Enum
class FeatureType(str, Enum):
    """Event feature types"""

    ACTIVITY = "activity"
    REWARD = "reward"
    SHIPPING = "shipping"
    CERTIFICATE = "certificate"
    LEADERBOARD = "leaderboard"


# API Response Status
class APIResponseStatus(str, Enum):
    """API response status"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"
