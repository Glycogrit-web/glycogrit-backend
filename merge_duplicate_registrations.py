#!/usr/bin/env python3
"""
Merge Duplicate Registrations Script
For users with multiple registration rows for the same event:
- Keep the most recent CONFIRMED registration (if exists)
- Otherwise keep the most recent one
- Delete all other rows
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import SessionLocal

def merge_duplicates():
    db = SessionLocal()

    try:
        # Find users with multiple registrations for the same event (any status)
        result = db.execute(text("""
            SELECT
                user_id,
                event_id,
                COUNT(*) as reg_count
            FROM registrations
            GROUP BY user_id, event_id
            HAVING COUNT(*) > 1
        """))

        duplicates = result.fetchall()

        if not duplicates:
            print("✓ No duplicate registrations found!")
            return

        print(f"Found {len(duplicates)} user(s) with duplicate registrations:\n")

        total_deleted = 0

        for dup in duplicates:
            user_id = dup.user_id
            event_id = dup.event_id

            # Get all registrations for this user-event combination
            regs_result = db.execute(text("""
                SELECT
                    r.id,
                    r.registration_number,
                    r.status,
                    r.registered_at,
                    r.current_tier_id,
                    ert.tier_name,
                    u.email,
                    e.name as event_name
                FROM registrations r
                JOIN users u ON r.user_id = u.id
                JOIN events e ON r.event_id = e.id
                LEFT JOIN event_registration_tiers ert ON r.current_tier_id = ert.id
                WHERE r.user_id = :user_id
                AND r.event_id = :event_id
                ORDER BY
                    CASE WHEN r.status = 'confirmed' THEN 0 ELSE 1 END,
                    r.registered_at DESC
            """), {"user_id": user_id, "event_id": event_id})

            regs = regs_result.fetchall()

            if len(regs) < 2:
                continue

            print(f"User: {regs[0].email}")
            print(f"Event: {regs[0].event_name}")
            print(f"Found {len(regs)} registration rows:")

            # Keep the first one (most recent confirmed, or most recent overall)
            keep_reg = regs[0]
            delete_regs = regs[1:]

            print(f"  ✓ KEEPING:  Reg #{keep_reg.registration_number} - {keep_reg.status} - Tier: {keep_reg.tier_name or 'N/A'} - Date: {keep_reg.registered_at}")

            for delete_reg in delete_regs:
                print(f"  ✗ DELETING: Reg #{delete_reg.registration_number} - {delete_reg.status} - Tier: {delete_reg.tier_name or 'N/A'} - Date: {delete_reg.registered_at}")

                # Delete the duplicate registration
                db.execute(text("""
                    DELETE FROM registrations
                    WHERE id = :reg_id
                """), {"reg_id": delete_reg.id})

                total_deleted += 1

            print()

        db.commit()
        print(f"\n✅ Merge complete! Deleted {total_deleted} duplicate registration(s).")
        print("Each user now has only ONE registration row per event.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("="*60)
    print("MERGE DUPLICATE REGISTRATIONS")
    print("="*60)
    print("\nThis script will:")
    print("1. Find users with multiple registration ROWS for the same event")
    print("2. Keep the MOST RECENT CONFIRMED registration")
    print("3. Or keep the MOST RECENT one if no confirmed exists")
    print("4. DELETE all other duplicate rows")
    print("\n⚠️  WARNING: This permanently deletes rows from database!")
    print("="*60)

    response = input("\nProceed with merge? (yes/no): ")

    if response.lower() == 'yes':
        merge_duplicates()
    else:
        print("Cancelled. No changes made.")
