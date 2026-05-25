"""
Authentication API Endpoints - DDD Module

Provides user authentication and authorization functionality:
- User registration
- Login with email/password
- Google OAuth authentication
- Token management
"""

import logging
from typing import Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_current_active_user
from app.core.config import settings
from app.core.constants import APIRoutes
from app.core.database import get_db
from app.core.rate_limit import RateLimits, limiter
from app.models.user import User
from app.modules.users.schemas.auth import (
    GoogleAuthRequest,
    Token,
    UserLogin,
    UserRegister,
)
from app.modules.users.schemas.user import UserResponse
from app.modules.users.services.auth_service import AuthService
from app.modules.users.services.commands import RegisterOAuthUserCommand, RegisterUserCommand
from app.modules.users.services.user_service import UserService

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

router = APIRouter(prefix=APIRoutes.AUTH, tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.AUTH)
async def register(
    request: Request,
    response: Response,
    user_data: UserRegister,
    db: Session = Depends(get_db)
) -> Token:
    """
    Register a new user account with email and/or phone.

    Creates a new user with provided credentials and returns JWT token.
    At least one identifier (email or phone) is required.

    Rate Limit: 5 requests per minute per client

    Example (Email):
        ```json
        {
          "email": "user@example.com",
          "password": "SecurePass123!",
          "first_name": "John",
          "last_name": "Doe",
          "city": "Mumbai",
          "state": "Maharashtra"
        }
        ```

    Example (Phone):
        ```json
        {
          "phone": "9876543210",
          "password": "SecurePass123!",
          "first_name": "John",
          "last_name": "Doe"
        }
        ```
    """
    service = UserService(db)

    # Create command
    command = RegisterUserCommand(
        email=user_data.email,
        phone=user_data.phone,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        city=user_data.city,
        state=user_data.state
    )

    # Execute command
    new_user = service.handle_register_user(command)

    # Create access token
    access_token = create_access_token(data={"sub": new_user.id})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/login", response_model=Token)
@limiter.limit(RateLimits.AUTH)
async def login(
    request: Request,
    response: Response,
    credentials: UserLogin,
    db: Session = Depends(get_db)
) -> Token:
    """
    Authenticate user with email or phone and obtain access token.

    Automatically detects whether identifier is email or phone.

    Rate Limit: 5 requests per minute per client

    Example (Email):
        ```json
        {
          "identifier": "user@example.com",
          "password": "SecurePass123!"
        }
        ```

    Example (Phone):
        ```json
        {
          "identifier": "9876543210",
          "password": "SecurePass123!"
        }
        ```
    """
    auth_service = AuthService(db)

    result = auth_service.authenticate_user(
        identifier=credentials.identifier,
        password=credentials.password,
        identifier_type=credentials.identifier_type
    )

    return result


@router.get("/me", response_model=UserResponse)
@limiter.limit(RateLimits.READ_DETAIL)
async def get_current_user_info(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get authenticated user's profile information.

    Returns detailed information about the currently authenticated user.

    Rate Limit: 100 requests per minute per user

    Requires: Bearer token in Authorization header
    """
    return current_user


@router.post("/google", response_model=Token)
@limiter.limit(RateLimits.AUTH)
async def google_auth(
    request: Request,
    response: Response,
    auth_request: GoogleAuthRequest,
    db: Session = Depends(get_db)
) -> Token:
    """
    Authenticate or register user via Google OAuth.

    Accepts either:
    1. Google ID token (direct from Google Sign-In button)
    2. Authorization code (from OAuth redirect flow)

    The backend will exchange the authorization code for tokens if needed.

    Rate Limit: 5 requests per minute per client

    Example (ID Token):
        ```json
        {
          "token": "google_id_token_from_google_button"
        }
        ```

    Example (Authorization Code):
        ```json
        {
          "token": "4/0AfJohXmE..."
        }
        ```
    """
    auth_service = AuthService(db)
    token_to_verify = auth_request.token

    # Check if this is an authorization code (starts with "4/" or similar patterns)
    # If so, exchange it for an ID token
    if auth_request.token.startswith(("4/", "1/")) or len(auth_request.token) > 500:
        # This looks like an authorization code, exchange it for tokens
        logger.info(f"Processing OAuth authorization code (length: {len(auth_request.token)})")

        try:
            redirect_uri = settings.google_oauth_redirect_uri
            logger.info(f"Token exchange redirect_uri: {redirect_uri}")

            async with httpx.AsyncClient() as client:
                token_exchange_response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": auth_request.token,
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code"
                    }
                )

                logger.info(f"Google token exchange status: {token_exchange_response.status_code}")

                if token_exchange_response.status_code != 200:
                    error_detail = token_exchange_response.text
                    logger.error(f"Token exchange failed: {error_detail}")

                    # Add helpful error message for redirect URI mismatch
                    if "invalid_grant" in error_detail:
                        logger.error(
                            f"REDIRECT URI MISMATCH? Backend using: {redirect_uri}. "
                            f"Ensure frontend uses same value (check VITE_GOOGLE_REDIRECT_URI)."
                        )

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Failed to exchange authorization code: {error_detail}"
                    )

                token_data = token_exchange_response.json()
                token_to_verify = token_data.get("id_token")

                if not token_to_verify:
                    logger.error("No ID token in Google response")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No ID token received from Google"
                    )

                logger.info("Successfully exchanged authorization code for ID token")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token exchange: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not exchange authorization code: {str(e)}"
            )

    # Verify Google ID token
    try:
        async with httpx.AsyncClient() as client:
            google_response = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={token_to_verify}"
            )

            if google_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Google token"
                )

            token_info = google_response.json()

            # Verify audience (client ID)
            if token_info.get("aud") != settings.GOOGLE_CLIENT_ID:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token audience"
                )

            # Extract user info
            email = token_info.get("email")
            google_id = token_info.get("sub")
            first_name = token_info.get("given_name", "")
            last_name = token_info.get("family_name", "")
            profile_picture = token_info.get("picture")

            if not email or not google_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Incomplete user information from Google"
                )

    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not verify Google token"
        )

    # Create OAuth user command
    command = RegisterOAuthUserCommand(
        email=email,
        oauth_provider="google",
        oauth_id=google_id,
        first_name=first_name,
        last_name=last_name,
        profile_picture_url=profile_picture
    )

    # Register or authenticate OAuth user
    result = auth_service.handle_register_oauth_user(command)

    return result


@router.post("/refresh", response_model=Token)
@limiter.limit(RateLimits.AUTH)
async def refresh_token(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Token:
    """
    Refresh access token for authenticated user.

    Generates a new JWT token for the current user.

    Rate Limit: 5 requests per minute per user

    Requires: Bearer token in Authorization header
    """
    auth_service = AuthService(db)
    result = auth_service.refresh_token(current_user.id)
    return result


@router.post("/logout", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user)
) -> dict[str, str]:
    """
    Logout current user.

    Note: JWT tokens are stateless, so logout is handled client-side
    by removing the token. This endpoint serves as a confirmation.

    Rate Limit: 30 requests per minute per user

    Requires: Bearer token in Authorization header
    """
    return {
        "message": "Successfully logged out",
        "detail": "Please remove the token from client storage"
    }
