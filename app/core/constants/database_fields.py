"""
Database Fields Constants

Centralized constants for database field names to ensure consistency
across queries and prevent typos.
"""


class CommonFields:
    """Common database field names used across multiple tables."""

    # Primary Keys
    ID = "id"
    UUID = "uuid"

    # Timestamps
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    DELETED_AT = "deleted_at"
    LAST_MODIFIED = "last_modified"

    # Status
    STATUS = "status"
    IS_ACTIVE = "is_active"
    IS_DELETED = "is_deleted"
    IS_VERIFIED = "is_verified"
    IS_PUBLISHED = "is_published"

    # Foreign Keys
    USER_ID = "user_id"
    EVENT_ID = "event_id"
    REGISTRATION_ID = "registration_id"
    ORDER_ID = "order_id"
    PAYMENT_ID = "payment_id"
    CHALLENGE_ID = "challenge_id"

    # Common Fields
    NAME = "name"
    DESCRIPTION = "description"
    EMAIL = "email"
    PHONE = "phone"
    TYPE = "type"


class UserFields:
    """User table field names."""

    ID = "id"
    UUID = "uuid"
    EMAIL = "email"
    USERNAME = "username"
    PASSWORD = "password"
    HASHED_PASSWORD = "hashed_password"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FULL_NAME = "full_name"
    PHONE = "phone"
    DATE_OF_BIRTH = "date_of_birth"
    GENDER = "gender"
    PROFILE_PICTURE = "profile_picture"
    ROLE = "role"
    IS_ACTIVE = "is_active"
    IS_VERIFIED = "is_verified"
    EMAIL_VERIFIED = "email_verified"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    LAST_LOGIN = "last_login"


class EventFields:
    """Event table field names."""

    ID = "id"
    UUID = "uuid"
    NAME = "name"
    SLUG = "slug"
    DESCRIPTION = "description"
    SHORT_DESCRIPTION = "short_description"
    EVENT_TYPE = "event_type"
    STATUS = "status"
    CATEGORY_ID = "category_id"
    ORGANIZER_ID = "organizer_id"
    START_DATE = "start_date"
    END_DATE = "end_date"
    REGISTRATION_START_DATE = "registration_start_date"
    REGISTRATION_END_DATE = "registration_end_date"
    LOCATION = "location"
    BANNER_IMAGE = "banner_image"
    MAX_PARTICIPANTS = "max_participants"
    CURRENT_PARTICIPANTS = "current_participants"
    PRICE = "price"
    IS_FREE = "is_free"
    IS_PUBLISHED = "is_published"
    FEATURES = "features"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class RegistrationFields:
    """Registration table field names."""

    ID = "id"
    UUID = "uuid"
    USER_ID = "user_id"
    EVENT_ID = "event_id"
    STATUS = "status"
    PAYMENT_STATUS = "payment_status"
    LAST_PAYMENT_STATUS = "last_payment_status"
    ORDER_ID = "order_id"
    BIB_NUMBER = "bib_number"
    TSHIRT_SIZE = "tshirt_size"
    EMERGENCY_CONTACT_NAME = "emergency_contact_name"
    EMERGENCY_CONTACT_PHONE = "emergency_contact_phone"
    REGISTERED_AT = "registered_at"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class PaymentFields:
    """Payment table field names."""

    ID = "id"
    UUID = "uuid"
    ORDER_ID = "order_id"
    USER_ID = "user_id"
    REGISTRATION_ID = "registration_id"
    AMOUNT = "amount"
    CURRENCY = "currency"
    STATUS = "status"
    PAYMENT_METHOD = "payment_method"
    GATEWAY = "gateway"
    GATEWAY_PAYMENT_ID = "gateway_payment_id"
    GATEWAY_ORDER_ID = "gateway_order_id"
    GATEWAY_SIGNATURE = "gateway_signature"
    TRANSACTION_ID = "transaction_id"
    PAID_AT = "paid_at"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class ActivityFields:
    """Activity table field names."""

    ID = "id"
    UUID = "uuid"
    USER_ID = "user_id"
    EVENT_ID = "event_id"
    CHALLENGE_ID = "challenge_id"
    ACTIVITY_TYPE = "activity_type"
    SOURCE = "source"
    EXTERNAL_ID = "external_id"
    DISTANCE = "distance"
    DURATION = "duration"
    ELEVATION_GAIN = "elevation_gain"
    CALORIES = "calories"
    AVERAGE_SPEED = "average_speed"
    MAX_SPEED = "max_speed"
    STARTED_AT = "started_at"
    ENDED_AT = "ended_at"
    SYNCED_AT = "synced_at"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class ChallengeFields:
    """Challenge table field names."""

    ID = "id"
    UUID = "uuid"
    EVENT_ID = "event_id"
    NAME = "name"
    DESCRIPTION = "description"
    CHALLENGE_TYPE = "challenge_type"
    ACTIVITY_TYPE = "activity_type"
    TARGET_DISTANCE = "target_distance"
    TARGET_DURATION = "target_duration"
    START_DATE = "start_date"
    END_DATE = "end_date"
    STATUS = "status"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class CertificateFields:
    """Certificate table field names."""

    ID = "id"
    UUID = "uuid"
    USER_ID = "user_id"
    EVENT_ID = "event_id"
    REGISTRATION_ID = "registration_id"
    CERTIFICATE_NUMBER = "certificate_number"
    CERTIFICATE_URL = "certificate_url"
    TEMPLATE_ID = "template_id"
    GENERATED_AT = "generated_at"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class RewardFields:
    """Reward table field names."""

    ID = "id"
    UUID = "uuid"
    USER_ID = "user_id"
    EVENT_ID = "event_id"
    REGISTRATION_ID = "registration_id"
    REWARD_TYPE = "reward_type"
    STATUS = "status"
    CLAIMED_AT = "claimed_at"
    SHIPPED_AT = "shipped_at"
    DELIVERED_AT = "delivered_at"
    TRACKING_NUMBER = "tracking_number"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class ShipmentFields:
    """Shipment table field names."""

    ID = "id"
    UUID = "uuid"
    ORDER_ID = "order_id"
    USER_ID = "user_id"
    REWARD_ID = "reward_id"
    SHIPROCKET_ORDER_ID = "shiprocket_order_id"
    SHIPROCKET_SHIPMENT_ID = "shiprocket_shipment_id"
    AWB_CODE = "awb_code"
    TRACKING_NUMBER = "tracking_number"
    COURIER_NAME = "courier_name"
    STATUS = "status"
    CURRENT_STATUS = "current_status"
    PICKUP_SCHEDULED_DATE = "pickup_scheduled_date"
    DELIVERED_DATE = "delivered_date"
    ADDRESS_LINE1 = "address_line1"
    ADDRESS_LINE2 = "address_line2"
    CITY = "city"
    STATE = "state"
    POSTAL_CODE = "postal_code"
    COUNTRY = "country"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class FitnessTrackerFields:
    """Fitness tracker connection table field names."""

    ID = "id"
    UUID = "uuid"
    USER_ID = "user_id"
    PROVIDER = "provider"
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    TOKEN_EXPIRES_AT = "token_expires_at"
    IS_CONNECTED = "is_connected"
    LAST_SYNC_AT = "last_sync_at"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class WebhookFields:
    """Webhook log table field names."""

    ID = "id"
    UUID = "uuid"
    EVENT_TYPE = "event_type"
    GATEWAY = "gateway"
    PAYLOAD = "payload"
    STATUS = "status"
    PROCESSED_AT = "processed_at"
    ERROR_MESSAGE = "error_message"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
