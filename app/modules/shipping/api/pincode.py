"""
Pincode Lookup API Endpoints

Standalone endpoint that calls Shiprocket API with proper token caching.
Uses the same authentication flow as the main Shiprocket client to avoid rate limiting.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pincode", tags=["pincode"])

# Token cache (in-memory, shared across requests)
_cached_token: Optional[str] = None
_token_expires_at: Optional[datetime] = None


async def _get_cached_token() -> Optional[str]:
    """
    Get cached authentication token if still valid.
    Tokens expire in 10 days, we cache for 9 days to be safe.

    Returns:
        Cached token if valid, None otherwise
    """
    global _cached_token, _token_expires_at

    if _cached_token and _token_expires_at:
        if datetime.utcnow() < _token_expires_at:
            logger.info(f"🔑 Using cached token (expires: {_token_expires_at})")
            return _cached_token

    logger.info("🔄 Token expired or missing, need to authenticate")
    return None


async def _authenticate_shiprocket() -> Optional[str]:
    """
    Authenticate with Shiprocket and cache the token.
    Uses proper authentication flow with token caching to avoid rate limiting.

    Returns:
        Authentication token if successful, None otherwise
    """
    global _cached_token, _token_expires_at

    # Get Shiprocket credentials from environment
    shiprocket_email = os.getenv("SHIPROCKET_API_EMAIL") or os.getenv("SHIPROCKET_EMAIL")
    shiprocket_password = os.getenv("SHIPROCKET_API_PASSWORD") or os.getenv("SHIPROCKET_PASSWORD")

    if not shiprocket_email or not shiprocket_password:
        logger.warning("Shiprocket credentials not configured")
        return None

    base_url = "https://apiv2.shiprocket.in/v1/external"

    try:
        logger.info(f"🔗 Authenticating with Shiprocket API user: {shiprocket_email}")

        async with httpx.AsyncClient(timeout=15.0) as client:
            auth_response = await client.post(
                f"{base_url}/auth/login",
                json={
                    "email": shiprocket_email,
                    "password": shiprocket_password,
                },
            )

            if auth_response.status_code == 200:
                data = auth_response.json()
                token = data.get("token")

                # Cache token for 9 days (expires in 10 days)
                _cached_token = token
                _token_expires_at = datetime.utcnow() + timedelta(days=9)

                logger.info(f"✅ Shiprocket authentication successful, token cached until: {_token_expires_at}")
                return token
            elif auth_response.status_code == 403:
                logger.error(f"❌ 403 Forbidden - WAF/Firewall blocking API user: {shiprocket_email}")
                return None
            else:
                logger.error(f"❌ Authentication failed: {auth_response.status_code}")
                return None

    except Exception as e:
        logger.error(f"❌ Shiprocket auth error: {str(e)}")
        return None


async def check_shiprocket_pincode(pincode: str) -> dict[str, Any]:
    """
    Check pincode details using Shiprocket postcode API with proper token caching.

    This function uses cached authentication tokens to avoid rate limiting and 403 errors.
    Tokens are cached for 9 days and reused across requests.

    Args:
        pincode: 6-digit Indian pincode

    Returns:
        Dict with location details and error handling
    """
    # Step 1: Get or refresh authentication token
    token = await _get_cached_token()

    if not token:
        # Need to authenticate
        token = await _authenticate_shiprocket()

        if not token:
            return {
                "success": False,
                "error": "Authentication failed",
                "error_type": "auth_failure"
            }

    # Step 2: Lookup pincode details using cached token
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            pincode_response = await client.get(
                "https://apiv2.shiprocket.in/v1/postcode/details",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "postcode": pincode,
                    "is_web": 1
                },
            )

            if pincode_response.status_code == 200:
                data = pincode_response.json()

                if data.get("success"):
                    details = data.get("postcode_details", {})
                    logger.info(f"✅ Pincode {pincode} lookup: {details.get('city')}, {details.get('state')}")

                    return {
                        "success": True,
                        "delivery_postcode": details.get("postcode"),
                        "city": details.get("city"),
                        "state": details.get("state"),
                        "state_code": details.get("state_code"),
                        "is_serviceable": True,  # Assume serviceable if pincode exists
                    }
                else:
                    logger.warning(f"Pincode {pincode} not found in Shiprocket database")
                    return {
                        "success": False,
                        "error": f"Pincode {pincode} not found",
                        "error_type": "pincode_not_found"
                    }
            elif pincode_response.status_code == 401:
                # Token expired, clear cache and retry once
                global _cached_token, _token_expires_at
                _cached_token = None
                _token_expires_at = None
                logger.warning("Token expired (401), will retry on next request")
                return {
                    "success": False,
                    "error": "Authentication expired",
                    "error_type": "auth_failure"
                }
            else:
                logger.warning(f"Pincode lookup failed: {pincode_response.status_code}")
                return {
                    "success": False,
                    "error": f"Pincode lookup failed",
                    "error_type": "pincode_not_found"
                }

    except httpx.TimeoutException as e:
        logger.error(f"Shiprocket API timeout: {str(e)}")
        return {
            "success": False,
            "error": "Service timeout",
            "error_type": "timeout"
        }
    except httpx.RequestError as e:
        logger.error(f"Shiprocket API error: {str(e)}")
        return {
            "success": False,
            "error": "Service temporarily unavailable",
            "error_type": "service_unavailable"
        }
    except Exception as e:
        logger.error(f"Unexpected error in pincode lookup: {str(e)}")
        return {
            "success": False,
            "error": "Internal error",
            "error_type": "service_unavailable"
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
            error_type = result.get("error_type", "unknown")

            # Auth failures or service issues: Return 200 with null data (silent fail)
            if error_type in ["auth_failure", "service_unavailable", "timeout"]:
                logger.warning(f"Pincode service unavailable: {error_type}")
                return {
                    "data": None,
                    "available": False,
                    "status": 200,
                    "message": "Service temporarily unavailable"
                }

            # Real pincode not found: Return 404 (let frontend handle gracefully)
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
