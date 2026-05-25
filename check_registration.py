#!/usr/bin/env python3
"""Check registration status for a specific event"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.event import Event
from app.models.registration import Registration
from app.models.user import User

db = SessionLocal()

# Find the test event
event_slug = "test1+++++"
event = db.query(Event).filter(Event.slug == event_slug).first()

if event:
    print(f"✓ Event found: {event.title} (ID: {event.id})")
    print(f"  Slug: {event.slug}")
    print("\n" + "="*60)
    print("REGISTRATIONS FOR THIS EVENT:")
    print("="*60 + "\n")

    registrations = db.query(Registration).filter(Registration.event_id == event.id).all()

    if not registrations:
        print("❌ No registrations found for this event")
    else:
        for idx, reg in enumerate(registrations, 1):
            user = db.query(User).filter(User.id == reg.user_id).first()
            print(f"{idx}. Registration #{reg.registration_number}")
            print(f"   User: {user.email if user else 'Unknown'} (ID: {reg.user_id})")
            print(f"   Status: {reg.status}")
            print(f"   Tier: {reg.tier_name if hasattr(reg, 'tier_name') else 'N/A'}")
            print(f"   Registered at: {reg.registered_at}")
            print()
else:
    print(f"❌ Event '{event_slug}' not found")
    print("\nAvailable events:")
    events = db.query(Event).limit(10).all()
    for e in events:
        print(f"  - {e.title} (slug: {e.slug})")

db.close()
