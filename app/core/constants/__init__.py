"""
Constants module for centralized management of magic strings.

This module provides a centralized location for all constants used throughout
the application, preventing magic strings from being scattered across the codebase.
"""

from .api_routes import APIRoutes, APIVersion, QueryParams, RouteParams
from .database_fields import (
    ActivityFields,
    CertificateFields,
    ChallengeFields,
    CommonFields,
    EventFields,
    FitnessTrackerFields,
    PaymentFields,
    RegistrationFields,
    RewardFields,
    ShipmentFields,
    UserFields,
    WebhookFields,
)
from .error_messages import ErrorMessages
from .http_headers import HeaderValues, HTTPHeaders
from .mime_types import AllowedMimeTypes, FileExtensions, MimeTypes
from .webhook_events import (
    PayPalEvents,
    RazorpayEvents,
    ShiprocketEvents,
    StravaWebhookEvents,
    StripeEvents,
    WebhookEventTypes,
    WebhookStatus,
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
