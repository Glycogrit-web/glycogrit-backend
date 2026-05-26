"""
JWT Authentication Utilities
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

# Lazy import to avoid circular dependency
if TYPE_CHECKING:
    from app.models.user import User

# Security scheme - auto_error=False so we can return 401 instead of 403
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    password_bytes = password.encode("utf-8")[:72]  # Truncate to bcrypt limit
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    password_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    # Ensure 'sub' is a string (JWT spec requires it)
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode JWT access token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except (jwt.PyJWTError, jwt.InvalidTokenError, Exception) as e:
        # Log detailed error for debugging (not exposed to user)
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"JWT decode error: {type(e).__name__}: {str(e)}")

        # Return generic error message to user (no internal details)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> "User":
    """Get current authenticated user from JWT token"""
    # Import here to avoid circular dependency
    from app.models.user import User

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Convert string back to int
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(current_user: "User" = Depends(get_current_user)) -> "User":
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
) -> Optional["User"]:
    """Get current user if authenticated, None otherwise"""
    # Import here to avoid circular dependency
    from app.models.user import User

    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")

        if user_id_str is None:
            return None

        user_id = int(user_id_str)
        user = db.query(User).filter(User.id == user_id).first()

        return user if user and user.is_active else None
    except Exception:
        return None


async def require_admin(current_user: "User" = Depends(get_current_user)) -> "User":
    """Require user to have admin role"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
