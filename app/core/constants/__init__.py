"""
Constants module for centralized management of magic strings.

This module provides a centralized location for all constants used throughout
the application, preventing magic strings from being scattered across the codebase.
"""

from .http_headers import HTTPHeaders, HeaderValues
from .error_messages import ErrorMessages
from .webhook_events import (
    RazorpayEvents,
    StripeEvents,
    PayPalEvents,
    StravaWebhookEvents,
    ShiprocketEvents,
    WebhookEventTypes,
    WebhookStatus,
)
from .mime_types import MimeTypes, AllowedMimeTypes, FileExtensions
from .api_routes import APIRoutes, APIVersion, RouteParams, QueryParams
from .database_fields import (
    CommonFields,
    UserFields,
    EventFields,
    PaymentFields,
    RegistrationFields,
    ActivityFields,
    ChallengeFields,
    CertificateFields,
    RewardFields,
    ShipmentFields,
    FitnessTrackerFields,
    WebhookFields,
)

__all__ = [
    # HTTP Headers
    "HTTPHeaders",
    "HeaderValues",
    # Error Messages
    "ErrorMessages",
    # Webhook Events
    "RazorpayEvents",
    "StripeEvents",
    "PayPalEvents",
    "StravaWebhookEvents",
    "ShiprocketEvents",
    "WebhookEventTypes",
    "WebhookStatus",
    # MIME Types
    "MimeTypes",
    "AllowedMimeTypes",
    "FileExtensions",
    # API Routes
    "APIRoutes",
    "APIVersion",
    "RouteParams",
    "QueryParams",
    # Database Fields
    "CommonFields",
    "UserFields",
    "EventFields",
    "PaymentFields",
    "RegistrationFields",
    "ActivityFields",
    "ChallengeFields",
    "CertificateFields",
    "RewardFields",
    "ShipmentFields",
    "FitnessTrackerFields",
    "WebhookFields",
]
