#!/usr/bin/env python3
"""Check all registrations for test event"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import SessionLocal

db = SessionLocal()

try:
    # Find ALL registrations for test1+++++ event
    result = db.execute(text("""
        SELECT
            r.id,
            r.registration_number,
            r.status,
            r.user_id,
            u.email,
            e.name as event_name,
            e.slug as event_slug
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        JOIN events e ON r.event_id = e.id
        WHERE e.slug = 'test1+++++'
        ORDER BY r.id DESC
    """))

    registrations = result.fetchall()

    if not registrations:
        print("❌ No registrations found for test1+++++")
    else:
        print(f"✓ Found {len(registrations)} registration(s) for test1+++++:\n")
        for reg in registrations:
            print(f"ID: {reg.id}")
            print(f"Registration #: {reg.registration_number}")
            print(f"User ID: {reg.user_id}")
            print(f"User Email: {reg.email}")
            print(f"Status: {reg.status}")
            print(f"Event: {reg.event_name} ({reg.event_slug})")
            print("-" * 60)

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    db.close()
