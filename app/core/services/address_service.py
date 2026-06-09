"""
Address Service
Provides address validation, auto-fill, and normalization services
"""

import logging
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.core.schemas.address import AddressAutoFillResponse, PincodeDetails
from app.modules.shipping.integrations.shiprocket.client import ShiprocketService

logger = logging.getLogger(__name__)


class AddressService:
    """
    Service for address-related operations including:
    - Pincode lookup and validation
    - Address auto-fill from pincode
    - Address normalization
    - Serviceability checks
    """

    def __init__(self, db: Session):
        self.db = db
        self.shiprocket = ShiprocketService(db)

    async def lookup_pincode(self, pincode: str) -> Optional[PincodeDetails]:
        """
        Look up pincode details from Shiprocket API.

        Args:
            pincode: 6-digit Indian PIN code

        Returns:
            PincodeDetails with city, state, and serviceability info
            None if pincode not found or API error
        """
        try:
            # Ensure token is valid
            await self.shiprocket._ensure_token()

            # Call Shiprocket pincode API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.shiprocket.BASE_URL}/courier/serviceability/",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.shiprocket.token}",
                    },
                    params={
                        "pickup_postcode": self.shiprocket.config.default_pickup_location or "110001",
                        "delivery_postcode": pincode,
                        "weight": 0.5,
                        "cod": 0,
                    },
                )

                if response.status_code == 200:
                    data = response.json()

                    if data.get("status") == 200 and data.get("data"):
                        service_data = data["data"]

                        # Extract delivery postcode info
                        delivery_info = service_data.get("delivery_postcode_info", {})

                        if delivery_info:
                            return PincodeDetails(
                                pincode=pincode,
                                city=delivery_info.get("city", ""),
                                state=delivery_info.get("state", ""),
                                state_code=delivery_info.get("state_code"),
                                is_serviceable=service_data.get("is_serviceable", False),
                                region=delivery_info.get("region"),
                                delivery_days=service_data.get("estimated_delivery_days"),
                            )

                    logger.warning(f"Pincode {pincode} not found in Shiprocket database")
                    return None

                else:
                    logger.error(
                        f"Shiprocket pincode lookup failed with status {response.status_code}: {response.text}"
                    )
                    return None

        except httpx.RequestError as e:
            logger.error(f"Network error during pincode lookup for {pincode}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during pincode lookup for {pincode}: {str(e)}")
            return None

    async def auto_fill_address(self, pincode: str) -> Optional[AddressAutoFillResponse]:
        """
        Auto-fill address fields based on pincode.

        Args:
            pincode: 6-digit Indian PIN code

        Returns:
            AddressAutoFillResponse with city, state, and serviceability
            None if pincode not found
        """
        pincode_details = await self.lookup_pincode(pincode)

        if pincode_details:
            suggested_address = f"{pincode_details.city}, {pincode_details.state} - {pincode}"

            return AddressAutoFillResponse(
                pincode=pincode,
                city=pincode_details.city,
                state=pincode_details.state,
                state_code=pincode_details.state_code,
                is_serviceable=pincode_details.is_serviceable,
                suggested_address=suggested_address,
            )

        return None

    async def check_serviceability(self, pincode: str, weight: float = 0.5) -> bool:
        """
        Check if delivery is available to the given pincode.

        Args:
            pincode: 6-digit Indian PIN code
            weight: Package weight in kg (default: 0.5)

        Returns:
            True if serviceable, False otherwise
        """
        try:
            result = await self.shiprocket.check_pincode_serviceability(
                delivery_pincode=pincode,
                weight=weight,
            )

            return result.get("is_serviceable", False)

        except Exception as e:
            logger.error(f"Error checking serviceability for pincode {pincode}: {str(e)}")
            return False

    def normalize_address(self, address_data: dict) -> dict:
        """
        Normalize address data by:
        - Stripping whitespace
        - Capitalizing city/state
        - Ensuring consistent field names

        Args:
            address_data: Raw address dictionary

        Returns:
            Normalized address dictionary
        """
        normalized = {}

        # Normalize name
        if "name" in address_data and address_data["name"]:
            normalized["name"] = address_data["name"].strip().title()

        # Normalize phone
        if "phone" in address_data and address_data["phone"]:
            # Remove non-digit characters
            phone = "".join(filter(str.isdigit, address_data["phone"]))
            # Keep last 10 digits for Indian numbers
            normalized["phone"] = phone[-10:] if len(phone) >= 10 else phone

        # Normalize address lines
        for field in ["address_line1", "address_line2"]:
            if field in address_data and address_data[field]:
                normalized[field] = address_data[field].strip()

        # Normalize and capitalize location fields
        for field in ["city", "state"]:
            if field in address_data and address_data[field]:
                normalized[field] = address_data[field].strip().title()

        # Normalize pincode
        if "pincode" in address_data and address_data["pincode"]:
            # Extract only digits
            pincode = "".join(filter(str.isdigit, address_data["pincode"]))
            normalized["pincode"] = pincode

        # Handle postal_code -> pincode conversion
        if "postal_code" in address_data and "pincode" not in normalized:
            postal_code = "".join(filter(str.isdigit, address_data["postal_code"]))
            normalized["pincode"] = postal_code

        # Normalize country
        if "country" in address_data:
            normalized["country"] = address_data["country"].strip().title()
        else:
            normalized["country"] = "India"

        # Copy other fields as-is
        for field in ["email", "alternate_phone", "landmark", "special_instructions"]:
            if field in address_data and address_data[field]:
                normalized[field] = address_data[field].strip()

        return normalized

    def validate_address_completeness(self, address_data: dict) -> tuple[bool, list[str]]:
        """
        Validate if address has all required fields.

        Args:
            address_data: Address dictionary to validate

        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        required_fields = ["name", "phone", "address_line1", "city", "state", "pincode"]
        missing_fields = []

        for field in required_fields:
            if field not in address_data or not address_data[field]:
                missing_fields.append(field)

        is_valid = len(missing_fields) == 0
        return is_valid, missing_fields

    def convert_legacy_address(self, legacy_address: dict) -> dict:
        """
        Convert legacy address format to standardized format.
        Handles old field names like postal_code -> pincode.

        Args:
            legacy_address: Address with old field names

        Returns:
            Address with standardized field names
        """
        converted = {}

        # Field name mappings (old_name -> new_name)
        field_mappings = {
            "postal_code": "pincode",
            "shipping_postal_code": "pincode",
            "shipping_address_line1": "address_line1",
            "shipping_address_line2": "address_line2",
            "shipping_city": "city",
            "shipping_state": "state",
            "shipping_phone": "phone",
            "shipping_email": "email",
            "full_name": "name",
        }

        # Apply mappings
        for old_name, new_name in field_mappings.items():
            if old_name in legacy_address:
                converted[new_name] = legacy_address[old_name]

        # Copy fields that don't need conversion
        for field in ["name", "phone", "address_line1", "address_line2", "city", "state", "pincode", "country", "email"]:
            if field in legacy_address and field not in converted:
                converted[field] = legacy_address[field]

        return self.normalize_address(converted)
