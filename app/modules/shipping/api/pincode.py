"""
Pincode Lookup API Endpoints

Standalone endpoint that calls Shiprocket API directly without database dependencies.
This ensures it works across all branch configurations.
"""

import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pincode", tags=["pincode"])


async def check_shiprocket_pincode(pincode: str) -> dict[str, Any]:
    """
    Check pincode serviceability using Shiprocket API directly.

    This is a standalone function that doesn't require database or Shiprocket models.
    It uses environment variables for authentication.

    Args:
        pincode: 6-digit Indian pincode

    Returns:
        Dict with location details and serviceability info
    """
    # Get Shiprocket credentials from environment
    shiprocket_email = os.getenv("SHIPROCKET_EMAIL")
    shiprocket_password = os.getenv("SHIPROCKET_PASSWORD")

    if not shiprocket_email or not shiprocket_password:
        # If Shiprocket not configured, fall back to a simple lookup
        # This prevents breaking the app if Shiprocket is not set up
        logger.warning("Shiprocket credentials not configured, pincode lookup unavailable")
        return {
            "success": False,
            "error": "Pincode lookup service not configured"
        }

    base_url = "https://apiv2.shiprocket.in/v1/external"

    try:
        # Step 1: Authenticate with Shiprocket
        async with httpx.AsyncClient(timeout=10.0) as client:
            auth_response = await client.post(
                f"{base_url}/auth/login",
                json={
                    "email": shiprocket_email,
                    "password": shiprocket_password,
                },
            )

            if auth_response.status_code != 200:
                logger.error(f"Shiprocket auth failed: {auth_response.status_code}")
                return {
                    "success": False,
                    "error": "Authentication failed"
                }

            token = auth_response.json().get("token")

            # Step 2: Check pincode serviceability
            serviceability_response = await client.get(
                f"{base_url}/courier/serviceability/",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "delivery_postcode": pincode,
                    "pickup_postcode": "110001",  # Default Delhi pincode
                    "weight": 0.5,
                    "cod": 0,
                },
            )

            if serviceability_response.status_code == 200:
                data = serviceability_response.json()
                serviceability_data = data.get("data", {})

                return {
                    "success": True,
                    "delivery_postcode": serviceability_data.get("delivery_postcode"),
                    "city": serviceability_data.get("city"),
                    "state": serviceability_data.get("state"),
                    "state_code": serviceability_data.get("state_code"),
                    "is_serviceable": serviceability_data.get("is_serviceable", False),
                }
            else:
                logger.warning(f"Serviceability check failed: {serviceability_response.status_code}")
                return {
                    "success": False,
                    "error": f"Pincode {pincode} not found"
                }

    except httpx.RequestError as e:
        logger.error(f"Shiprocket API error: {str(e)}")
        return {
            "success": False,
            "error": "Service temporarily unavailable"
        }
    except Exception as e:
        logger.error(f"Unexpected error in pincode lookup: {str(e)}")
        return {
            "success": False,
            "error": "Internal error"
        }


@router.get("/{pincode}")
async def lookup_pincode(pincode: str):
    """
    Lookup pincode details using Shiprocket API.

    Returns city, state, and serviceability information for the given pincode.
    This endpoint does not require authentication and works independently.

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
        # Check pincode serviceability
        result = await check_shiprocket_pincode(pincode)

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
        logger.error(f"Pincode lookup error for {pincode}: {str(e)}")

        raise HTTPException(
            status_code=500, detail="Unable to lookup pincode at this time. Please enter manually."
        )
