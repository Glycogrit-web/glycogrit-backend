import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import settings
import os

# Initialize Firebase Admin SDK
cred = None
if os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)


async def verify_firebase_token(token: str) -> dict:
    """
    Verify Firebase ID token and return decoded token data.

    Args:
        token: Firebase ID token from client

    Returns:
        dict: Decoded token data containing user info

    Raises:
        Exception: If token is invalid or expired
    """
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise Exception(f"Invalid token: {str(e)}")


def get_user_from_token(token: str) -> dict:
    """
    Get user information from Firebase token.

    Args:
        token: Firebase ID token

    Returns:
        dict: User information including uid, email, etc.
    """
    try:
        decoded_token = auth.verify_id_token(token)
        return {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified"),
            "name": decoded_token.get("name"),
        }
    except Exception as e:
        raise Exception(f"Failed to get user from token: {str(e)}")
