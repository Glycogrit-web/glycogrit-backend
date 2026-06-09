"""
Unified Address Schemas
Standardized address models used across the application
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.validators import IndianPhoneStr, IndianPinCodeStr, PersonNameStr


class AddressBase(BaseModel):
    """
    Base address schema with common fields.
    Used for Indian addresses with standardized field names.
    """

    name: PersonNameStr = Field(..., description="Full name of the recipient")
    phone: IndianPhoneStr = Field(..., description="10-digit Indian phone number")
    address_line1: str = Field(..., min_length=5, max_length=500, description="Street address, building name")
    address_line2: Optional[str] = Field(None, max_length=500, description="Apartment, suite, unit, floor, etc.")
    city: str = Field(..., min_length=2, max_length=100, description="City name")
    state: str = Field(..., min_length=2, max_length=100, description="State name")
    pincode: IndianPinCodeStr = Field(..., description="6-digit Indian PIN code")
    country: str = Field(default="India", max_length=100, description="Country (defaults to India)")

    @field_validator("address_line1", "address_line2")
    @classmethod
    def validate_address_lines(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace and validate address lines"""
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Address line cannot be empty or only whitespace")
        return v

    @field_validator("city", "state")
    @classmethod
    def validate_location_fields(cls, v: str) -> str:
        """Strip and capitalize location fields"""
        v = v.strip()
        if not v:
            raise ValueError("City and state cannot be empty")
        return v.title()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Rajesh Kumar",
                "phone": "9876543210",
                "address_line1": "123, MG Road",
                "address_line2": "Near City Mall, Apt 4B",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
                "country": "India",
            }
        }


class ShippingAddressCreate(AddressBase):
    """
    Schema for creating a new shipping address.
    Extends AddressBase with additional shipping-specific fields.
    """

    email: Optional[str] = Field(None, max_length=255, description="Email for shipping notifications")
    alternate_phone: Optional[IndianPhoneStr] = Field(None, description="Alternate contact number")
    landmark: Optional[str] = Field(None, max_length=200, description="Nearby landmark for easy location")
    special_instructions: Optional[str] = Field(None, max_length=500, description="Delivery instructions")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Rajesh Kumar",
                "phone": "9876543210",
                "address_line1": "123, MG Road",
                "address_line2": "Near City Mall, Apt 4B",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
                "country": "India",
                "email": "rajesh@example.com",
                "alternate_phone": "9123456789",
                "landmark": "Opposite ICICI Bank",
                "special_instructions": "Call before delivery",
            }
        }


class ShippingAddressUpdate(BaseModel):
    """
    Schema for updating an existing shipping address.
    All fields are optional.
    """

    name: Optional[PersonNameStr] = None
    phone: Optional[IndianPhoneStr] = None
    address_line1: Optional[str] = Field(None, min_length=5, max_length=500)
    address_line2: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=100)
    pincode: Optional[IndianPinCodeStr] = None
    country: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    alternate_phone: Optional[IndianPhoneStr] = None
    landmark: Optional[str] = Field(None, max_length=200)
    special_instructions: Optional[str] = Field(None, max_length=500)


class ShippingAddressResponse(AddressBase):
    """
    Schema for shipping address in API responses.
    Includes all address fields plus metadata.
    """

    email: Optional[str] = None
    alternate_phone: Optional[str] = None
    landmark: Optional[str] = None
    special_instructions: Optional[str] = None

    class Config:
        from_attributes = True


class UserProfileAddress(BaseModel):
    """
    Simplified address for user profile.
    Stores only city, state, pincode for user location.
    """

    city: Optional[str] = Field(None, max_length=100, description="City name")
    state: Optional[str] = Field(None, max_length=100, description="State name")
    pincode: Optional[IndianPinCodeStr] = Field(None, description="6-digit Indian PIN code")
    country: Optional[str] = Field(default="India", max_length=100, description="Country")

    @field_validator("city", "state")
    @classmethod
    def validate_location(cls, v: Optional[str]) -> Optional[str]:
        """Strip and capitalize location fields"""
        if v is None:
            return None
        v = v.strip()
        return v.title() if v else None

    class Config:
        json_schema_extra = {
            "example": {
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
                "country": "India",
            }
        }


class PincodeDetails(BaseModel):
    """
    Response schema for pincode lookup.
    Returns city, state, and serviceability information.
    """

    pincode: str = Field(..., description="6-digit PIN code")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State name")
    state_code: Optional[str] = Field(None, description="State code")
    is_serviceable: bool = Field(..., description="Whether delivery is available to this pincode")
    region: Optional[str] = Field(None, description="Region/zone")
    delivery_days: Optional[str] = Field(None, description="Estimated delivery time")

    class Config:
        json_schema_extra = {
            "example": {
                "pincode": "400001",
                "city": "Mumbai",
                "state": "Maharashtra",
                "state_code": "MH",
                "is_serviceable": True,
                "region": "West",
                "delivery_days": "3-5 days",
            }
        }


class AddressAutoFillRequest(BaseModel):
    """
    Request schema for address auto-fill by pincode.
    """

    pincode: IndianPinCodeStr = Field(..., description="6-digit PIN code to lookup")

    class Config:
        json_schema_extra = {"example": {"pincode": "400001"}}


class AddressAutoFillResponse(BaseModel):
    """
    Response schema for address auto-fill.
    Returns pre-filled city and state based on pincode.
    """

    pincode: str
    city: str
    state: str
    state_code: Optional[str] = None
    is_serviceable: bool
    suggested_address: Optional[str] = Field(None, description="Full address suggestion if available")

    class Config:
        json_schema_extra = {
            "example": {
                "pincode": "400001",
                "city": "Mumbai",
                "state": "Maharashtra",
                "state_code": "MH",
                "is_serviceable": True,
                "suggested_address": "Mumbai, Maharashtra - 400001",
            }
        }
