#!/usr/bin/env python3
"""
Fix missing activity_progress records for registrations that have event_activity_id
but no corresponding activity_progress record.
"""

import os
import sys
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database URL
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:AXAVbrPvtStBmpObpiyoQufpkPtAvmeI@nozomi.proxy.rlwy.net:29493/railway')

def fix_missing_progress():
    """Create missing activity_progress records for registrations with activities."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Find registrations that have an activity but no progress record
        result = session.execute(text("""
            SELECT
                r.id as registration_id,
                r.user_id,
                r.event_id,
                r.event_activity_id,
                a.distance as target_distance,
                r.registration_number
            FROM registrations r
            LEFT JOIN activity_progress ap ON r.id = ap.registration_id
            LEFT JOIN event_activities a ON r.event_activity_id = a.id
            WHERE r.event_activity_id IS NOT NULL
              AND ap.id IS NULL
              AND a.distance IS NOT NULL
            ORDER BY r.event_id, r.id
        """))

        registrations = result.fetchall()

        if not registrations:
            print("✅ No missing activity_progress records found.")
            return

        print(f"Found {len(registrations)} registrations missing activity_progress records:")
        print("-" * 100)

        for reg in registrations:
            reg_id, user_id, event_id, activity_id, target_distance, reg_number = reg
            print(f"  {reg_number}: user_id={user_id}, event_id={event_id}, activity_id={activity_id}, target={target_distance}km")

            # Create the activity_progress record
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
                    :event_id,
                    :activity_id,
                    0.00,
                    :target_distance,
                    NOW(),
                    NOW()
                )
            """), {
                'user_id': user_id,
                'registration_id': reg_id,
                'event_id': event_id,
                'activity_id': activity_id,
                'target_distance': target_distance
            })

        session.commit()
        print(f"\n✅ Successfully created {len(registrations)} activity_progress records!")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    fix_missing_progress()
