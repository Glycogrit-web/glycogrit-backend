"""
Pincode Lookup API Endpoints

Standalone endpoint that calls Shiprocket API with proper token caching.
Uses database-stored token from shiprocket_config table to avoid rate limiting.

Proxy Support:
Set SHIPROCKET_PROXY_URL environment variable to route requests through a proxy.
This is useful when Railway's IP is blocked by Shiprocket's firewall.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.shipping.domain.config import ShiprocketConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pincode", tags=["pincode"])

# Shiprocket base URL
BASE_URL = "https://apiv2.shiprocket.in/v1/external"

# Request timeout in seconds
API_TIMEOUT = 15.0

# Proxy support for IP blocking workaround
PROXY_URL = os.getenv("SHIPROCKET_PROXY_URL")
if PROXY_URL:
    logger.info(f"🔀 Shiprocket pincode proxy enabled: {PROXY_URL}")


async def _get_token_from_db(db: Session) -> Optional[str]:
    """
    Get authentication token from database if still valid.
    Tokens expire in 10 days, we cache for 9 days to be safe.

    Args:
        db: Database session

    Returns:
        Valid token from database if exists, None otherwise
    """
    config = db.query(ShiprocketConfig).filter(ShiprocketConfig.is_active == True).first()

    if not config:
        logger.warning("⚠️ No active Shiprocket config found in database")
        return None

    if config.access_token and config.token_expires_at:
        # Check if token is still valid (with 1-hour buffer)
        if datetime.now(timezone.utc) < config.token_expires_at - timedelta(hours=1):
            logger.info(f"🔑 Using database token (expires: {config.token_expires_at})")
            return config.access_token

    logger.info("🔄 Database token expired or missing, need to authenticate")
    return None


def _get_url(endpoint: str) -> str:
    """
    Get the URL for a Shiprocket API endpoint.

    If proxy is configured, returns proxy URL. Otherwise returns direct Shiprocket URL.

    Args:
        endpoint: API endpoint (e.g., "/auth/login", "/postcode/details")

    Returns:
        Full URL to use for the request
    """
    # Remove leading slash if present
    endpoint = endpoint.lstrip("/")

    if PROXY_URL:
        # Route through proxy
        return f"{PROXY_URL}/{endpoint}"
    else:
        # Direct to Shiprocket
        return f"{BASE_URL}/{endpoint}"


async def _authenticate_shiprocket(db: Session) -> Optional[str]:
    """
    Authenticate with Shiprocket and store the token in database.
    Uses proper authentication flow with database token storage to avoid rate limiting.

    Security Features:
    - Uses httpx with proper SSL verification (verify=True)
    - Supports proxy routing if SHIPROCKET_PROXY_URL is set
    - Never logs credentials or token values

    Args:
        db: Database session

    Returns:
        Authentication token if successful, None otherwise
    """
    # Get active Shiprocket config from database
    config = db.query(ShiprocketConfig).filter(ShiprocketConfig.is_active == True).first()

    if not config:
        logger.warning("⚠️ No active Shiprocket config found in database")
        # Fallback to environment variables
        shiprocket_email = os.getenv("SHIPROCKET_API_EMAIL") or os.getenv("SHIPROCKET_EMAIL")
        shiprocket_password = os.getenv("SHIPROCKET_API_PASSWORD") or os.getenv("SHIPROCKET_PASSWORD")

        if not shiprocket_email or not shiprocket_password:
            logger.warning("Shiprocket credentials not configured in database or environment")
            return None
    else:
        # Use database credentials (decrypt password if encrypted)
        shiprocket_email = config.email
        shiprocket_password = config.encrypted_password  # TODO: Decrypt if using Fernet encryption

    try:
        logger.info(f"🔗 Authenticating with Shiprocket API user: {shiprocket_email}")

        # SECURITY: httpx with verify=True for secure authentication
        async with httpx.AsyncClient(timeout=API_TIMEOUT, verify=True) as client:
            auth_response = await client.post(
                _get_url("/auth/login"),
                json={
                    "email": shiprocket_email,
                    "password": shiprocket_password,
                },
            )

            if auth_response.status_code == 200:
                data = auth_response.json()
                token = data.get("token")

                # Store token in database for 9 days (expires in 10 days)
                if config:
                    config.access_token = token
                    config.token_expires_at = datetime.now(timezone.utc) + timedelta(days=9)
                    db.commit()
                    logger.info(f"✅ Shiprocket authentication successful, token stored in database until: {config.token_expires_at}")
                else:
                    logger.info(f"✅ Shiprocket authentication successful (no database config to store token)")

                return token
            elif auth_response.status_code == 403:
                logger.error(f"❌ 403 Forbidden - WAF/Firewall blocking API user: {shiprocket_email}")
                return None
            else:
                logger.error(f"❌ Authentication failed: {auth_response.status_code}")
                return None

    except Exception as e:
        logger.error(f"❌ Shiprocket auth error: {str(e)}")
        db.rollback()
        return None


async def check_shiprocket_pincode(pincode: str, db: Session) -> dict[str, Any]:
    """
    Check pincode details using Shiprocket open postcode API.

    This endpoint is public and doesn't require authentication.
    No token caching needed as it's an open endpoint.

    Args:
        pincode: 6-digit Indian pincode
        db: Database session (unused for open endpoint)

    Returns:
        Dict with location details and error handling
    """
    # Step 1: Lookup pincode details using open endpoint (no auth required)
    try:
        # SECURITY: httpx with verify=True for secure API calls
        async with httpx.AsyncClient(timeout=API_TIMEOUT, verify=True) as client:
            pincode_response = await client.get(
                _get_url("/open/postcode/details"),  # Use open endpoint (no auth)
                headers={
                    "Content-Type": "application/json"
                },
                params={
                    "postcode": pincode
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
                # Token expired, clear database token and retry once
                config = db.query(ShiprocketConfig).filter(ShiprocketConfig.is_active == True).first()
                if config:
                    config.access_token = None
                    config.token_expires_at = None
                    db.commit()
                logger.warning("Token expired (401), will retry on next request")
                return {
                    "success": False,
                    "error": "Authentication expired",
                    "error_type": "auth_failure"
                }
            elif pincode_response.status_code == 403:
                # WAF/Firewall blocking - treat as service unavailable
                logger.warning(f"Pincode lookup blocked by WAF/Firewall (403)")
                return {
                    "success": False,
                    "error": "Service blocked by firewall",
                    "error_type": "service_unavailable"
                }
            elif pincode_response.status_code == 404:
                # Pincode not found in Shiprocket database
                logger.warning(f"Pincode {pincode} not found (404)")
                return {
                    "success": False,
                    "error": f"Pincode {pincode} not found",
                    "error_type": "pincode_not_found"
                }
            else:
                # Other errors - treat as service issues
                logger.warning(f"Pincode lookup failed: {pincode_response.status_code}")
                return {
                    "success": False,
                    "error": f"Pincode lookup failed",
                    "error_type": "service_unavailable"
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
async def lookup_pincode(pincode: str, db: Session = Depends(get_db)):
    """
    Lookup pincode details using Shiprocket API.

    Returns city, state, and serviceability information for the given pincode.
    Uses database-stored token for authentication.

    Args:
        pincode: 6-digit Indian pincode
        db: Database session (injected)

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
        result = await check_shiprocket_pincode(pincode, db)

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
