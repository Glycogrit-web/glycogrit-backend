"""
Shiprocket Service
Handles all Shiprocket API interactions for order creation, tracking, and label generation
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.user_reward import UserReward
from app.modules.shipping.domain.config import ShiprocketConfig

logger = logging.getLogger(__name__)


class ShiprocketService:
    """
    Service for interacting with Shiprocket API.
    Handles authentication, order creation, tracking, and shipping operations.
    """

    BASE_URL = "https://apiv2.shiprocket.in/v1/external"

    def __init__(self, db: Session):
        """
        Initialize Shiprocket service.

        Args:
            db: Database session
        """
        self.db = db
        self.config = self._get_config()
        self.token: str | None = None

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

    async def _ensure_token(self) -> None:
        """
        Ensure we have a valid access token.
        Fetches new token if current one is expired or missing.
        """
        # Check if we have a valid token
        if self.config.access_token and self.config.token_expires_at:
            # Token expires in 10 days, refresh 1 hour before expiry
            if datetime.utcnow() < self.config.token_expires_at - timedelta(hours=1):
                self.token = self.config.access_token
                return

        # Token expired or missing, authenticate
        await self._authenticate()

    async def _authenticate(self) -> None:
        """
        Authenticate with Shiprocket and store access token.

        Raises:
            Exception: If authentication fails
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/auth/login",
                    json={
                        "email": self.config.email,
                        "password": self._decrypt_password(self.config.encrypted_password),
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self.token = data["token"]

                    # Store token in database
                    self.config.access_token = self.token
                    self.config.token_expires_at = datetime.utcnow() + timedelta(days=10)
                    self.db.commit()

                    logger.info("✅ Shiprocket authentication successful")
                else:
                    error_msg = f"Shiprocket authentication failed: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

        except httpx.RequestError as e:
            error_msg = f"Shiprocket API request error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

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

        # Prepare order payload
        payload = {
            "order_id": order_reference,
            "order_date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "pickup_location": self.config.default_pickup_location,
            "billing_customer_name": shipping_details["full_name"],
            "billing_address": shipping_details["address_line1"],
            "billing_address_2": shipping_details.get("address_line2", ""),
            "billing_city": shipping_details["city"],
            "billing_pincode": shipping_details["postal_code"],
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

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/orders/create/adhoc",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ Shiprocket order created: {data.get('order_id')}")
                    return {
                        "success": True,
                        "order_id": data.get("order_id"),
                        "shipment_id": data.get("shipment_id"),
                        "status_code": data.get("status_code"),
                        "payload": payload,
                        "response": data,
                    }
                else:
                    error_msg = f"Order creation failed: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {"success": False, "error": response.text, "payload": payload}

        except httpx.RequestError as e:
            error_msg = f"Shiprocket API request error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "payload": payload}

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
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
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

        except httpx.RequestError as e:
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
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

        except httpx.RequestError as e:
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
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

        except httpx.RequestError as e:
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
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

        except httpx.RequestError as e:
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
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

        except httpx.RequestError as e:
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
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

        except httpx.RequestError as e:
            return {"success": False, "error": str(e)}
