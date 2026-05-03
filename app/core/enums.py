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
    """Event lifecycle status"""
    DRAFT = "draft"
    PUBLISHED = "published"
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


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
    NIKE_RUN_CLUB = "nike_run_club"


# OAuth Provider Enums
class OAuthProvider(str, Enum):
    """OAuth provider"""
    GOOGLE = "google"
    FACEBOOK = "facebook"
    APPLE = "apple"
