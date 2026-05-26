"""
Shiprocket Service - Dummy Implementation
This is a placeholder service for future Shiprocket API integration.
"""

import uuid
from datetime import datetime, timedelta

from pydantic import BaseModel


class ShiprocketConfig(BaseModel):
    """Shiprocket configuration"""

    email: str = "admin@example.com"
    password: str = "dummy_password"
    base_url: str = "https://apiv2.shiprocket.in/v1/external"
    access_token: str | None = None


class ShippingAddress(BaseModel):
    """Shipping address model"""

    name: str
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str
    phone: str
    email: str | None = None


class OrderItem(BaseModel):
    """Order item model"""

    name: str
    sku: str
    units: int = 1
    selling_price: float = 0.0
    discount: float = 0.0
    weight: float = 0.5  # kg


class ShiprocketOrder(BaseModel):
    """Shiprocket order model"""

    order_id: str
    order_date: str
    pickup_location: str
    billing_customer_name: str
    billing_address: str
    billing_city: str
    billing_state: str
    billing_pincode: str
    billing_country: str
    billing_phone: str
    billing_email: str
    shipping_is_billing: bool = True
    order_items: list[OrderItem]
    payment_method: str = "Prepaid"
    sub_total: float = 0.0
    length: float = 10.0  # cm
    breadth: float = 10.0  # cm
    height: float = 5.0  # cm
    weight: float = 0.5  # kg


class TrackingInfo(BaseModel):
    """Tracking information model"""

    awb: str
    courier_name: str
    current_status: str
    shipment_status: int
    shipped_date: str | None = None
    delivered_date: str | None = None
    estimated_delivery_date: str | None = None
    origin: str | None = None
    destination: str | None = None
    tracking_url: str


class ShipmentResponse(BaseModel):
    """Shipment creation response"""

    order_id: int
    shipment_id: int
    awb_code: str
    courier_name: str
    courier_company_id: int
    status: str


