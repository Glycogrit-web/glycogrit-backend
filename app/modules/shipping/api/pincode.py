"""
Pincode Lookup API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.shipping.integrations.shiprocket.client import ShiprocketService

router = APIRouter(prefix="/pincode", tags=["pincode"])


@router.get("/{pincode}")
async def lookup_pincode(pincode: str, db: Session = Depends(get_db)):
    """
    Lookup pincode details using Shiprocket API.

    Returns city, state, and serviceability information for the given pincode.
    This endpoint does not require authentication.

    Args:
        pincode: 6-digit Indian pincode

    Returns:
        Dict with location details:
        - city: City name
        - state: State name
        - state_code: State code
        - is_serviceable: Whether delivery is available
    """
    # Validate pincode format
    if not pincode.isdigit() or len(pincode) != 6:
        raise HTTPException(status_code=400, detail="Invalid pincode format. Must be 6 digits.")

    try:
        # Create Shiprocket service
        shiprocket = ShiprocketService(db)

        # Check pincode serviceability
        result = await shiprocket.check_pincode_serviceability(delivery_pincode=pincode)

        if not result.get("success"):
            # Return 404 if pincode not found or API failed
            raise HTTPException(
                status_code=404, detail=result.get("error", "Pincode not found or not serviceable")
            )

        # Return location data
        return {
            "data": {
                "delivery_postcode": result.get("delivery_postcode"),
                "city": result.get("city"),
                "state": result.get("state"),
                "state_code": result.get("state_code"),
                "is_serviceable": result.get("is_serviceable", False),
            },
            "status": 200,
            "message": "Pincode lookup successful",
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log error and return generic error message
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Pincode lookup error for {pincode}: {str(e)}")

        raise HTTPException(
            status_code=500, detail="Unable to lookup pincode at this time. Please enter manually."
        )
