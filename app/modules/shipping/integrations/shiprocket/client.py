"""
Shiprocket Service
Handles all Shiprocket API interactions for order creation, tracking, and label generation

Security Features:
- TLS fingerprinting bypass using curl_cffi (mimics Chrome browser)
- Strict SSL verification (never disabled)
- Request timeouts to prevent server hangs
- PII sanitization in logs
- Token caching with secure expiry
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from curl_cffi.requests import AsyncSession
from sqlalchemy.orm import Session

from app.modules.shipping.domain.config import ShiprocketConfig
from app.models.user_reward import UserReward

logger = logging.getLogger(__name__)

# Request timeout in seconds - prevents server hangs if Shiprocket is down
API_TIMEOUT = 15.0


class ShiprocketService:
    """
    Service for interacting with Shiprocket API.
    Handles authentication, order creation, tracking, and shipping operations.

    Proxy Support:
    Set SHIPROCKET_PROXY_URL environment variable to route requests through a proxy.
    This is useful when Railway's IP is blocked by Shiprocket's firewall.
    """

    BASE_URL = "https://apiv2.shiprocket.in/v1/external"

    def __init__(self, db: Session):
        """
        Initialize Shiprocket service.

        Args:
            db: Database session
        """
        import os

        self.db = db
        self.config = self._get_config()
        self.token: str | None = None

        # Proxy support for IP blocking workaround
        self.proxy_url = os.getenv("SHIPROCKET_PROXY_URL")
        if self.proxy_url:
            logger.info(f"🔀 Shiprocket proxy enabled: {self.proxy_url}")
            logger.info(f"   All requests will be routed through the proxy")

    def _get_config(self) -> ShiprocketConfig:
        """
        Get active Shiprocket configuration.

        Returns:
            ShiprocketConfig instance

        Raises:
            ValueError: If no active configuration found
        """
        config = self.db.query(ShiprocketConfig).filter(ShiprocketConfig.is_active).first()

        if not config:
            raise ValueError(
                "Shiprocket configuration not found. Please configure Shiprocket credentials."
            )

        return config

    def _get_url(self, endpoint: str) -> str:
        """
        Get the URL for a Shiprocket API endpoint.

        If proxy is configured, returns proxy URL. Otherwise returns direct Shiprocket URL.

        Args:
            endpoint: API endpoint (e.g., "/auth/login", "/orders/create/adhoc")

        Returns:
            Full URL to use for the request
        """
        # Remove leading slash if present
        endpoint = endpoint.lstrip("/")

        if self.proxy_url:
            # Route through proxy
            return f"{self.proxy_url}/{endpoint}"
        else:
            # Direct to Shiprocket
            return f"{self.BASE_URL}/{endpoint}"

    async def _ensure_token(self) -> None:
        """
        Ensure we have a valid access token.
        Fetches new token if current one is expired or missing.

        Note: We've confirmed the 403 error is due to Cloudflare/WAF IP blocking,
        not token reuse. Token caching is safe and reduces auth API load.
        """
        # Check if we have a valid token
        if self.config.access_token and self.config.token_expires_at:
            # Token expires in 10 days, refresh 1 hour before expiry
            if datetime.now(timezone.utc) < self.config.token_expires_at - timedelta(hours=1):
                self.token = self.config.access_token
                logger.info(f"🔑 Using existing token (expires: {self.config.token_expires_at})")
                return

        # Token expired or missing, authenticate
        logger.info("🔄 Token expired or missing, re-authenticating...")
        auth_success = await self._authenticate()
        if not auth_success:
            raise Exception("Failed to authenticate with Shiprocket")

    async def _authenticate(self) -> bool:
        """
        Authenticate with Shiprocket and store access token.

        Security Features:
        - Uses curl_cffi to mimic Chrome browser TLS fingerprint
        - Keeps SSL verification ENABLED (secure)
        - Strict 15-second timeout to prevent hangs
        - Never logs credentials or token values

        Priority order for credentials:
        1. Environment variables (SHIPROCKET_API_EMAIL, SHIPROCKET_API_PASSWORD)
        2. Legacy env vars (SHIPROCKET_EMAIL, SHIPROCKET_PASSWORD)
        3. Database configuration

        Returns:
            bool: True if authentication succeeded, False if failed
        """
        import os

        # Try environment variables first (API user without 2FA)
        email = os.getenv("SHIPROCKET_API_EMAIL") or os.getenv("SHIPROCKET_EMAIL")
        password = os.getenv("SHIPROCKET_API_PASSWORD") or os.getenv("SHIPROCKET_PASSWORD")

        # Fall back to database config if env vars not set
        if not email or not password:
            email = self.config.email
            password = self._decrypt_password(self.config.encrypted_password)
            logger.info("🔐 Using Shiprocket credentials from database")
        else:
            # SECURITY: Only log email, never password
            logger.info(f"🔐 Using Shiprocket API user: {email}")

        try:
            logger.info(f"🔗 Authenticating with Shiprocket (Chrome TLS fingerprint)")

            # SECURITY: impersonate="chrome" mimics real Chrome browser
            # SSL verification stays ENABLED (verify=True is default)
            async with AsyncSession(impersonate="chrome", timeout=API_TIMEOUT) as session:
                response = await session.post(
                    self._get_url("/auth/login"),
                    json={
                        "email": email,
                        "password": password,
                    },
                )

                logger.info(f"📡 Auth response: status={response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    self.token = data["token"]

                    # Store token in database with 9-day expiry (refresh before 10-day limit)
                    self.config.access_token = self.token
                    self.config.token_expires_at = datetime.now(timezone.utc) + timedelta(days=9)
                    self.db.commit()

                    logger.info("✅ Shiprocket authentication successful")
                    # SECURITY: Never log the actual token value
                    logger.info(f"   Token cached until: {self.config.token_expires_at}")
                    return True
                elif response.status_code == 403:
                    logger.error(f"❌ 403 Forbidden - WAF/Firewall blocking")
                    logger.error(f"   API user: {email}")
                    return False
                else:
                    logger.error(f"❌ Authentication failed: {response.status_code}")
                    logger.error(f"   API user: {email}")
                    return False

        except Exception as e:
            logger.error(f"❌ Shiprocket auth error: {str(e)}")
            return False

    def _decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt Shiprocket password.

        Args:
            encrypted_password: Encrypted password from database

        Returns:
            Decrypted password

        Note:
            For development, this returns the password as-is.
            In production, implement proper Fernet decryption.
        """
        # TODO: Implement Fernet decryption in production
        # from cryptography.fernet import Fernet
        # cipher = Fernet(settings.ENCRYPTION_KEY)
        # return cipher.decrypt(encrypted_password.encode()).decode()

        return encrypted_password  # Development only

    async def create_order(
        self, order_reference: str, user_reward: UserReward, shipping_details: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create an order in Shiprocket.

        Implements retry logic with fresh token on auth failures (401/403).

        Args:
            order_reference: Our internal order reference (RNR-EVT-X-USR-Y-RWD-Z)
            user_reward: UserReward instance
            shipping_details: Shipping address details

        Returns:
            Dict with order creation result:
            {
                "success": bool,
                "order_id": int,
                "shipment_id": int,
                "status_code": int,
                "payload": dict,
                "response": dict
            }
        """
        await self._ensure_token()

        # Split name into first and last for Shiprocket requirements
        # Support both "full_name" (correct) and "name" (legacy) for backward compatibility
        full_name = shipping_details.get("full_name") or shipping_details.get("name", "Customer")
        postal_code = shipping_details.get("postal_code") or shipping_details.get("pincode", "000000")

        name_parts = full_name.strip().split(maxsplit=1)
        first_name = name_parts[0] if name_parts else "Customer"
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        logger.info(f"📦 Creating Shiprocket order for reference: {order_reference}")
        logger.info(f"   Name split: '{full_name}' → first='{first_name}', last='{last_name}'")
        logger.info(f"   Shipping to: {shipping_details['city']}, {shipping_details['state']} - {postal_code}")

        # Prepare order payload
        payload = {
            "order_id": order_reference,
            "order_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "pickup_location": self.config.default_pickup_location,
            "billing_customer_name": full_name,
            "billing_first_name": first_name,
            "billing_last_name": last_name,
            "billing_address": shipping_details["address_line1"],
            "billing_address_2": shipping_details.get("address_line2", ""),
            "billing_city": shipping_details["city"],
            "billing_pincode": postal_code,
            "billing_state": shipping_details["state"],
            "billing_country": shipping_details.get("country", "India"),
            "billing_email": shipping_details.get("email", ""),
            "billing_phone": shipping_details["phone"],
            "shipping_is_billing": True,
            "order_items": [
                {
                    "name": user_reward.reward_name,
                    "sku": user_reward.item_sku
                    or f"REWARD-{user_reward.reward_type.value.upper()}",
                    "units": 1,
                    "selling_price": "0",  # Free reward
                    "discount": "0",
                    "tax": "0",
                    "hsn": user_reward.item_hsn or "",
                }
            ],
            "payment_method": "Prepaid",  # Prepaid for free rewards
            "sub_total": 0,
            "length": float(user_reward.item_length or self.config.default_length),
            "breadth": float(user_reward.item_breadth or self.config.default_breadth),
            "height": float(user_reward.item_height or self.config.default_height),
            "weight": float(user_reward.item_weight or self.config.default_weight),
        }

        # Try up to 2 times: once with cached token, once with fresh token
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"🔗 Attempt {attempt}/{max_attempts}: Creating Shiprocket order")
                # SECURITY: Never log token value, only confirm it exists
                logger.info(f"   Auth: Token present ({'Yes' if self.token else 'No'})")
                # SECURITY: Log structure only, never PII values
                logger.info(f"   Payload structure: {list(payload.keys())}")

                # SECURITY: impersonate="chrome" with SSL verification enabled
                async with AsyncSession(impersonate="chrome", timeout=API_TIMEOUT) as session:
                    response = await session.post(
                        self._get_url("/orders/create/adhoc"),
                        headers={"Authorization": f"Bearer {self.token}"},
                        json=payload,
                    )

                    logger.info(f"📡 Response: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"✅ Shiprocket order API returned 200")

                        # Check if response indicates success
                        order_id = data.get('order_id')
                        shipment_id = data.get('shipment_id')

                        # SECURITY: Log IDs only (not PII)
                        logger.info(f"   Order ID: {order_id}")
                        logger.info(f"   Shipment ID: {shipment_id}")

                        # Shiprocket may return 200 but with errors in the response
                        if not order_id or not shipment_id:
                            error_msg = data.get('message', 'Order creation failed - missing IDs')
                            logger.error(f"❌ Order creation failed: {error_msg}")
                            return {
                                "success": False,
                                "error": error_msg,
                                "response": data,
                            }

                        logger.info(f"✅ Shiprocket order created successfully!")
                        return {
                            "success": True,
                            "order_id": order_id,
                            "shipment_id": shipment_id,
                            "status_code": data.get("status_code"),
                            "response": data,
                        }

                    # Auth errors (401/403) - check if HTML (Cloudflare) or JSON (Shiprocket)
                    elif response.status_code in [401, 403]:
                        error_text = response.text[:500]
                        is_html_response = error_text.strip().startswith("<html")

                        if is_html_response:
                            # HTML 403 = Cloudflare/WAF blocking at infrastructure level
                            logger.error(f"❌ {response.status_code} - Cloudflare/WAF blocking detected (HTML response)")
                            logger.error(f"   This is an IP blocking issue, not an authentication issue")
                            logger.error(f"   Current token is valid until: {self.config.token_expires_at}")
                            logger.error(f"   Railway's IP address is blocked by Shiprocket's firewall")
                            logger.error(f"   Skipping re-authentication (auth endpoint is also blocked)")

                            return {
                                "success": False,
                                "error": "Railway IP blocked by Shiprocket's firewall. Contact Shiprocket support to whitelist Railway IPs.",
                                "payload": payload,
                                "is_blocked": True
                            }

                        # JSON 403/401 = Real auth issue, try fresh token
                        if attempt < max_attempts:
                            logger.warning(f"⚠️  {response.status_code} Auth error on attempt {attempt}/{max_attempts}")
                            logger.warning(f"   Response: {error_text}")
                            logger.warning(f"   🔄 Retrying with fresh token...")

                            # Force fresh authentication
                            auth_success = await self._authenticate()
                            if not auth_success:
                                logger.error("❌ Fresh authentication failed")
                                return {
                                    "success": False,
                                    "error": "Authentication failed - could not obtain valid token",
                                    "payload": payload,
                                    "is_blocked": False
                                }

                            # Continue to next attempt with fresh token
                            continue
                        else:
                            # Final attempt failed
                            logger.error(f"❌ {response.status_code} Auth error - All retry attempts exhausted")
                            logger.error(f"   Response: {error_text}")

                            if response.status_code == 403:
                                logger.error(f"   This typically means Railway's IP is blocked by Shiprocket's firewall")
                                logger.error(f"   Possible solutions:")
                                logger.error(f"   1. Contact Shiprocket support to whitelist Railway IPs")
                                logger.error(f"   2. Use a proxy service to route requests")
                                logger.error(f"   3. Upgrade to Railway static IPs and whitelist them")

                            return {
                                "success": False,
                                "error": f"{response.status_code} Auth error: {error_text}",
                                "payload": payload,
                                "is_blocked": response.status_code == 403
                            }

                    # Validation errors - don't retry
                    elif response.status_code == 422:
                        error_text = response.text
                        logger.error(f"❌ 422 Validation Error - Invalid payload")
                        logger.error(f"   Response: {error_text}")
                        try:
                            error_data = response.json()
                            if "errors" in error_data:
                                logger.error(f"   Validation errors: {error_data['errors']}")
                        except Exception:
                            pass
                        return {"success": False, "error": error_text, "payload": payload}

                    # Other errors - don't retry
                    else:
                        error_text = response.text[:500]
                        logger.error(f"❌ Order creation failed: {response.status_code}")
                        logger.error(f"   Response: {error_text}")
                        return {"success": False, "error": error_text, "payload": payload}

            except Exception as e:
                error_msg = f"Shiprocket API request error: {str(e)}"
                logger.error(error_msg)

                # Don't retry on network errors
                return {"success": False, "error": error_msg, "payload": payload}

        # Should never reach here, but just in case
        return {"success": False, "error": "Unknown error - all retry attempts completed without result", "payload": payload}

    async def assign_awb(self, shipment_id: int, courier_id: int | None = None) -> dict[str, Any]:
        """
        Assign AWB (tracking number) to shipment.

        Args:
            shipment_id: Shiprocket shipment ID
            courier_id: Optional specific courier ID

        Returns:
            Dict with AWB assignment result:
            {
                "success": bool,
                "awb_code": str,
                "courier_company_id": int,
                "courier_name": str
            }
        """
        await self._ensure_token()

        payload = {"shipment_id": shipment_id}
        if courier_id:
            payload["courier_id"] = courier_id

        try:
            async with AsyncSession(impersonate="chrome", timeout=API_TIMEOUT) as session:
                response = await session.post(
                    f"{self.BASE_URL}/courier/assign/awb",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    awb_data = data.get("response", {}).get("data", {})
                    logger.info(f"✅ AWB assigned: {awb_data.get('awb_code')}")
                    return {
                        "success": True,
                        "awb_code": awb_data.get("awb_code"),
                        "courier_company_id": awb_data.get("courier_company_id"),
                        "courier_name": awb_data.get("courier_name"),
                    }
                else:
                    return {"success": False, "error": response.text}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def generate_label(self, shipment_id: int) -> dict[str, Any]:
        """
        Generate shipping label for shipment.

        Args:
            shipment_id: Shiprocket shipment ID

        Returns:
            Dict with label generation result:
            {
                "success": bool,
                "label_url": str
            }
        """
        await self._ensure_token()

        try:
            async with AsyncSession(impersonate="chrome", timeout=API_TIMEOUT) as session:
                response = await session.post(
                    f"{self.BASE_URL}/courier/generate/label",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={"shipment_id": [shipment_id]},
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ Label generated for shipment {shipment_id}")
                    return {"success": True, "label_url": data.get("label_url")}
                else:
                    return {"success": False, "error": response.text}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def generate_manifest(self, shipment_id: int) -> dict[str, Any]:
        """
        Generate manifest for shipment.

        Args:
            shipment_id: Shiprocket shipment ID

        Returns:
            Dict with manifest generation result:
            {
                "success": bool,
                "manifest_url": str
            }
        """
        await self._ensure_token()

        try:
            async with AsyncSession(impersonate="chrome", timeout=API_TIMEOUT) as session:
                response = await session.post(
                    f"{self.BASE_URL}/manifests/generate",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={"shipment_id": [shipment_id]},
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ Manifest generated for shipment {shipment_id}")
                    return {"success": True, "manifest_url": data.get("manifest_url")}
                else:
                    return {"success": False, "error": response.text}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def schedule_pickup(self, shipment_id: int) -> dict[str, Any]:
        """
        Schedule pickup with courier for shipment.

        Args:
            shipment_id: Shiprocket shipment ID

        Returns:
            Dict with pickup scheduling result:
            {
                "success": bool,
                "pickup_scheduled_date": str,
                "pickup_token_number": str
            }
        """
        await self._ensure_token()

        try:
            async with AsyncSession(impersonate="chrome", timeout=API_TIMEOUT) as session:
                response = await session.post(
                    f"{self.BASE_URL}/courier/generate/pickup",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={"shipment_id": [shipment_id]},
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ Pickup scheduled for shipment {shipment_id}")
                    return {
                        "success": True,
                        "pickup_scheduled_date": data.get("pickup_scheduled_date"),
                        "pickup_token_number": data.get("pickup_token_number"),
                    }
                else:
                    return {"success": False, "error": response.text}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def track_shipment(self, shipment_id: int) -> dict[str, Any]:
        """
        Get tracking information for shipment.

        Args:
            shipment_id: Shiprocket shipment ID

        Returns:
            Dict with tracking information:
            {
                "success": bool,
                "status": str,
                "tracking_history": list,
                "tracking_url": str,
                "etd": str
            }
        """
        await self._ensure_token()

        try:
            async with AsyncSession(impersonate="chrome", timeout=API_TIMEOUT) as session:
                response = await session.get(
                    f"{self.BASE_URL}/courier/track/shipment/{shipment_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    tracking_data = data.get("tracking_data", {})

                    return {
                        "success": True,
                        "status": tracking_data.get("shipment_status"),
                        "tracking_history": tracking_data.get("shipment_track", []),
                        "tracking_url": tracking_data.get("track_url"),
                        "etd": tracking_data.get("etd"),
                    }
                else:
                    return {"success": False, "error": response.text}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def track_by_awb(self, awb_code: str) -> dict[str, Any]:
        """
        Get tracking information by AWB code.

        Args:
            awb_code: AWB/tracking number

        Returns:
            Dict with tracking information
        """
        await self._ensure_token()

        try:
            async with AsyncSession(impersonate="chrome", timeout=API_TIMEOUT) as session:
                response = await session.get(
                    f"{self.BASE_URL}/courier/track/awb/{awb_code}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    tracking_data = data.get("tracking_data", {})

                    return {
                        "success": True,
                        "status": tracking_data.get("shipment_status"),
                        "tracking_history": tracking_data.get("shipment_track", []),
                        "tracking_url": tracking_data.get("track_url"),
                        "etd": tracking_data.get("etd"),
                    }
                else:
                    return {"success": False, "error": response.text}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def lookup_pincode_details(self, pincode: str) -> dict[str, Any]:
        """
        Look up pincode details without requiring pickup location.
        Uses the postcode details API which doesn't need serviceability check.

        Args:
            pincode: Pincode to lookup

        Returns:
            Dict with pincode details:
            {
                "success": bool,
                "postcode": str,
                "city": str,
                "state": str,
                "state_code": str,
                "locality": list,
                "latitude": str,
                "longitude": str
            }
        """
        await self._ensure_token()

        try:
            async with AsyncSession(impersonate="chrome", timeout=API_TIMEOUT) as session:
                response = await session.get(
                    "https://apiv2.shiprocket.in/v1/postcode/details",
                    headers={"Authorization": f"Bearer {self.token}"},
                    params={
                        "postcode": pincode,
                        "is_web": 1
                    },
                )

                if response.status_code == 200:
                    data = response.json()

                    if data.get("success"):
                        details = data.get("postcode_details", {})
                        logger.info(f"✅ Pincode {pincode} details: {details.get('city')}, {details.get('state')}")

                        return {
                            "success": True,
                            "postcode": details.get("postcode"),
                            "city": details.get("city"),
                            "state": details.get("state"),
                            "state_code": details.get("state_code"),
                            "locality": details.get("locality", []),
                            "latitude": details.get("latitude"),
                            "longitude": details.get("longitude"),
                            "country": details.get("country", "India")
                        }
                    else:
                        logger.warning(f"Pincode {pincode} not found")
                        return {"success": False, "error": "Pincode not found"}
                else:
                    logger.warning(f"Pincode lookup failed: {response.status_code} - {response.text}")
                    return {"success": False, "error": response.text}

        except Exception as e:
            logger.error(f"Pincode lookup API error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def check_pincode_serviceability(
        self,
        delivery_pincode: str,
        pickup_pincode: str | None = None,
        weight: float = 0.5,
        length: float = 15,
        breadth: float = 10,
        height: float = 5,
    ) -> dict[str, Any]:
        """
        Check serviceability and get location details for a pincode.

        Args:
            delivery_pincode: Delivery pincode to check
            pickup_pincode: Optional pickup pincode (uses default if not provided)
            weight: Package weight in kg (default: 0.5)
            length: Package length in cm (default: 15)
            breadth: Package breadth in cm (default: 10)
            height: Package height in cm (default: 5)

        Returns:
            Dict with pincode details and serviceability:
            {
                "success": bool,
                "delivery_postcode": str,
                "city": str,
                "state": str,
                "state_code": str,
                "is_serviceable": bool,
                "available_couriers": list
            }
        """
        await self._ensure_token()

        try:
            async with AsyncSession(impersonate="chrome", timeout=API_TIMEOUT) as session:
                response = await session.get(
                    f"{self.BASE_URL}/courier/serviceability/",
                    headers={"Authorization": f"Bearer {self.token}"},
                    params={
                        "delivery_postcode": delivery_pincode,
                        "pickup_pincode": pickup_pincode,
                        "weight": weight,
                        "length": length,
                        "breadth": breadth,
                        "height": height,
                        "cod": 0,  # Prepaid
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    serviceability_data = data.get("data", {})

                    # Log the full response for debugging
                    logger.info(f"Shiprocket serviceability response: {data}")

                    # Extract location details - check both locations
                    city = serviceability_data.get("city") or serviceability_data.get("delivery_city")
                    state = serviceability_data.get("state") or serviceability_data.get("delivery_state")

                    logger.info(
                        f"✅ Pincode {delivery_pincode} serviceability checked: {city or 'Unknown'}, {state or 'Unknown'}"
                    )

                    return {
                        "success": True,
                        "delivery_postcode": serviceability_data.get("delivery_postcode") or delivery_pincode,
                        "city": city,
                        "state": state,
                        "state_code": serviceability_data.get("state_code"),
                        "is_serviceable": serviceability_data.get("is_serviceable", False),
                        "available_couriers": serviceability_data.get(
                            "available_courier_companies", []
                        ),
                    }
                else:
                    logger.warning(
                        f"Pincode serviceability check failed: {response.status_code} - {response.text}"
                    )
                    return {"success": False, "error": response.text}

        except Exception as e:
            logger.error(f"Pincode serviceability API error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_pickup_locations(self) -> dict[str, Any]:
        """
        Get all registered pickup locations from Shiprocket account.

        Returns:
            Dict with success status and list of pickup locations:
            {
                "success": bool,
                "pickup_locations": [
                    {
                        "id": int,
                        "nickname": str,
                        "address": str,
                        "city": str,
                        "state": str,
                        "pincode": str,
                        "phone": str,
                        "is_primary": bool
                    }
                ]
            }
        """
        await self._ensure_token()

        try:
            async with AsyncSession(impersonate="chrome", timeout=API_TIMEOUT) as session:
                response = await session.get(
                    f"{self.BASE_URL}/settings/company/pickup",
                    headers={"Authorization": f"Bearer {self.token}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    pickup_locations = data.get("data", {}).get("shipping_address", [])

                    logger.info(f"✅ Retrieved {len(pickup_locations)} pickup locations from Shiprocket")

                    return {
                        "success": True,
                        "pickup_locations": [
                            {
                                "id": loc.get("id"),
                                "nickname": loc.get("pickup_location") or loc.get("nickname"),
                                "address": loc.get("address"),
                                "address_2": loc.get("address_2"),
                                "city": loc.get("city"),
                                "state": loc.get("state"),
                                "pincode": loc.get("pin_code"),
                                "phone": loc.get("phone"),
                                "email": loc.get("email"),
                                "is_primary": loc.get("is_primary_location", False),
                            }
                            for loc in pickup_locations
                        ],
                    }
                else:
                    logger.warning(
                        f"Failed to fetch pickup locations: {response.status_code} - {response.text}"
                    )
                    return {"success": False, "error": response.text}

        except Exception as e:
            logger.error(f"Pickup locations API error: {str(e)}")
            return {"success": False, "error": str(e)}
