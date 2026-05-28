#!/usr/bin/env python3
"""
Fix Event 28 Progress Tracking

This script creates missing activity_progress records for Event 28 registrations
by mapping tier names to appropriate activities.

IMPORTANT: This makes assumptions about which activities users selected based on
their tier names. Review the mapping carefully before running.

Usage:
    python fix_event_28_progress.py --dry-run  # Preview changes
    python fix_event_28_progress.py           # Apply changes
"""

import argparse
import os
import sys
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database URL
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:AXAVbrPvtStBmpObpiyoQufpkPtAvmeI@nozomi.proxy.rlwy.net:29493/railway')


def get_tier_to_activity_mapping(session):
    """
    Map Event 28 tier names to activity IDs.

    This mapping is based on tier name analysis and available activities.
    Adjust as needed based on actual event tiers.
    """
    # Get all tiers for Event 28
    result = session.execute(text("""
        SELECT id, tier_name, tier_order
        FROM event_registration_tiers
        WHERE event_id = 28
        ORDER BY tier_order
    """))

    tiers = result.fetchall()

    print("\nEvent 28 Tiers:")
    print("="*80)
    for tier in tiers:
        print(f"  Tier ID {tier.id}: {tier.tier_name} (order: {tier.tier_order})")

    # Get available activities
    result = session.execute(text("""
        SELECT id, name, distance, activity_type
        FROM event_activities
        WHERE activity_type IN ('running', 'cycling')
        ORDER BY distance
    """))

    activities = result.fetchall()

    print("\nAvailable Activities:")
    print("="*80)
    for act in activities:
        print(f"  Activity ID {act.id}: {act.name} ({act.distance} km, {act.activity_type})")

    # Manual mapping - REVIEW THIS CAREFULLY
    # Map tier_name patterns to activity_id
    mapping = {
        # Running activities
        '3': 21,   # 3 km running
        '5': 22,   # 5 km running
        '10': 23,  # 10 km running
        '21': 24,  # 21 km (half marathon) running

        # Cycling activities
        '5_cycle': 25,  # 5 km cycling
        '10_cycle': 26, # 10 km cycling (if exists)
    }

    print("\nTier → Activity Mapping:")
    print("="*80)
    print("This mapping will be used to assign activities to registrations.")
    print("Review carefully before proceeding!")
    print()

    return mapping


def preview_changes(session):
    """Preview what changes will be made without committing."""

    # Get Event 28 registrations that need fixing
    result = session.execute(text("""
        SELECT
            r.id as registration_id,
            r.registration_number,
            r.user_id,
            r.status,
            r.event_activity_id,
            r.current_tier_id,
            t.tier_name
        FROM registrations r
        LEFT JOIN event_registration_tiers t ON r.current_tier_id = t.id
        WHERE r.event_id = 28
        AND r.event_activity_id IS NULL
        ORDER BY r.id
    """))

    registrations = result.fetchall()

    print(f"\nFound {len(registrations)} Event 28 registrations needing activity assignment:")
    print("="*100)

    for reg in registrations:
        print(f"\nRegistration #{reg.registration_number} (ID: {reg.registration_id})")
        print(f"  User ID: {reg.user_id}")
        print(f"  Status: {reg.status}")
        print(f"  Current Tier: {reg.tier_name} (ID: {reg.current_tier_id})")
        print(f"  Activity ID: {reg.event_activity_id} (NULL - needs assignment)")

        # Try to determine activity from tier name
        tier_name_lower = (reg.tier_name or '').lower()
        suggested_activity = None

        if '3' in tier_name_lower and 'km' in tier_name_lower:
            suggested_activity = 21  # 3 km
        elif '5' in tier_name_lower and 'km' in tier_name_lower and 'cycle' not in tier_name_lower:
            suggested_activity = 22  # 5 km running
        elif '10' in tier_name_lower and 'km' in tier_name_lower and 'cycle' not in tier_name_lower:
            suggested_activity = 23  # 10 km running
        elif '21' in tier_name_lower or 'half' in tier_name_lower or 'marathon' in tier_name_lower:
            suggested_activity = 24  # 21 km
        elif 'cycle' in tier_name_lower or 'bike' in tier_name_lower or 'ride' in tier_name_lower:
            if '5' in tier_name_lower:
                suggested_activity = 25  # 5 km cycling

        if suggested_activity:
            print(f"  ✓ Suggested Activity: ID {suggested_activity}")
        else:
            print(f"  ⚠️  WARNING: Cannot determine activity from tier name!")

    return registrations


