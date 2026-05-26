#!/usr/bin/env python3
"""
Cleanup Duplicate Registrations Script
Ensures only ONE active registration per user per event
Keeps the most recent confirmed registration, cancels older ones
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text

from app.core.database import SessionLocal


def cleanup_duplicates():
    db = SessionLocal()

    try:
        # Find users with multiple registrations for the same event
        result = db.execute(text("""
            SELECT
                user_id,
                event_id,
                COUNT(*) as reg_count
            FROM registrations
            WHERE status IN ('confirmed', 'pending')
            GROUP BY user_id, event_id
            HAVING COUNT(*) > 1
        """))

        duplicates = result.fetchall()

        if not duplicates:
            print("✓ No duplicate active registrations found!")
            return

        print(f"Found {len(duplicates)} user(s) with duplicate registrations:\n")

        total_cancelled = 0

        for dup in duplicates:
            user_id = dup.user_id
            event_id = dup.event_id

            # Get all registrations for this user-event combination
            regs_result = db.execute(
                text("""
                SELECT
                    r.id,
                    r.registration_number,
                    r.status,
                    r.registered_at,
                    r.current_tier_id,
                    rt.tier_name,
                    u.email,
                    e.name as event_name
                FROM registrations r
                JOIN users u ON r.user_id = u.id
                JOIN events e ON r.event_id = e.id
                LEFT JOIN registration_tiers rt ON r.current_tier_id = rt.id
                WHERE r.user_id = :user_id
                AND r.event_id = :event_id
                AND r.status IN ('confirmed', 'pending')
                ORDER BY r.registered_at DESC
            """),
                {"user_id": user_id, "event_id": event_id},
            )

            regs = regs_result.fetchall()

            if len(regs) < 2:
                continue

            print(f"User: {regs[0].email}")
            print(f"Event: {regs[0].event_name}")
            print(f"Found {len(regs)} active registrations:")

            # Keep the most recent one (first in DESC order)
            keep_reg = regs[0]
            cancel_regs = regs[1:]

            print(
                f"  ✓ KEEPING:    Reg #{keep_reg.registration_number} - {keep_reg.status} - Tier: {keep_reg.tier_name or 'N/A'} - Date: {keep_reg.registered_at}"
            )

            for cancel_reg in cancel_regs:
                print(
                    f"  ✗ CANCELLING: Reg #{cancel_reg.registration_number} - {cancel_reg.status} - Tier: {cancel_reg.tier_name or 'N/A'} - Date: {cancel_reg.registered_at}"
                )

                # Cancel the older registration
                db.execute(
                    text("""
                    UPDATE registrations
                    SET status = 'cancelled'
                    WHERE id = :reg_id
                """),
                    {"reg_id": cancel_reg.id},
                )

                total_cancelled += 1

            print()

        db.commit()
        print(f"\n✅ Cleanup complete! Cancelled {total_cancelled} duplicate registration(s).")
        print("Each user now has only ONE active registration per event.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("DUPLICATE REGISTRATION CLEANUP")
    print("=" * 60)
    print("\nThis script will:")
    print("1. Find users with multiple active registrations for the same event")
    print("2. Keep the MOST RECENT registration")
    print("3. Cancel all older registrations")
    print("\n" + "=" * 60)

    response = input("\nProceed with cleanup? (yes/no): ")

    if response.lower() == "yes":
        cleanup_duplicates()
    else:
        print("Cancelled. No changes made.")
