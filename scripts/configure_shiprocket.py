"""
Configure Shiprocket Integration
Adds Shiprocket credentials to database and tests connection
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.shiprocket_config import ShiprocketConfig
from app.services.shiprocket.shiprocket_service import ShiprocketService

# Database connection
DATABASE_URL = "postgresql://postgres:AXAVbrPvtStBmpObpiyoQufpkPtAvmeI@nozomi.proxy.rlwy.net:29493/railway"

# Shiprocket credentials
SHIPROCKET_EMAIL = "teamglycogrit@gmail.com"
SHIPROCKET_PASSWORD = "US9AEHCCvUpLo&*kL%0YWOAFxXXiP3df"
PICKUP_LOCATION = "Home"  # Your PRIMARY pickup location nickname


def configure_shiprocket():
    """Add Shiprocket configuration to database"""
    print("🚀 Configuring Shiprocket Integration...\n")

    # Create database connection
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Check if config already exists
        existing_config = db.query(ShiprocketConfig).first()

        if existing_config:
            print("⚠️  Shiprocket configuration already exists")
            print(f"   Email: {existing_config.email}")
            print(f"   Pickup Location: {existing_config.default_pickup_location}")

            response = input("\n   Update configuration? (y/n): ")
            if response.lower() != 'y':
                print("❌ Configuration cancelled")
                return

            # Update existing config
            existing_config.email = SHIPROCKET_EMAIL
            existing_config.encrypted_password = SHIPROCKET_PASSWORD  # TODO: Encrypt in production
            existing_config.default_pickup_location = PICKUP_LOCATION
            existing_config.is_active = True

            print("\n✅ Configuration updated successfully!")
        else:
            # Create new config
            config = ShiprocketConfig(
                email=SHIPROCKET_EMAIL,
                encrypted_password=SHIPROCKET_PASSWORD,  # TODO: Encrypt in production
                default_pickup_location=PICKUP_LOCATION,
                is_active=True,
                auto_generate_label=True,
                auto_schedule_pickup=True,
                default_weight=0.5,  # 500g default for medals/certificates
                default_length=20.0,  # 20cm
                default_breadth=15.0,  # 15cm
                default_height=5.0   # 5cm
            )

            db.add(config)
            print("\n✅ Configuration added successfully!")

        db.commit()

        # Display configuration
        print("\n📋 Shiprocket Configuration:")
        print(f"   Email: {SHIPROCKET_EMAIL}")
        print(f"   Pickup Location: {PICKUP_LOCATION}")
        print("   Auto Generate Label: True")
        print("   Auto Schedule Pickup: True")
        print("   Default Package Size: 20x15x5 cm, 0.5 kg")

    except Exception as e:
        print(f"\n❌ Error configuring Shiprocket: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


async def test_connection():
    """Test Shiprocket API connection"""
    print("\n\n🧪 Testing Shiprocket API Connection...\n")

    # Create database connection
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Initialize service
        service = ShiprocketService(db)

        # Test authentication
        print("🔐 Authenticating with Shiprocket...")
        await service._authenticate()

        if service.token:
            print("✅ Authentication successful!")
            print(f"   Token: {service.token[:50]}...")
            print(f"   Token expires: {service.config.token_expires_at}")

            print("\n🎉 Shiprocket integration is ready to use!")
            print("\n📝 Next Steps:")
            print("   1. Create a test reward in your database")
            print("   2. Run: python scripts/test_create_order.py")
            print("   3. Check Shiprocket dashboard for the order")
        else:
            print("❌ Authentication failed - no token received")

    except Exception as e:
        print(f"❌ Error testing connection: {str(e)}")
        print(f"\n   Details: {type(e).__name__}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("   SHIPROCKET INTEGRATION SETUP")
    print("=" * 60)

    # Step 1: Configure database
    configure_shiprocket()

    # Step 2: Test API connection
    asyncio.run(test_connection())

    print("\n" + "=" * 60)
    print("   SETUP COMPLETE")
    print("=" * 60)
