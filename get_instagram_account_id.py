#!/usr/bin/env python3
"""
Script to fetch Instagram Business Account ID from Facebook Graph API.
This ID is needed for the gallery submission feature.

Usage:
    python get_instagram_account_id.py YOUR_ACCESS_TOKEN
"""

import sys

import requests
import urllib3

# Disable SSL warnings for this script only
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_instagram_account_id(access_token: str):
    """
    Fetch Instagram Business Account ID using Facebook Graph API.

    Args:
        access_token: Your Facebook/Instagram access token
    """
    print("=" * 60)
    print("Instagram Account ID Fetcher")
    print("=" * 60)
    print()

    # Step 1: Get all Facebook Pages
    print("Step 1: Fetching your Facebook Pages...")
    pages_url = "https://graph.facebook.com/v18.0/me/accounts"
    params = {"access_token": access_token, "fields": "id,name,access_token"}

    try:
        response = requests.get(pages_url, params=params, timeout=30)
        response.raise_for_status()
        pages_data = response.json()

        if "error" in pages_data:
            print(f"❌ Error: {pages_data['error']['message']}")
            return

        pages = pages_data.get("data", [])

        if not pages:
            print("❌ No Facebook Pages found associated with this token.")
            print("   Make sure:")
            print("   1. You have a Facebook Page")
            print("   2. The Page is connected to an Instagram Business Account")
            print("   3. Your token has 'pages_show_list' permission")
            return

        print(f"✅ Found {len(pages)} Facebook Page(s):")
        print()

        # Step 2: Get Instagram account for each page
        for idx, page in enumerate(pages, 1):
            page_id = page["id"]
            page_name = page["name"]
            page_token = page.get("access_token", access_token)

            print(f"Page {idx}: {page_name} (ID: {page_id})")

            # Get Instagram account
            ig_url = f"https://graph.facebook.com/v18.0/{page_id}"
            ig_params = {"access_token": page_token, "fields": "instagram_business_account"}

            ig_response = requests.get(ig_url, params=ig_params, timeout=30)
            ig_data = ig_response.json()

            if "instagram_business_account" in ig_data:
                ig_account = ig_data["instagram_business_account"]
                ig_account_id = ig_account["id"]

                # Get Instagram username
                username_url = f"https://graph.facebook.com/v18.0/{ig_account_id}"
                username_params = {"access_token": page_token, "fields": "username,name"}
                username_response = requests.get(username_url, params=username_params, timeout=30)
                username_data = username_response.json()

                ig_username = username_data.get("username", "Unknown")
                ig_name = username_data.get("name", "Unknown")

                print("  ✅ Instagram Account Found!")
                print(f"     Username: @{ig_username}")
                print(f"     Name: {ig_name}")
                print(f"     Instagram Account ID: {ig_account_id}")
                print()
                print("=" * 60)
                print("📋 ADD THESE TO YOUR DOPPLER/ENV:")
                print("=" * 60)
                print(f"INSTAGRAM_ACCOUNT_ID={ig_account_id}")
                print(f"INSTAGRAM_ACCESS_TOKEN={page_token}")
                print("=" * 60)
                print()

                # Verify permissions
                print("Step 3: Verifying token permissions...")
                verify_permissions(page_token)

            else:
                print("  ⚠️  No Instagram Business Account connected to this page")
                print(f"     Connect Instagram at: https://www.facebook.com/{page_id}/settings")

            print()

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {str(e)}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def verify_permissions(access_token: str):
    """Verify that the token has required permissions."""
    url = "https://graph.facebook.com/v18.0/me/permissions"
    params = {"access_token": access_token}

    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if "data" not in data:
            print("⚠️  Could not verify permissions")
            return

        permissions = {p["permission"]: p["status"] for p in data["data"]}

        required = [
            "instagram_basic",
            "instagram_content_publish",
            "pages_read_engagement",
            "pages_show_list",
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
            print("\n✅ All required permissions are granted!")
        else:
            print("\n⚠️  Some permissions are missing. You may need to:")
            print("   1. Go to Facebook Developers: https://developers.facebook.com/apps")
            print("   2. Select your app")
            print("   3. Add missing permissions")
            print("   4. Generate a new token with all permissions")

    except Exception as e:
        print(f"⚠️  Could not verify permissions: {str(e)}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python get_instagram_account_id.py YOUR_ACCESS_TOKEN")
        print()
        print("Get your access token from:")
        print("1. Facebook Graph API Explorer: https://developers.facebook.com/tools/explorer")
        print("2. Select your app")
        print(
            "3. Add permissions: instagram_basic, instagram_content_publish, pages_read_engagement"
        )
        print("4. Click 'Generate Access Token'")
        print("5. Copy the token and run this script")
        sys.exit(1)

    access_token = sys.argv[1]
    get_instagram_account_id(access_token)


if __name__ == "__main__":
    main()