class ShiprocketService:
    """
    Dummy Shiprocket Service for managing shipments.

    This is a placeholder implementation that simulates Shiprocket API behavior.
    When ready to integrate with real Shiprocket API, replace the dummy methods
    with actual API calls to Shiprocket endpoints.

    Shiprocket API Documentation: https://apidocs.shiprocket.in/
    """

    def __init__(self, config: ShiprocketConfig | None = None):
        """Initialize Shiprocket service"""
        self.config = config or ShiprocketConfig()
        self._access_token: str | None = None
        # Dummy in-memory storage for simulated shipments
        self._dummy_shipments: dict[str, dict] = {}

    async def authenticate(self) -> bool:
        """
        Authenticate with Shiprocket API.

        Real implementation would call:
        POST /auth/login
        {
            "email": "your_email",
            "password": "your_password"
        }

        Returns:
            bool: True if authentication successful
        """
        # Dummy implementation - always succeeds
        self._access_token = f"dummy_token_{uuid.uuid4().hex[:16]}"
        return True

    async def create_order(
        self, user_id: str, challenge_id: str, reward_name: str, shipping_address: ShippingAddress
    ) -> ShipmentResponse:
        """
        Create a new order in Shiprocket.

        Real implementation would call:
        POST /orders/create/adhoc

        Args:
            user_id: User ID
            challenge_id: Challenge ID
            reward_name: Name of the reward
            shipping_address: Shipping address details

        Returns:
            ShipmentResponse: Shipment details including AWB and tracking
        """
        # Dummy implementation
        order_id = int(datetime.now().timestamp())
        shipment_id = order_id + 1000
        awb_code = f"AWB{uuid.uuid4().hex[:12].upper()}"

        # Store dummy shipment data
        self._dummy_shipments[awb_code] = {
            "order_id": order_id,
            "shipment_id": shipment_id,
            "awb": awb_code,
            "courier_name": "BlueDart",
            "courier_company_id": 12,
            "status": "NEW",
            "created_at": datetime.now().isoformat(),
            "user_id": user_id,
            "challenge_id": challenge_id,
            "reward_name": reward_name,
            "shipping_address": shipping_address.dict(),
            "current_status": "Order Placed",
            "shipment_status": 1,
        }

        return ShipmentResponse(
            order_id=order_id,
            shipment_id=shipment_id,
            awb_code=awb_code,
            courier_name="BlueDart",
            courier_company_id=12,
            status="NEW",
        )

    async def track_shipment(self, awb_code: str) -> TrackingInfo:
        """
        Track a shipment by AWB code.

        Real implementation would call:
        GET /courier/track/awb/{awb_code}

        Args:
            awb_code: Air Waybill number

        Returns:
            TrackingInfo: Current tracking information
        """
        # Dummy implementation
        if awb_code in self._dummy_shipments:
            shipment = self._dummy_shipments[awb_code]
        else:
            # Generate dummy tracking info for unknown AWB
            shipment = {
                "awb": awb_code,
                "courier_name": "BlueDart",
                "current_status": "In Transit",
                "shipment_status": 6,
                "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
            }

        # Calculate estimated delivery (7 days from creation)
        created_date = datetime.fromisoformat(
            shipment.get("created_at", datetime.now().isoformat())
        )
        estimated_delivery = created_date + timedelta(days=7)

        return TrackingInfo(
            awb=awb_code,
            courier_name=shipment.get("courier_name", "BlueDart"),
            current_status=shipment.get("current_status", "In Transit"),
            shipment_status=shipment.get("shipment_status", 6),
            shipped_date=created_date.strftime("%Y-%m-%d"),
            estimated_delivery_date=estimated_delivery.strftime("%Y-%m-%d"),
            tracking_url=f"https://shiprocket.co/tracking/{awb_code}",
        )

    async def track_shipment_by_order_id(self, order_id: int) -> TrackingInfo:
        """
        Track a shipment by Shiprocket order ID.

        Real implementation would call:
        GET /courier/track/shipment/{shipment_id}

        Args:
            order_id: Shiprocket order ID

        Returns:
            TrackingInfo: Current tracking information
        """
        # Find shipment by order_id
        for awb, shipment in self._dummy_shipments.items():
            if shipment.get("order_id") == order_id:
                return await self.track_shipment(awb)

        # If not found, return dummy data
        return await self.track_shipment(f"AWB{str(order_id)[-12:]}")

    async def generate_label(self, shipment_id: int) -> str:
        """
        Generate shipping label for a shipment.

        Real implementation would call:
        POST /courier/generate/label

        Args:
            shipment_id: Shiprocket shipment ID

        Returns:
            str: URL to download the shipping label PDF
        """
        # Dummy implementation
        return f"https://shiprocket.co/labels/dummy_label_{shipment_id}.pdf"

    async def cancel_order(self, order_id: int) -> bool:
        """
        Cancel a Shiprocket order.

        Real implementation would call:
        POST /orders/cancel

        Args:
            order_id: Shiprocket order ID

        Returns:
            bool: True if cancellation successful
        """
        # Dummy implementation - find and update status
        for _awb, shipment in self._dummy_shipments.items():
            if shipment.get("order_id") == order_id:
                shipment["current_status"] = "Cancelled"
                shipment["shipment_status"] = 9
                return True
        return True

    async def get_courier_list(self) -> list[dict]:
        """
        Get list of available couriers.

        Real implementation would call:
        GET /courier/courierListWithCounts

        Returns:
            List[Dict]: List of available couriers
        """
        # Dummy implementation
        return [
            {
                "id": 12,
                "name": "BlueDart",
                "is_surface": False,
                "is_air": True,
                "estimated_delivery_days": "3-5",
            },
            {
                "id": 17,
                "name": "Delhivery",
                "is_surface": True,
                "is_air": False,
                "estimated_delivery_days": "5-7",
            },
            {
                "id": 25,
                "name": "DTDC",
                "is_surface": True,
                "is_air": True,
                "estimated_delivery_days": "4-6",
            },
        ]

    async def handle_webhook(self, webhook_data: dict) -> bool:
        """
        Handle Shiprocket webhook for shipment status updates.

        Webhook events include:
        - ORDER_CREATED
        - SHIPMENT_CREATED
        - IN_TRANSIT
        - OUT_FOR_DELIVERY
        - DELIVERED
        - CANCELLED
        - RTO_INITIATED
        - RTO_DELIVERED

        Args:
            webhook_data: Webhook payload from Shiprocket

        Returns:
            bool: True if webhook processed successfully
        """
        # Dummy implementation - extract relevant data
        awb = webhook_data.get("awb")
        status = webhook_data.get("current_status")
        shipment_status = webhook_data.get("shipment_status")

        if awb and awb in self._dummy_shipments:
            self._dummy_shipments[awb]["current_status"] = status
            self._dummy_shipments[awb]["shipment_status"] = shipment_status

            if shipment_status == 7:  # Delivered
                self._dummy_shipments[awb]["delivered_date"] = datetime.now().isoformat()

        return True


# Shiprocket shipment status codes
SHIPMENT_STATUS_CODES = {
    1: "Pickup Scheduled",
    2: "Pickup Generated",
    3: "Pickup Queued",
    4: "Pickup Cancelled",
    5: "Pickup Error",
    6: "In Transit",
    7: "Delivered",
    8: "Cancelled",
    9: "RTO Initiated",
    10: "RTO Delivered",
    11: "Lost",
    12: "Damaged",
    13: "Out for Delivery",
    14: "Pickup Exception",
    15: "Undelivered",
    16: "Delayed",
    17: "Partial Delivered",
    18: "Destroyed",
    19: "Contact Customer Care",
}


def get_shipment_status_label(status_code: int) -> str:
    """Get human-readable label for shipment status code"""
    return SHIPMENT_STATUS_CODES.get(status_code, "Unknown")
