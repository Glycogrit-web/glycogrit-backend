"""
Authentication Manager for Shiprocket CLI
Handles credential storage, token management, and auto-refresh
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx


class AuthManager:
    """Manages Shiprocket authentication and credential storage"""

    BASE_URL = "https://apiv2.shiprocket.in/v1/external"
    CONFIG_DIR = Path.home() / ".shiprocket"
    CONFIG_FILE = CONFIG_DIR / "credentials.json"

    def __init__(self):
        """Initialize auth manager"""
        self.config_dir = self.CONFIG_DIR
        self.config_file = self.CONFIG_FILE
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        # Set restrictive permissions (owner only)
        os.chmod(self.config_dir, 0o700)

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid credentials"""
        if not self.config_file.exists():
            return False

        config = self._load_config()
        return bool(config.get("email") and config.get("password"))

    def has_valid_token(self) -> bool:
        """Check if we have a valid access token"""
        if not self.is_authenticated():
            return False

        config = self._load_config()
        token = config.get("access_token")
        expires_at = config.get("token_expires_at")

        if not token or not expires_at:
            return False

        # Check if token is still valid (with 1 hour buffer)
        expiry_time = datetime.fromisoformat(expires_at)
        return datetime.utcnow() < expiry_time - timedelta(hours=1)

    def _load_config(self) -> dict:
        """Load configuration from file"""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_config(self, config: dict) -> None:
        """Save configuration to file"""
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)
        # Set restrictive permissions (owner only)
        os.chmod(self.config_file, 0o600)

    async def login(self, email: str, password: str) -> tuple[bool, str]:
        """
        Login to Shiprocket and store credentials

        Args:
            email: Shiprocket account email
            password: Shiprocket account password

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Test authentication
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                response = await client.post(
                    f"{self.BASE_URL}/auth/login",
                    json={"email": email, "password": password},
                )

                if response.status_code == 200:
                    data = response.json()
                    token = data.get("token")

                    if not token:
                        return False, "No token received from Shiprocket"

                    # Save credentials and token
                    config = {
                        "email": email,
                        "password": password,  # TODO: Encrypt in production
                        "access_token": token,
                        "token_expires_at": (
                            datetime.utcnow() + timedelta(days=10)
                        ).isoformat(),
                        "logged_in_at": datetime.utcnow().isoformat(),
                    }
                    self._save_config(config)

                    return True, "Successfully logged in to Shiprocket"

                elif response.status_code == 401:
                    return False, "Invalid email or password"
                elif response.status_code == 422:
                    return False, "Invalid request format. Check your credentials."
                else:
                    return (
                        False,
                        f"Authentication failed: {response.status_code} - {response.text}",
                    )

        except httpx.RequestError as e:
            return False, f"Network error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    async def get_token(self) -> Optional[str]:
        """
        Get valid access token, refreshing if necessary

        Returns:
            Access token or None if authentication fails
        """
        if self.has_valid_token():
            config = self._load_config()
            return config.get("access_token")

        # Token expired or missing, try to refresh
        if not self.is_authenticated():
            return None

        config = self._load_config()
        success, _ = await self.login(config["email"], config["password"])

        if success:
            config = self._load_config()
            return config.get("access_token")

        return None

    def logout(self) -> None:
        """Remove stored credentials"""
        if self.config_file.exists():
            self.config_file.unlink()

    def get_user_info(self) -> Optional[dict]:
        """Get logged-in user information"""
        if not self.is_authenticated():
            return None

        config = self._load_config()
        return {
            "email": config.get("email"),
            "logged_in_at": config.get("logged_in_at"),
            "token_expires_at": config.get("token_expires_at"),
        }
