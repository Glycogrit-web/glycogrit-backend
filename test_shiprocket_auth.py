#!/usr/bin/env python3
"""
Test Shiprocket Authentication
Tests authentication with Shiprocket API using credentials from environment variables
"""

import asyncio
import os
import sys
from datetime import datetime

import httpx


async def test_shiprocket_auth():
    """Test Shiprocket API authentication"""

    print("=" * 60)
    print("Shiprocket Authentication Test")
    print("=" * 60)
    print()

    # Get credentials from environment
    email = os.getenv("SHIPROCKET_API_EMAIL") or os.getenv("SHIPROCKET_EMAIL")
    password = os.getenv("SHIPROCKET_API_PASSWORD") or os.getenv("SHIPROCKET_PASSWORD")

    print("1. Checking Environment Variables:")
    print(f"   SHIPROCKET_API_EMAIL: {'✓ Set' if os.getenv('SHIPROCKET_API_EMAIL') else '✗ Not set'}")
    print(f"   SHIPROCKET_EMAIL: {'✓ Set' if os.getenv('SHIPROCKET_EMAIL') else '✗ Not set'}")
    print(f"   SHIPROCKET_API_PASSWORD: {'✓ Set' if os.getenv('SHIPROCKET_API_PASSWORD') else '✗ Not set'}")
    print(f"   SHIPROCKET_PASSWORD: {'✓ Set' if os.getenv('SHIPROCKET_PASSWORD') else '✗ Not set'}")
    print()

    if not email or not password:
        print("❌ ERROR: Credentials not found in environment variables")
        print()
        print("Please set one of the following pairs:")
        print("  - SHIPROCKET_API_EMAIL and SHIPROCKET_API_PASSWORD")
        print("  - SHIPROCKET_EMAIL and SHIPROCKET_PASSWORD")
        print()
        print("To test with Doppler:")
        print("  doppler run -- python test_shiprocket_auth.py")
        return False

    print(f"2. Using Credentials:")
    print(f"   Email: {email}")
    print(f"   Password: {'*' * len(password)} (masked)")
    print()

    # Test authentication
    print("3. Testing Authentication:")
    print(f"   Endpoint: https://apiv2.shiprocket.in/v1/external/auth/login")
    print(f"   Method: POST")
    print()

    try:
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.post(
                "https://apiv2.shiprocket.in/v1/external/auth/login",
                json={
                    "email": email,
                    "password": password,
                },
            )

            print(f"4. Response:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()

            if response.status_code == 200:
                data = response.json()
                token = data.get("token", "")

                print("✅ SUCCESS: Authentication successful!")
                print()
                print(f"5. Token Details:")
                print(f"   Token (first 20 chars): {token[:20]}...")
                print(f"   Token Length: {len(token)} characters")
                print(f"   Token Validity: 10 days")
                print()

                # Test a simple API call with the token
                print("6. Testing API Call with Token:")
                test_response = await client.get(
                    "https://apiv2.shiprocket.in/v1/external/settings/company/pickup",
                    headers={"Authorization": f"Bearer {token}"}
                )

                print(f"   Endpoint: /settings/company/pickup")
                print(f"   Status Code: {test_response.status_code}")

                if test_response.status_code == 200:
                    print("   ✅ API call successful - Token is valid!")
                else:
                    print(f"   ⚠️  API call failed: {test_response.status_code}")
                    print(f"   Response: {test_response.text[:200]}")

                print()
                print("=" * 60)
                print("✅ All checks passed! Shiprocket authentication is working.")
                print("=" * 60)
                return True

            elif response.status_code == 403:
                print("❌ ERROR: 403 Forbidden")
                print()
                print("Possible Causes:")
                print("  1. These are not API user credentials")
                print("  2. The API user doesn't have proper permissions")
                print("  3. IP address not whitelisted (if configured)")
                print()
                print("Steps to Fix:")
                print("  1. Log into Shiprocket")
                print("  2. Go to: Settings → API → Add New API User")
                print("  3. Create a new API user with a unique email")
                print("  4. Update Doppler with the new credentials:")
                print("     - SHIPROCKET_API_EMAIL: <api_user_email>")
                print("     - SHIPROCKET_API_PASSWORD: <password_from_email>")
                print()
                print("Response Body:")
                print(f"  {response.text}")
                return False

            elif response.status_code == 401:
                print("❌ ERROR: 401 Unauthorized")
                print()
                print("The email or password is incorrect.")
                print()
                print("Steps to Fix:")
                print("  1. Verify the API user email and password")
                print("  2. Reset password if needed from Shiprocket dashboard")
                print("  3. Update credentials in Doppler")
                print()
                print("Response Body:")
                print(f"  {response.text}")
                return False

            else:
                print(f"❌ ERROR: Unexpected status code {response.status_code}")
                print()
                print("Response Body:")
                print(f"  {response.text}")
                return False

    except httpx.RequestError as e:
        print(f"❌ ERROR: Network error")
        print(f"   {str(e)}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Unexpected error")
        print(f"   {str(e)}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_shiprocket_auth())
    sys.exit(0 if success else 1)
