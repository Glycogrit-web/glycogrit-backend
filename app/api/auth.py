"""
Authentication API Endpoints

Provides user authentication and authorization functionality including:
- User registration
- Login with email/password
- Google OAuth authentication
- Profile retrieval and updates
- Password management
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, status, Request, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.config import settings
from app.core.rate_limit import limiter, RateLimits
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse, GoogleAuthRequest
from app.schemas.user import UserUpdate, UserDetailResponse, PasswordChange
from app.models.user import User
from app.services.user_service import UserService
import httpx

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.AUTH)
async def register(
    request: Request,
    user_data: UserRegister,
    db: Session = Depends(get_db)
) -> Token:
    """
    Register a new user account.

    Creates a new user with provided credentials and returns JWT token.

    Args:
        request: FastAPI Request object (required for rate limiting)
        user_data: User registration data (email, password, names, location)
        db: Database session dependency

    Returns:
        Token: JWT access token and token type

    Raises:
        AlreadyExistsException: If email is already registered
        ValidationException: If data validation fails

    Rate Limit:
        5 requests per minute per client (strict to prevent spam)

    Example:
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
    """
    service: UserService = UserService(db)
    result: Token = service.register_user(
        email=user_data.email,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        city=user_data.city,
        state=user_data.state
    )
    return result


@router.post("/login", response_model=Token)
@limiter.limit(RateLimits.AUTH)
async def login(
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db)
) -> Token:
    """
    Authenticate user and obtain access token.

    Validates credentials and returns JWT token for authenticated requests.

    Args:
        request: FastAPI Request object (required for rate limiting)
        credentials: User login credentials (email and password)
        db: Database session dependency

    Returns:
        Token: JWT access token and token type

    Raises:
        AuthenticationException: If credentials are invalid
        NotFoundException: If user not found

    Rate Limit:
        5 requests per minute per client (strict to prevent brute force)

    Example:
        ```json
        {
          "email": "user@example.com",
          "password": "SecurePass123!"
        }
        ```
    """
    service: UserService = UserService(db)
    result: Token = service.authenticate_user(
        email=credentials.email,
        password=credentials.password
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

    Args:
        request: FastAPI Request object (required for rate limiting)
        current_user: Current authenticated user from JWT token

    Returns:
        UserResponse: User profile data

    Rate Limit:
        100 requests per minute per user

    Requires:
        Bearer token in Authorization header
    """
    return current_user


@router.put("/users/{user_id}", response_model=UserDetailResponse)
@limiter.limit(RateLimits.WRITE_UPDATE)
async def update_user(
    request: Request,
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserDetailResponse:
    """
    Update user profile information.

    Allows users to update their own profile data including names and location.

    Args:
        request: FastAPI Request object (required for rate limiting)
        user_id: ID of the user to update
        user_data: Updated user profile data
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        UserDetailResponse: Updated user profile data

    Raises:
        NotFoundException: If user not found
        PermissionDeniedException: If user tries to update another user's profile
        ValidationException: If data validation fails

    Rate Limit:
        30 requests per minute per user

    Authorization:
        Only the user themselves can update their profile

    Requires:
        Bearer token in Authorization header
    """
    service: UserService = UserService(db)
    update_dict: Dict[str, Any] = user_data.model_dump(exclude_unset=True)
    updated_user: UserDetailResponse = service.update_user(user_id, update_dict, current_user.id)
    return updated_user


@router.post("/users/{user_id}/change-password", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.AUTH)
async def change_password(
    request: Request,
    user_id: int,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Change user password.

    Updates the user's password after verifying the current password.

    Args:
        request: FastAPI Request object (required for rate limiting)
        user_id: ID of the user
        password_data: Current and new password data
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        Dict with success message

    Raises:
        NotFoundException: If user not found
        PermissionDeniedException: If user tries to change another user's password
        AuthenticationException: If current password is incorrect
        ValidationException: If new password doesn't meet requirements

    Rate Limit:
        5 requests per minute per user (strict to prevent brute force)

    Authorization:
        Only the user themselves can change their password

    Requires:
        Bearer token in Authorization header

    Example:
        ```json
        {
          "current_password": "OldPass123!",
          "new_password": "NewSecurePass456!"
        }
        ```
    """
    service: UserService = UserService(db)
    service.change_password(
        user_id=user_id,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
        current_user_id=current_user.id
    )
    return {"message": "Password changed successfully"}


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
@limiter.limit(RateLimits.WRITE_DELETE)
async def delete_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete user account (soft delete - deactivates the account).

    Soft deletes the user account by marking it as inactive while preserving data.

    Args:
        request: FastAPI Request object (required for rate limiting)
        user_id: ID of the user to delete
        current_user: Current authenticated user from JWT token
        db: Database session dependency

    Returns:
        Dict with success message

    Raises:
        NotFoundException: If user not found
        PermissionDeniedException: If user tries to delete another user's account

    Rate Limit:
        10 requests per minute per user

    Authorization:
        Only the user themselves can delete their account

    Requires:
        Bearer token in Authorization header

    Note:
        This is a soft delete - the account is deactivated but data is preserved
        for data integrity and potential recovery.
    """
    service: UserService = UserService(db)
    service.delete_user(user_id, current_user.id)
    return {"message": "User account deleted successfully"}


@router.post("/google", response_model=Token)
@limiter.limit(RateLimits.AUTH)
async def google_auth(
    request: Request,
    response: Response,
    auth_data: GoogleAuthRequest,
    db: Session = Depends(get_db)
) -> Token:
    """
    Authenticate user with Google OAuth token.

    Validates Google OAuth token and creates/authenticates user account.

    Args:
        request: FastAPI Request object (required for rate limiting)
        token: Google OAuth ID token from frontend
        db: Database session dependency

    Returns:
        Token: JWT access token and token type

    Raises:
        HTTPException: If token validation fails or Google API error

    Rate Limit:
        5 requests per minute per client

    Example:
        Frontend sends the Google ID token received from Google Sign-In:
        ```json
        {
          "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."
        }
        ```
    """
    try:
        # Verify Google token by calling Google's tokeninfo endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={auth_data.token}",
                timeout=10.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Google token"
                )

            token_info = response.json()

            # Verify the token is for our application
            token_aud = token_info.get("aud")
            expected_client_id = settings.GOOGLE_CLIENT_ID

            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Token aud: '{token_aud}'")
            logger.info(f"Expected CLIENT_ID: '{expected_client_id}'")
            logger.info(f"Match: {token_aud == expected_client_id}")

            if token_aud != expected_client_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Token not intended for this application. Expected: {expected_client_id[:20]}..., Got: {token_aud[:20] if token_aud else 'None'}..."
                )

            # Extract user information
            email = token_info.get("email")
            google_id = token_info.get("sub")
            given_name = token_info.get("given_name", "")
            family_name = token_info.get("family_name", "")
            picture = token_info.get("picture")

            if not email or not google_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token: missing required fields"
                )

            # Authenticate or create user
            service: UserService = UserService(db)
            result: Token = service.authenticate_or_create_oauth_user(
                email=email,
                oauth_provider="google",
                oauth_id=google_id,
                first_name=given_name,
                last_name=family_name,
                profile_picture_url=picture
            )

            return result

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to verify Google token: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )
