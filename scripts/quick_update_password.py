"""
Quick Password Update for Shiprocket
"""

import psycopg2

DATABASE_URL = "postgresql://postgres:AXAVbrPvtStBmpObpiyoQufpkPtAvmeI@nozomi.proxy.rlwy.net:29493/railway"

# REPLACE THIS WITH YOUR ACTUAL SHIPROCKET LOGIN PASSWORD
# The password you use to log into shiprocket.in dashboard
YOUR_PASSWORD = "YOUR_PASSWORD_HERE"

def update_password():
    if YOUR_PASSWORD == "YOUR_PASSWORD_HERE":
        print("❌ Please edit this script and replace YOUR_PASSWORD_HERE with your actual password")
        print("   Line 11: YOUR_PASSWORD = \"your_actual_password\"")
        return

    print("🔄 Updating Shiprocket password in database...")

    # Parse database URL
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
    user, db_password, host, port, database = match.groups()

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
    """, (YOUR_PASSWORD,))

    conn.commit()

    print("✅ Password updated successfully!")
    print("\n📝 Next: Run python scripts/test_shiprocket_auth.py")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    update_password()
