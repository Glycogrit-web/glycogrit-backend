"""
Address API Endpoints
Provides address auto-fill and validation services
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.schemas.address import AddressAutoFillResponse, PincodeDetails
from app.core.services.address_service import AddressService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/address", tags=["address"])


@router.get(
    "/pincode/{pincode}",
    response_model=PincodeDetails,
    summary="Lookup pincode details",
    description="Get city, state, and serviceability information for a given pincode",
)
async def lookup_pincode(
    pincode: str = Path(..., description="6-digit Indian PIN code", pattern="^[0-9]{6}$"),
    db: Session = Depends(get_db),
):
    """
    Look up pincode details from Shiprocket.

    Returns:
    - City and state for the pincode
    - Whether delivery is serviceable
    - Estimated delivery time

    This endpoint is useful for:
    - Validating user-entered pincodes
    - Auto-filling city/state fields
    - Checking delivery availability
    """
    try:
        service = AddressService(db)
        result = await service.lookup_pincode(pincode)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pincode {pincode} not found or not serviceable",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up pincode {pincode}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to lookup pincode details",
        )


@router.get(
    "/auto-fill/{pincode}",
    response_model=AddressAutoFillResponse,
    summary="Auto-fill address from pincode",
    description="Get pre-filled city and state based on pincode for address forms",
)
async def auto_fill_address(
    pincode: str = Path(..., description="6-digit Indian PIN code", pattern="^[0-9]{6}$"),
    db: Session = Depends(get_db),
):
    """
    Auto-fill address fields based on pincode.

    This endpoint is designed for frontend forms where users enter pincode first,
    and the city/state fields are automatically populated.

    Returns:
    - Pre-filled city and state
    - Serviceability status
    - Suggested full address string

    Example usage:
    1. User enters pincode: "400001"
    2. Frontend calls this endpoint
    3. Response auto-fills: city="Mumbai", state="Maharashtra"
    4. User completes remaining fields (name, address lines)
    """
    try:
        service = AddressService(db)
        result = await service.auto_fill_address(pincode)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unable to auto-fill address for pincode {pincode}. Please enter city and state manually.",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error auto-filling address for pincode {pincode}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to auto-fill address",
        )


@router.get(
    "/serviceability/{pincode}",
    summary="Check delivery serviceability",
    description="Check if delivery is available to the given pincode",
)
async def check_serviceability(
    pincode: str = Path(..., description="6-digit Indian PIN code", pattern="^[0-9]{6}$"),
    weight: float = 0.5,
    db: Session = Depends(get_db),
):
    """
    Check if delivery is serviceable to the given pincode.

    Query Parameters:
    - weight: Package weight in kg (default: 0.5)

    Returns:
    - is_serviceable: Boolean indicating delivery availability
    - pincode: The checked pincode
    - message: User-friendly message

    This is useful for:
    - Validating shipping addresses before order creation
    - Showing delivery availability on product pages
    - Filtering out non-serviceable regions
    """
    try:
        service = AddressService(db)
        is_serviceable = await service.check_serviceability(pincode, weight)

        return {
            "is_serviceable": is_serviceable,
            "pincode": pincode,
            "message": (
                f"Delivery available to pincode {pincode}"
                if is_serviceable
                else f"Delivery not available to pincode {pincode}"
            ),
        }

    except Exception as e:
        logger.error(f"Error checking serviceability for pincode {pincode}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check serviceability",
        )
