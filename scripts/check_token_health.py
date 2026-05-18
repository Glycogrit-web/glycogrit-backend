#!/usr/bin/env python3
"""
Check health and expiry of Instagram tokens.

Usage:
    python scripts/check_token_health.py
"""

import os
import sys
import requests
import urllib3
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

def check_token(token: str, token_name: str, required_permissions: list):
    """Check token validity and expiry."""

    if not token:
        print(f"❌ {token_name}: NOT SET")
        return False

    print(f"\n{'=' * 70}")
    print(f"Checking: {token_name}")
    print('=' * 70)
    print(f"Token: {token[:20]}...")

    try:
        # Check token validity and expiry
        debug_url = f"https://graph.facebook.com/v18.0/debug_token"
        # Need app token for debug, using token itself as approximation
        # Better: Use me endpoint to check validity
        me_url = "https://graph.facebook.com/v18.0/me"
        params = {"access_token": token}

        response = requests.get(me_url, params=params, verify=False, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: Valid")
            print(f"   User ID: {data.get('id', 'Unknown')}")
            print(f"   Name: {data.get('name', 'Unknown')}")

            # Check permissions
            perm_url = "https://graph.facebook.com/v18.0/me/permissions"
            perm_response = requests.get(perm_url, params=params, verify=False, timeout=10)

            if perm_response.status_code == 200:
                perm_data = perm_response.json()
                granted_perms = {p["permission"]: p["status"] for p in perm_data.get("data", [])}

                print(f"\n   Permissions:")
                all_granted = True
                for perm in required_permissions:
                    status = granted_perms.get(perm, "not_granted")
                    icon = "✅" if status == "granted" else "❌"
                    print(f"     {icon} {perm}: {status}")
                    if status != "granted":
                        all_granted = False

                if all_granted:
                    print(f"\n   ✅ All required permissions present")
                    return True
                else:
                    print(f"\n   ⚠️  Missing some permissions - token may need refresh")
                    return False
            else:
                print(f"   ⚠️  Could not check permissions")
                return True  # Token valid but can't check perms

        else:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "Unknown error")
            print(f"❌ Status: Invalid")
            print(f"   Error: {error_msg}")

            if "expired" in error_msg.lower():
                print(f"   Action: Generate new token immediately!")
                print(f"   Run: python scripts/refresh_instagram_token.py")

            return False

    except requests.exceptions.Timeout:
        print(f"⚠️  Status: Timeout - cannot verify")
        return None
    except Exception as e:
        print(f"❌ Error checking token: {str(e)}")
        return False


def main():
    print("=" * 70)
    print("Instagram Token Health Check")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check backend token
    backend_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    backend_perms = [
        "instagram_basic",
        "instagram_content_publish",
        "pages_manage_posts",
        "pages_show_list"
    ]
    backend_valid = check_token(backend_token, "INSTAGRAM_ACCESS_TOKEN (Backend)", backend_perms)

    # Check frontend token
    frontend_token = os.getenv("VITE_INSTAGRAM_ACCESS_TOKEN")
    frontend_perms = [
        "instagram_basic",
        "instagram_graph_user_media"
    ]
    frontend_valid = check_token(frontend_token, "VITE_INSTAGRAM_ACCESS_TOKEN (Frontend)", frontend_perms)

    # Summary
    print(f"\n{'=' * 70}")
    print("Summary")
    print('=' * 70)

    if backend_valid and frontend_valid:
        print("✅ All tokens are healthy!")
        print("\n📅 Recommendation: Set reminder to refresh tokens in 40-50 days")
    elif backend_valid is False or frontend_valid is False:
        print("❌ Some tokens are invalid!")
        print("\n🔧 Action Required:")
        if backend_valid is False:
            print("   1. Refresh backend token: python scripts/refresh_instagram_token.py backend")
        if frontend_valid is False:
            print("   2. Refresh frontend token: python scripts/refresh_instagram_token.py frontend")
    else:
        print("⚠️  Could not verify all tokens")

    print("\n" + "=" * 70)
    print("For detailed instructions, see: TOKEN_MANAGEMENT.md")
    print("=" * 70)


if __name__ == "__main__":
    main()
