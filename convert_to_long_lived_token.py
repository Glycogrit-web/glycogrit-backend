#!/usr/bin/env python3
"""
Convert a short-lived Facebook/Instagram access token to a long-lived token (60 days).

Usage:
    python convert_to_long_lived_token.py APP_ID APP_SECRET SHORT_LIVED_TOKEN
"""

import sys
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def convert_to_long_lived_token(app_id: str, app_secret: str, short_lived_token: str):
    """
    Exchange a short-lived token for a long-lived token (60 days).

    Args:
        app_id: Your Facebook App ID
        app_secret: Your Facebook App Secret
        short_lived_token: Current short-lived access token
    """
    print("=" * 60)
    print("Converting to Long-Lived Token")
    print("=" * 60)
    print()

    url = "https://graph.facebook.com/v18.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token
    }

    try:
        print("🔄 Requesting long-lived token from Facebook...")
        response = requests.get(url, params=params, verify=False)
        response.raise_for_status()

        data = response.json()

        if "access_token" in data:
            long_lived_token = data["access_token"]
            expires_in = data.get("expires_in", "unknown")

            # Convert seconds to days
            if expires_in != "unknown":
                days = expires_in // 86400
                print(f"✅ Success! Token converted.")
                print(f"   Expires in: {days} days ({expires_in} seconds)")
            else:
                print("✅ Success! Token converted.")
                print(f"   Expires in: {expires_in}")

            print()
            print("=" * 60)
            print("📋 YOUR LONG-LIVED TOKEN:")
            print("=" * 60)
            print(long_lived_token)
            print("=" * 60)
            print()
            print("💾 ADD TO DOPPLER:")
            print("=" * 60)
            print(f"INSTAGRAM_ACCESS_TOKEN={long_lived_token}")
            print("INSTAGRAM_ACCOUNT_ID=26266167426339589")
            print("=" * 60)
            print()
            print("⚠️  IMPORTANT:")
            print(f"   - This token will expire in ~{days if expires_in != 'unknown' else '60'} days")
            print("   - Set a reminder to refresh it before expiry")
            print("   - Keep this token SECRET - don't commit to git!")
            print()

            # Verify the new token
            print("🔍 Verifying new token permissions...")
            verify_token(long_lived_token)

        else:
            print("❌ Error: No access token in response")
            print(f"Response: {data}")

    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if e.response:
            print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def verify_token(access_token: str):
    """Verify the new token has required permissions."""
    url = "https://graph.facebook.com/v18.0/me/permissions"
    params = {"access_token": access_token}

    try:
        response = requests.get(url, params=params, verify=False)
        data = response.json()

        if "data" not in data:
            print("⚠️  Could not verify permissions")
            return

        permissions = {p["permission"]: p["status"] for p in data["data"]}

        required = [
            "instagram_basic",
            "instagram_content_publish",
            "pages_manage_posts",
            "pages_show_list"
        ]

        print("\nToken Permissions:")
        all_granted = True
        for perm in required:
            status = permissions.get(perm, "not_granted")
            icon = "✅" if status == "granted" else "❌"
            print(f"  {icon} {perm}: {status}")
            if status != "granted":
                all_granted = False

        if all_granted:
            print("\n✅ All required permissions verified!")
        else:
            print("\n⚠️  Some permissions are missing.")

    except Exception as e:
        print(f"⚠️  Could not verify permissions: {str(e)}")


def main():
    if len(sys.argv) != 4:
        print("Usage: python convert_to_long_lived_token.py APP_ID APP_SECRET SHORT_LIVED_TOKEN")
        print()
        print("To get your App ID and Secret:")
        print("1. Go to: https://developers.facebook.com/apps")
        print("2. Select your app (Glycogrit Social)")
        print("3. Go to Settings → Basic")
        print("4. Copy 'App ID' and 'App Secret'")
        print()
        print("Your current short-lived token:")
        print("EAAXffrHWGGQBRXI7RxZCcLIcoOk0BU2nix4VaS7VJjpZA4Nzba...")
        sys.exit(1)

    app_id = sys.argv[1]
    app_secret = sys.argv[2]
    short_lived_token = sys.argv[3]

    convert_to_long_lived_token(app_id, app_secret, short_lived_token)


if __name__ == "__main__":
    main()
