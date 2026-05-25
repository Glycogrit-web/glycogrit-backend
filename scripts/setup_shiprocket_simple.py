"""
Simple Shiprocket Configuration Script
Directly inserts credentials into database without model dependencies
"""

import os

import psycopg2

# Database connection from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/glycogrit")

# Shiprocket credentials from environment variables
SHIPROCKET_EMAIL = os.getenv("SHIPROCKET_EMAIL", "teamglycogrit@gmail.com")
SHIPROCKET_PASSWORD = os.getenv("SHIPROCKET_PASSWORD")  # nosec B105 - Not a hardcoded password
PICKUP_LOCATION = os.getenv("SHIPROCKET_PICKUP_LOCATION", "Home")  # Your PRIMARY pickup location nickname

if not SHIPROCKET_PASSWORD:
    raise ValueError("SHIPROCKET_PASSWORD environment variable must be set")


def configure_shiprocket():
    """Add Shiprocket configuration to database"""
    print("=" * 60)
    print("   SHIPROCKET INTEGRATION SETUP")
    print("=" * 60)
    print("\n🚀 Configuring Shiprocket Integration...\n")

    # Parse database URL
    # postgresql://user:password@host:port/database
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
    if not match:
        print("❌ Invalid database URL")
        return

    user, password, host, port, database = match.groups()

    try:
        # Connect to database
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor()

        # Check if config exists
        cursor.execute("SELECT id, email FROM shiprocket_config WHERE is_active = TRUE LIMIT 1")
        existing = cursor.fetchone()

        if existing:
            config_id, existing_email = existing
            print("⚠️  Shiprocket configuration already exists")
            print(f"   ID: {config_id}")
            print(f"   Email: {existing_email}")

            response = input("\n   Update configuration? (y/n): ")
            if response.lower() != 'y':
                print("❌ Configuration cancelled")
                cursor.close()
                conn.close()
                return

            # Update existing config
            cursor.execute("""
                UPDATE shiprocket_config
                SET
                    email = %s,
                    encrypted_password = %s,
                    default_pickup_location = %s,
                    is_active = TRUE,
                    auto_generate_label = TRUE,
                    auto_schedule_pickup = TRUE,
                    default_weight = 0.5,
                    default_length = 20.0,
                    default_breadth = 15.0,
                    default_height = 5.0,
                    updated_at = NOW()
                WHERE id = %s
            """, (SHIPROCKET_EMAIL, SHIPROCKET_PASSWORD, PICKUP_LOCATION, config_id))

            print("\n✅ Configuration updated successfully!")
        else:
            # Insert new config
            cursor.execute("""
                INSERT INTO shiprocket_config (
                    email,
                    encrypted_password,
                    default_pickup_location,
                    is_active,
                    auto_generate_label,
                    auto_schedule_pickup,
                    default_weight,
                    default_length,
                    default_breadth,
                    default_height,
                    created_at,
                    updated_at
                ) VALUES (
                    %s, %s, %s, TRUE, TRUE, TRUE, 0.5, 20.0, 15.0, 5.0, NOW(), NOW()
                )
            """, (SHIPROCKET_EMAIL, SHIPROCKET_PASSWORD, PICKUP_LOCATION))

            print("\n✅ Configuration added successfully!")

        conn.commit()

        # Display configuration
        print("\n📋 Shiprocket Configuration:")
        print(f"   Email: {SHIPROCKET_EMAIL}")
        print(f"   Pickup Location: {PICKUP_LOCATION}")
        print("   Auto Generate Label: True")
        print("   Auto Schedule Pickup: True")
        print("   Default Package Size: 20x15x5 cm, 0.5 kg")

        print("\n🎉 Configuration saved to database!")

        print("\n📝 Next Steps:")
        print("   1. Test API connection: python scripts/test_shiprocket_auth.py")
        print("   2. Create test order: python scripts/test_create_order.py")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print(f"   Type: {type(e).__name__}")
        raise


if __name__ == "__main__":
    configure_shiprocket()

    print("\n" + "=" * 60)
    print("   SETUP COMPLETE")
    print("=" * 60)
