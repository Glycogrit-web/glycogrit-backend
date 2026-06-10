#!/usr/bin/env python3
"""
Update Shiprocket Token in Railway Database

This script:
1. Authenticates with Shiprocket from local machine (bypasses Railway IP block)
2. Gets a fresh token with current permissions
3. Updates the Railway PostgreSQL database with the new token

Usage:
    doppler run -- python3 update_shiprocket_token.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


async def get_fresh_shiprocket_token() -> dict:
    """Get fresh token from Shiprocket API"""

    # Get credentials from environment
    email = os.getenv("SHIPROCKET_API_EMAIL") or os.getenv("SHIPROCKET_EMAIL")
    password = os.getenv("SHIPROCKET_API_PASSWORD") or os.getenv("SHIPROCKET_PASSWORD")

    if not email or not password:
        print("❌ ERROR: Shiprocket credentials not found in environment")
        print("   Make sure Doppler is configured with:")
        print("   - SHIPROCKET_API_EMAIL")
        print("   - SHIPROCKET_API_PASSWORD")
        return None

    print("🔐 Authenticating with Shiprocket...")
    print(f"   Email: {email}")
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

            if response.status_code == 200:
                data = response.json()
                token = data.get("token")

                print("✅ Authentication successful!")
                print(f"   Token (first 20 chars): {token[:20]}...")
                print(f"   Token length: {len(token)} characters")
                print()

                return {
                    "token": token,
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=9)
                }

            elif response.status_code == 403:
                print("❌ ERROR: 403 Forbidden")
                print("   This means:")
                print("   1. Invalid credentials, OR")
                print("   2. API user doesn't have proper permissions, OR")
                print("   3. Your local IP is also blocked (unlikely)")
                print()
                print(f"   Response: {response.text[:200]}")
                return None

            elif response.status_code == 401:
                print("❌ ERROR: 401 Unauthorized")
                print("   The email or password is incorrect")
                print()
                print(f"   Response: {response.text[:200]}")
                return None

            else:
                print(f"❌ ERROR: Unexpected status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return None

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None


def update_database_token(token: str, expires_at: datetime) -> bool:
    """Update token in Railway PostgreSQL database"""

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment")
        print("   Make sure Doppler is configured with DATABASE_URL")
        return False

    print("📊 Updating Railway database...")
    print(f"   Database: {database_url.split('@')[1] if '@' in database_url else 'unknown'}")
    print()

    try:
        # Create engine and session
        engine = create_engine(database_url)
        session = Session(engine)

        # Update the active Shiprocket config
        result = session.execute(
            text("""
                UPDATE shiprocket_config
                SET access_token = :token,
                    token_expires_at = :expires_at,
                    updated_at = :now
                WHERE is_active = true
                RETURNING id, email
            """),
            {
                "token": token,
                "expires_at": expires_at,
                "now": datetime.now(timezone.utc)
            }
        )

        updated = result.fetchone()

        if updated:
            session.commit()
            config_id, email = updated

            print("✅ Database updated successfully!")
            print(f"   Config ID: {config_id}")
            print(f"   Email: {email}")
            print(f"   Token expires: {expires_at}")
            print()
            return True
        else:
            print("❌ ERROR: No active Shiprocket config found in database")
            print("   Make sure there's a record in shiprocket_config with is_active=true")
            session.rollback()
            return False

    except Exception as e:
        print(f"❌ ERROR: Database update failed")
        print(f"   {str(e)}")
        return False
    finally:
        session.close()
        engine.dispose()


async def main():
    """Main function"""

    print("=" * 70)
    print("Shiprocket Token Update Script")
    print("=" * 70)
    print()
    print("This script will:")
    print("1. Get a fresh token from Shiprocket (from your local machine)")
    print("2. Update the Railway PostgreSQL database with the new token")
    print()
    print("Prerequisites:")
    print("- Doppler configured with Shiprocket credentials")
    print("- Doppler configured with Railway DATABASE_URL")
    print("- Run from local machine (not from Railway)")
    print()
    print("=" * 70)
    print()

    # Step 1: Get fresh token
    token_data = await get_fresh_shiprocket_token()

    if not token_data:
        print("❌ FAILED: Could not get fresh token")
        print()
        print("Troubleshooting:")
        print("1. Verify Shiprocket credentials in Doppler")
        print("2. Check if API user has proper permissions")
        print("3. Try authenticating via Shiprocket dashboard")
        return False

    # Step 2: Update database
    success = update_database_token(token_data["token"], token_data["expires_at"])

    if success:
        print("=" * 70)
        print("✅ SUCCESS: Token updated!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Railway backend will now use the fresh token")
        print("2. Token is valid until:", token_data["expires_at"])
        print("3. Test the 'Ready to Ship' button in admin dashboard")
        print()
        print("Note: You'll need to run this script again before the token expires")
        print("      (every 9 days, or whenever permissions change)")
        print()
        return True
    else:
        print("=" * 70)
        print("❌ FAILED: Could not update database")
        print("=" * 70)
        print()
        print("Troubleshooting:")
        print("1. Verify DATABASE_URL in Doppler")
        print("2. Check database connectivity")
        print("3. Verify shiprocket_config table exists")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
