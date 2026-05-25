#!/usr/bin/env python3
"""
Refresh Instagram Access Token

Usage:
    python scripts/refresh_instagram_token.py backend   # Refresh backend token
    python scripts/refresh_instagram_token.py frontend  # Refresh frontend token
"""

import sys
from datetime import datetime, timedelta

import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Credentials
APP_ID = "1653110126024804"
APP_SECRET = "403478ea0a30bd690df358e791f1ff41"

def refresh_token(token_type: str):
    """Refresh either backend or frontend Instagram token."""

    print("=" * 70)
    print(f"Instagram Token Refresh - {token_type.upper()}")
    print("=" * 70)
    print()

    # Define permissions needed
    if token_type == "backend":
        permissions_needed = [
            "instagram_basic",
            "instagram_content_publish",
            "pages_manage_posts",
            "pages_show_list"
        ]
        doppler_var = "INSTAGRAM_ACCESS_TOKEN"
        purpose = "Gallery submissions (create Instagram posts)"
    elif token_type == "frontend":
        permissions_needed = [
            "instagram_basic",
            "instagram_graph_user_media"
        ]
        doppler_var = "VITE_INSTAGRAM_ACCESS_TOKEN"
        purpose = "Gallery display (read Instagram posts)"
    else:
        print(f"❌ Invalid token type: {token_type}")
        print("Usage: python scripts/refresh_instagram_token.py [backend|frontend]")
        sys.exit(1)

    # Instructions for getting new token
    print(f"Purpose: {purpose}")
    print()
    print("=" * 70)
    print("STEP 1: Get New Short-Lived Token")
    print("=" * 70)
    print()
    print("1. Go to: https://developers.facebook.com/tools/explorer")
    print("2. Select: Glycogrit Social")
    print("3. Add these permissions:")
    for perm in permissions_needed:
        print(f"   ✓ {perm}")
    print("4. Click 'Generate Access Token'")
    print("5. Copy the token (starts with EAAX...)")
    print()

    short_token = input("Paste your short-lived token here: ").strip()

    if not short_token:
        print("❌ No token provided. Exiting.")
        sys.exit(1)

    print()
    print("=" * 70)
    print("STEP 2: Converting to Long-Lived Token...")
    print("=" * 70)
    print()

    # Convert to long-lived token
    try:
        url = "https://graph.facebook.com/v18.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": short_token
        }

        response = requests.get(url, params=params, verify=False)
        response.raise_for_status()

        data = response.json()
        long_token = data.get("access_token")
        expires_in = data.get("expires_in", 0)

        if not long_token:
            print("❌ Error: No access token returned")
            print(f"Response: {data}")
            sys.exit(1)

        days = expires_in // 86400
        expiry_date = datetime.now() + timedelta(seconds=expires_in)

        print("✅ Success! Token converted to long-lived")
        print(f"   Expires in: {days} days")
        print(f"   Expiry date: {expiry_date.strftime('%Y-%m-%d')}")
        print()

        # Verify permissions
        print("=" * 70)
        print("STEP 3: Verifying Permissions...")
        print("=" * 70)
        print()

        perm_url = "https://graph.facebook.com/v18.0/me/permissions"
        perm_params = {"access_token": long_token}
        perm_response = requests.get(perm_url, params=perm_params, verify=False)
        perm_data = perm_response.json()

        if "data" in perm_data:
            granted_perms = {p["permission"]: p["status"] for p in perm_data["data"]}

            all_granted = True
            for perm in permissions_needed:
                status = granted_perms.get(perm, "not_granted")
                icon = "✅" if status == "granted" else "❌"
                print(f"  {icon} {perm}: {status}")
                if status != "granted":
                    all_granted = False

            print()
            if all_granted:
                print("✅ All required permissions verified!")
            else:
                print("⚠️  Some permissions are missing. Please regenerate token with all permissions.")
                sys.exit(1)
        else:
            print("⚠️  Could not verify permissions")

        print()
        print("=" * 70)
        print("STEP 4: Update Doppler")
        print("=" * 70)
        print()
        print("1. Go to: https://dashboard.doppler.com")
        print("2. Project: glycogrit → Config: production")
        print(f"3. Update: {doppler_var}")
        print()
        print("Copy this value:")
        print("-" * 70)
        print(long_token)
        print("-" * 70)
        print()

        # Save to file option
        save = input("Save token to file for reference? (y/n): ").strip().lower()
        if save == 'y':
            filename = f"token_{token_type}_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(filename, 'w') as f:
                f.write(f"Token Type: {token_type}\n")
                f.write(f"Doppler Variable: {doppler_var}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Expires: {expiry_date.strftime('%Y-%m-%d')}\n")
                f.write(f"Token: {long_token}\n")
            print(f"✅ Token saved to: {filename}")
            print("⚠️  Remember to delete this file after updating Doppler!")

        print()
        print("=" * 70)
        print("STEP 5: Next Steps")
        print("=" * 70)
        print()
        print("1. ✅ Token generated and verified")
        print(f"2. ⏭️  Update {doppler_var} in Doppler")
        print("3. ⏭️  Redeploy (optional - auto-deploys on next push)")
        print(f"4. ⏭️  Test {'gallery submission' if token_type == 'backend' else 'gallery display'}")
        print(f"5. ⏭️  Set reminder to refresh in {days-10} days")
        print()
        print("=" * 70)
        print(f"📅 SET REMINDER: Refresh this token on {(datetime.now() + timedelta(days=days-10)).strftime('%Y-%m-%d')}")
        print("=" * 70)

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ["backend", "frontend"]:
        print("Usage: python scripts/refresh_instagram_token.py [backend|frontend]")
        print()
        print("Examples:")
        print("  python scripts/refresh_instagram_token.py backend   # Refresh gallery submission token")
        print("  python scripts/refresh_instagram_token.py frontend  # Refresh gallery display token")
        sys.exit(1)

    token_type = sys.argv[1]
    refresh_token(token_type)


if __name__ == "__main__":
    main()
