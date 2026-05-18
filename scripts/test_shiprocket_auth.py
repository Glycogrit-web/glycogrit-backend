"""
Test Shiprocket API Authentication
Verifies that credentials work and token can be generated
"""

import httpx
import psycopg2
import asyncio
from datetime import datetime, timedelta

# Database connection
DATABASE_URL = "postgresql://postgres:AXAVbrPvtStBmpObpiyoQufpkPtAvmeI@nozomi.proxy.rlwy.net:29493/railway"

# Shiprocket API
BASE_URL = "https://apiv2.shiprocket.in/v1/external"


async def test_authentication():
    """Test Shiprocket authentication"""
    print("=" * 60)
    print("   TEST SHIPROCKET API AUTHENTICATION")
    print("=" * 60)
    print("\n🔐 Testing Shiprocket API Connection...\n")

    # Parse database URL
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
    if not match:
        print("❌ Invalid database URL")
        return

    user, password, host, port, database = match.groups()

    try:
        # Get credentials from database
        print("📊 Fetching credentials from database...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT email, encrypted_password, default_pickup_location
            FROM shiprocket_config
            WHERE is_active = TRUE
            LIMIT 1
        """)

        result = cursor.fetchone()
        if not result:
            print("❌ No active Shiprocket configuration found in database")
            print("   Run: python scripts/setup_shiprocket_simple.py")
            cursor.close()
            conn.close()
            return

        email, encrypted_password, pickup_location = result
        print(f"✅ Found configuration for: {email}")
        print(f"   Pickup Location: {pickup_location}\n")

        # Test authentication
        print("🔑 Authenticating with Shiprocket API...")
        print(f"   URL: {BASE_URL}/auth/login")
        print(f"   Email: {email}")

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": email,
                    "password": encrypted_password
                }
            )

            print(f"   Status Code: {response.status_code}\n")

            if response.status_code == 200:
                data = response.json()
                token = data.get("token")

                if token:
                    print("✅ Authentication successful!")
                    print(f"   Token (first 50 chars): {token[:50]}...")
                    print(f"   Token length: {len(token)} characters")

                    # Store token in database
                    token_expires_at = datetime.utcnow() + timedelta(days=10)

                    cursor.execute("""
                        UPDATE shiprocket_config
                        SET
                            access_token = %s,
                            token_expires_at = %s,
                            updated_at = NOW()
                        WHERE email = %s
                    """, (token, token_expires_at, email))

                    conn.commit()

                    print(f"   Token expires: {token_expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    print("\n💾 Token saved to database")

                    print("\n🎉 Shiprocket integration is READY!")

                    print("\n📝 Next Steps:")
                    print("   1. Your Shiprocket integration is fully configured")
                    print("   2. You can now create orders using RewardFulfillmentService")
                    print("   3. Test with: python scripts/test_create_order.py")

                    print("\n💡 How to use in your code:")
                    print("   from app.services.shiprocket import RewardFulfillmentService")
                    print("   service = RewardFulfillmentService(db)")
                    print("   result = await service.create_shiprocket_order(reward_id)")

                else:
                    print("❌ No token in response")
                    print(f"   Response: {data}")

            else:
                print(f"❌ Authentication failed!")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text}")

                # Common errors
                if response.status_code == 401:
                    print("\n💡 This usually means:")
                    print("   - Incorrect email or password")
                    print("   - Check your Shiprocket credentials")
                elif response.status_code == 422:
                    print("\n💡 This usually means:")
                    print("   - Invalid request format")
                    print("   - Check that email/password are correct")

        cursor.close()
        conn.close()

    except httpx.RequestError as e:
        print(f"❌ Network error: {str(e)}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print(f"   Type: {type(e).__name__}")
        raise


if __name__ == "__main__":
    asyncio.run(test_authentication())

    print("\n" + "=" * 60)
    print("   TEST COMPLETE")
    print("=" * 60)
