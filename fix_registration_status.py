#!/usr/bin/env python3
"""
Fix Registration Status Script
Updates cancelled registration to confirmed for testing
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text

from app.core.database import SessionLocal


def fix_registration():
    db = SessionLocal()

    try:
        # Find cancelled registrations for test1+++++ event
        result = db.execute(text("""
            SELECT
                r.id,
                r.registration_number,
                r.status,
                u.email,
                e.name as event_name
            FROM registrations r
            JOIN users u ON r.user_id = u.id
            JOIN events e ON r.event_id = e.id
            WHERE e.slug = 'test1+++++'
            AND r.status = 'cancelled'
        """))

        cancelled_regs = result.fetchall()

        if not cancelled_regs:
            print("✓ No cancelled registrations found for test1+++++")
            return

        print(f"Found {len(cancelled_regs)} cancelled registration(s):")
        for reg in cancelled_regs:
            print(f"\n  ID: {reg.id}")
            print(f"  Reg #: {reg.registration_number}")
            print(f"  User: {reg.email}")
            print(f"  Event: {reg.event_name}")
            print(f"  Status: {reg.status}")

        # Ask for confirmation
        print("\n" + "=" * 60)
        response = input("Update these registrations to 'confirmed'? (yes/no): ")

        if response.lower() != "yes":
            print("Cancelled. No changes made.")
            return

        # Update to confirmed
        for reg in cancelled_regs:
            db.execute(
                text("""
                UPDATE registrations
                SET status = 'confirmed'
                WHERE id = :reg_id
            """),
                {"reg_id": reg.id},
            )
            print(f"✓ Updated registration {reg.registration_number} to 'confirmed'")

        db.commit()
        print("\n✅ All registrations updated successfully!")
        print("\n🔄 Please refresh your browser to see the changes.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    fix_registration()
