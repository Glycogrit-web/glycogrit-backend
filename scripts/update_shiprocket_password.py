"""
Update Shiprocket Password
Use your main account password (the one you use to log into Shiprocket dashboard)
"""

import getpass

import psycopg2

DATABASE_URL = "postgresql://postgres:AXAVbrPvtStBmpObpiyoQufpkPtAvmeI@nozomi.proxy.rlwy.net:29493/railway"

def update_password():
    print("=" * 60)
    print("   UPDATE SHIPROCKET PASSWORD")
    print("=" * 60)
    print("\n📝 Enter your Shiprocket MAIN ACCOUNT password")
    print("   (The password you use to log into shiprocket.in dashboard)\n")

    password = getpass.getpass("Password: ")

    if not password:
        print("❌ Password cannot be empty")
        return

    # Parse database URL
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
    if not match:
        print("❌ Invalid database URL")
        return

    user, db_password, host, port, database = match.groups()

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=db_password
        )
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE shiprocket_config
            SET encrypted_password = %s,
                updated_at = NOW()
            WHERE email = 'teamglycogrit@gmail.com'
        """, (password,))

        conn.commit()

        print("\n✅ Password updated successfully!")
        print("\n📝 Next step:")
        print("   Run: python scripts/test_shiprocket_auth.py")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    update_password()