def apply_fixes(session, dry_run=True):
    """Apply the fixes to create activity_progress records."""

    registrations = preview_changes(session)

    if not registrations:
        print("\n✅ No registrations need fixing!")
        return

    print(f"\n\n{'='*100}")
    if dry_run:
        print("DRY RUN MODE - No changes will be made")
        print("Run without --dry-run to apply changes")
    else:
        print("⚠️  APPLYING CHANGES - This will modify the database!")
    print(f"{'='*100}\n")

    if not dry_run:
        confirm = input("Are you sure you want to proceed? Type 'YES' to confirm: ")
        if confirm != 'YES':
            print("Aborted.")
            return

    changes_made = 0

    for reg in registrations:
        # Determine activity from tier name
        tier_name_lower = (reg.tier_name or '').lower()
        activity_id = None
        activity_distance = None

        if '3' in tier_name_lower and 'km' in tier_name_lower:
            activity_id, activity_distance = 21, Decimal('3.00')
        elif '5' in tier_name_lower and 'km' in tier_name_lower and 'cycle' not in tier_name_lower:
            activity_id, activity_distance = 22, Decimal('5.00')
        elif '10' in tier_name_lower and 'km' in tier_name_lower and 'cycle' not in tier_name_lower:
            activity_id, activity_distance = 23, Decimal('10.00')
        elif '21' in tier_name_lower or 'half' in tier_name_lower or 'marathon' in tier_name_lower:
            activity_id, activity_distance = 24, Decimal('21.00')
        elif 'cycle' in tier_name_lower or 'bike' in tier_name_lower or 'ride' in tier_name_lower:
            if '5' in tier_name_lower:
                activity_id, activity_distance = 25, Decimal('5.00')

        if not activity_id:
            print(f"⚠️  Skipping {reg.registration_number}: Cannot determine activity")
            continue

        if not dry_run:
            # Update registration with activity_id
            session.execute(text("""
                UPDATE registrations
                SET event_activity_id = :activity_id
                WHERE id = :registration_id
            """), {
                'activity_id': activity_id,
                'registration_id': reg.registration_id
            })

            # Create activity_progress record
            session.execute(text("""
                INSERT INTO activity_progress (
                    user_id,
                    registration_id,
                    event_id,
                    activity_id,
                    distance_completed,
                    target_distance,
                    created_at,
                    updated_at
                )
                VALUES (
                    :user_id,
                    :registration_id,
                    28,
                    :activity_id,
                    0.00,
                    :target_distance,
                    NOW(),
                    NOW()
                )
            """), {
                'user_id': reg.user_id,
                'registration_id': reg.registration_id,
                'activity_id': activity_id,
                'target_distance': activity_distance
            })

            print(f"✅ Fixed {reg.registration_number}: Assigned activity {activity_id} ({activity_distance} km)")
            changes_made += 1
        else:
            print(f"[DRY RUN] Would assign activity {activity_id} ({activity_distance} km) to {reg.registration_number}")

    if not dry_run:
        session.commit()
        print(f"\n✅ Successfully fixed {changes_made} registrations!")
        print("\nEvent 28 progress tracking should now work for these registrations.")
    else:
        print(f"\n[DRY RUN] Would fix {len([r for r in registrations if r.tier_name])} registrations")


def main():
    parser = argparse.ArgumentParser(description='Fix Event 28 progress tracking')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying them')
    args = parser.parse_args()

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("\n" + "="*100)
        print("Event 28 Progress Tracking Fix")
        print("="*100)

        # Show tier and activity info
        get_tier_to_activity_mapping(session)

        # Apply fixes
        apply_fixes(session, dry_run=args.dry_run)

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
