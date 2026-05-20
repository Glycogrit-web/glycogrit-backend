"""
API Routes Constants

Centralized constants for API route paths and prefixes.
"""


class APIVersion:
    """API version prefixes."""

    V1 = "/api/v1"
    V2 = "/api/v2"
    CURRENT = V1  # Current active version


class APIRoutes:
    """API route path segments."""

    # Base paths
    API = "/api"
    HEALTH = "/health"
    DOCS = "/docs"
    REDOC = "/redoc"

    # Authentication & Users
    AUTH = "/auth"
    LOGIN = "/login"
    LOGOUT = "/logout"
    REGISTER = "/register"
    USERS = "/users"
    PROFILE = "/profile"
    PASSWORD = "/password"
    PASSWORD_RESET = "/password-reset"
    VERIFY_EMAIL = "/verify-email"

    # Events
    EVENTS = "/events"
    EVENT_CATEGORIES = "/categories"
    EVENT_FAQS = "/faqs"

    # Registrations
    REGISTRATIONS = "/registrations"
    MY_REGISTRATIONS = "/my-registrations"
    CANCEL_REGISTRATION = "/cancel"

    # Payments
    PAYMENTS = "/payments"
    ORDERS = "/orders"
    TRANSACTIONS = "/transactions"
    REFUNDS = "/refunds"
    WEBHOOKS = "/webhooks"
    PAYMENT_CALLBACK = "/callback"

    # Activities & Tracking
    ACTIVITIES = "/activities"
    ACTIVITY_SYNC = "/sync"
    FITNESS_TRACKERS = "/fitness-trackers"
    STRAVA = "/strava"
    GOOGLE_FIT = "/google-fit"
    APPLE_HEALTH = "/apple-health"
    NIKE_RUN_CLUB = "/nike-run-club"
    GARMIN = "/garmin"
    WAHOO = "/wahoo"
    FITBIT = "/fitbit"

    # Challenges
    CHALLENGES = "/challenges"
    LEADERBOARD = "/leaderboard"
    JOIN_CHALLENGE = "/join"
    LEAVE_CHALLENGE = "/leave"

    # Rewards & Certificates
    REWARDS = "/rewards"
    CERTIFICATES = "/certificates"
    CLAIM = "/claim"
    DOWNLOAD = "/download"
    GENERATE = "/generate"

    # Shipments
    SHIPMENTS = "/shipments"
    TRACKING = "/tracking"
    ADDRESS = "/address"

    # Gallery & Media
    GALLERY = "/gallery"
    UPLOAD = "/upload"
    IMAGES = "/images"
    MEDIA = "/media"

    # Admin
    ADMIN = "/admin"
    STATISTICS = "/statistics"
    ANALYTICS = "/analytics"
    REPORTS = "/reports"

    # Third-party Integrations
    INSTAGRAM = "/instagram"
    FACEBOOK = "/facebook"
    TWITTER = "/twitter"


class RouteParams:
    """Common route parameter names."""

    # ID parameters
    EVENT_ID = "event_id"
    USER_ID = "user_id"
    REGISTRATION_ID = "registration_id"
    PAYMENT_ID = "payment_id"
    ORDER_ID = "order_id"
    ACTIVITY_ID = "activity_id"
    CHALLENGE_ID = "challenge_id"
    REWARD_ID = "reward_id"
    CERTIFICATE_ID = "certificate_id"
    SHIPMENT_ID = "shipment_id"
    IMAGE_ID = "image_id"

    # Other parameters
    TOKEN = "token"
    CODE = "code"
    SLUG = "slug"
    FILENAME = "filename"


class QueryParams:
    """Common query parameter names."""

    # Pagination
    PAGE = "page"
    LIMIT = "limit"
    OFFSET = "offset"
    SKIP = "skip"

    # Sorting
    SORT_BY = "sort_by"
    ORDER = "order"
    ORDER_BY = "order_by"

    # Filtering
    FILTER = "filter"
    STATUS = "status"
    TYPE = "type"
    CATEGORY = "category"
    SEARCH = "search"
    QUERY = "q"

    # Date filtering
    START_DATE = "start_date"
    END_DATE = "end_date"
    FROM_DATE = "from"
    TO_DATE = "to"

    # Specific filters
    EVENT_ID = "event_id"
    USER_ID = "user_id"
    INCLUDE = "include"
    FIELDS = "fields"


def build_route(*segments: str) -> str:
    """
    Build a route from segments.

    Args:
        *segments: Route segments to join

    Returns:
        Complete route path

    Example:
        build_route(APIVersion.V1, APIRoutes.EVENTS, "{event_id}")
        # Returns: "/api/v1/events/{event_id}"
    """
    return "/".join(segment.strip("/") for segment in segments if segment)


def build_admin_route(route: str) -> str:
    """
    Build an admin route.

    Args:
        route: The route path

    Returns:
        Admin route path

    Example:
        build_admin_route(APIRoutes.EVENTS)
        # Returns: "/api/v1/admin/events"
    """
    return build_route(APIVersion.V1, APIRoutes.ADMIN, route)
