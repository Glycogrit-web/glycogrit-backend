#!/usr/bin/env python3
"""
Script to add sample events/challenges to the database
Run this from the project root: python scripts/add_sample_events.py
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.event import Event
from app.models.category import EventCategory


def create_sample_events(db: Session):
    """Create sample events for testing"""

    # Get categories
    categories = db.query(EventCategory).all()
    running_cat = next((c for c in categories if c.name.lower() == 'running'), None)
    cycling_cat = next((c for c in categories if c.name.lower() == 'cycling'), None)
    mixed_cat = next((c for c in categories if c.name.lower() == 'mixed'), None)

    today = datetime.now().date()

    sample_events = [
        {
            "name": "30-Day Running Challenge",
            "slug": "30-day-running-challenge",
            "description": "Build your running habit with our 30-day challenge. Run at least 3km every day for 30 days.",
            "event_type": "running",
            "category_id": running_cat.id if running_cat else None,
            "status": "registration_open",
            "start_date": today,
            "end_date": today + timedelta(days=30),
            "location": "Virtual - Anywhere",
            "total_distance": 90.0,
            "max_participants": 1000,
            "current_participants": 0,
            "registration_fee": 0.0,
            "currency": "INR",
            "difficulty_level": "beginner",
            "goals": ["Run 3km daily", "Complete 30 consecutive days", "Build a running habit"],
            "rewards": ["Digital certificate", "30-Day Runner badge", "Entry into prize draw"],
            "rules": "Must log at least 3km run each day\nRest days allowed with prior notification\nActivity must be verified via tracking app",
            "is_virtual": True,
            "is_featured": True,
            "banner_image_url": "/images/challenges/30-day-running.jpg"
        },
        {
            "name": "Mumbai Half Marathon Training",
            "slug": "mumbai-half-marathon-training",
            "description": "12-week structured training program to prepare you for a half marathon (21.1km). Perfect for intermediate runners.",
            "event_type": "marathon",
            "category_id": running_cat.id if running_cat else None,
            "status": "registration_open",
            "start_date": today + timedelta(days=7),
            "end_date": today + timedelta(days=91),
            "location": "Mumbai, Maharashtra",
            "total_distance": 21.1,
            "max_participants": 500,
            "current_participants": 0,
            "registration_fee": 1500.0,
            "currency": "INR",
            "difficulty_level": "intermediate",
            "goals": ["Complete 21.1km race", "Improve endurance", "Follow structured training plan"],
            "rewards": ["Race entry included", "Training plan access", "Finisher medal"],
            "rules": "Must complete weekly long runs\nFollow the provided training schedule\nParticipate in group runs (optional)",
            "is_virtual": False,
            "is_featured": True,
            "banner_image_url": "/images/challenges/mumbai-half-marathon.jpg"
        },
        {
            "name": "Cycling Century Challenge",
            "slug": "cycling-century-challenge",
            "description": "Ride 100km in a single day! Join cyclists across India in this epic one-day challenge.",
            "event_type": "cycling",
            "category_id": cycling_cat.id if cycling_cat else None,
            "status": "registration_open",
            "start_date": today + timedelta(days=14),
            "end_date": today + timedelta(days=14),
            "location": "Multiple cities - Virtual",
            "total_distance": 100.0,
            "max_participants": 2000,
            "current_participants": 0,
            "registration_fee": 500.0,
            "currency": "INR",
            "difficulty_level": "advanced",
            "goals": ["Complete 100km in one day", "Join the Century Club", "Push your limits"],
            "rewards": ["Century Club badge", "Digital finisher certificate", "Exclusive jersey (top 100)"],
            "rules": "Must complete 100km within 24 hours\nActivity must be GPS tracked\nSafety gear mandatory",
            "is_virtual": True,
            "is_featured": True,
            "banner_image_url": "/images/challenges/century-challenge.jpg"
        },
        {
            "name": "5K for Beginners",
            "slug": "5k-for-beginners",
            "description": "Never run before? Start here! An 8-week program designed to take you from couch to running 5km.",
            "event_type": "running",
            "category_id": running_cat.id if running_cat else None,
            "status": "registration_open",
            "start_date": today + timedelta(days=3),
            "end_date": today + timedelta(days=59),
            "location": "Virtual - Anywhere",
            "total_distance": 5.0,
            "max_participants": 1500,
            "current_participants": 0,
            "registration_fee": 0.0,
            "currency": "INR",
            "difficulty_level": "beginner",
            "goals": ["Run 5km continuously", "Build fitness foundation", "Enjoy running"],
            "rewards": ["5K Finisher badge", "Training guide", "Community support"],
            "rules": "Follow the couch-to-5k program\nProgress at your own pace\nLog all activities",
            "is_virtual": True,
            "is_featured": False,
            "banner_image_url": "/images/challenges/5k-beginners.jpg"
        },
        {
            "name": "Delhi 10K Trail Run",
            "slug": "delhi-10k-trail-run",
            "description": "Experience the beauty of Delhi Ridge on this scenic 10km trail run. Mix of terrain and challenge.",
            "event_type": "running",
            "category_id": running_cat.id if running_cat else None,
            "status": "registration_open",
            "start_date": today + timedelta(days=21),
            "end_date": today + timedelta(days=21),
            "location": "Delhi Ridge, New Delhi",
            "total_distance": 10.0,
            "max_participants": 300,
            "current_participants": 0,
            "registration_fee": 800.0,
            "currency": "INR",
            "difficulty_level": "intermediate",
            "goals": ["Complete the trail run", "Experience nature", "Challenge yourself on varied terrain"],
            "rewards": ["Finisher medal", "Event t-shirt", "Refreshments and breakfast"],
            "rules": "Trail running shoes recommended\nCarry water bottle\nFollow trail markers",
            "is_virtual": False,
            "is_featured": False,
            "banner_image_url": "/images/challenges/delhi-trail-run.jpg"
        },
        {
            "name": "Ultimate Fitness Challenge",
            "slug": "ultimate-fitness-challenge",
            "description": "A 6-week multi-sport challenge combining running, cycling, and strength training. For the serious fitness enthusiast.",
            "event_type": "mixed",
            "category_id": mixed_cat.id if mixed_cat else None,
            "status": "registration_open",
            "start_date": today + timedelta(days=10),
            "end_date": today + timedelta(days=52),
            "location": "Virtual - Anywhere",
            "total_distance": 200.0,
            "max_participants": 500,
            "current_participants": 0,
            "registration_fee": 2000.0,
            "currency": "INR",
            "difficulty_level": "advanced",
            "goals": ["Complete 100km running", "Complete 100km cycling", "30 strength sessions"],
            "rewards": ["Ultimate Fitness badge", "Personalized report", "Premium finisher kit"],
            "rules": "Must complete all three disciplines\nLog all activities with proof\nMinimum weekly targets must be met",
            "is_virtual": True,
            "is_featured": True,
            "banner_image_url": "/images/challenges/ultimate-fitness.jpg"
        },
        {
            "name": "Bangalore Night Riders - 50K",
            "slug": "bangalore-night-riders-50k",
            "description": "Join us for a thrilling 50km night cycling event through Bangalore's illuminated streets. Starts at 9 PM!",
            "event_type": "cycling",
            "category_id": cycling_cat.id if cycling_cat else None,
            "status": "registration_open",
            "start_date": today + timedelta(days=28),
            "end_date": today + timedelta(days=28),
            "location": "Bangalore, Karnataka",
            "total_distance": 50.0,
            "max_participants": 400,
            "current_participants": 0,
            "registration_fee": 600.0,
            "currency": "INR",
            "difficulty_level": "intermediate",
            "goals": ["Complete 50km night ride", "Experience Bangalore by night", "Group cycling fun"],
            "rewards": ["Night Rider badge", "Event jersey", "Midnight refreshments"],
            "rules": "Working lights on bike mandatory\nReflective gear required\nStay with the group",
            "is_virtual": False,
            "is_featured": False,
            "banner_image_url": "/images/challenges/night-riders.jpg"
        },
        {
            "name": "21-Day Yoga & Run Combo",
            "slug": "21-day-yoga-run-combo",
            "description": "Perfect balance of flexibility and endurance. Combine daily yoga sessions with progressive running for holistic fitness.",
            "event_type": "mixed",
            "category_id": mixed_cat.id if mixed_cat else None,
            "status": "registration_open",
            "start_date": today + timedelta(days=5),
            "end_date": today + timedelta(days=26),
            "location": "Virtual - Anywhere",
            "total_distance": 42.0,
            "max_participants": 800,
            "current_participants": 0,
            "registration_fee": 500.0,
            "currency": "INR",
            "difficulty_level": "beginner",
            "goals": ["Practice yoga daily", "Run 2km daily", "Build mind-body connection"],
            "rewards": ["Wellness Warrior badge", "Yoga video library access", "Nutrition guide"],
            "rules": "Complete both yoga and run each day\nMinimum 20 minutes yoga\nLog all activities",
            "is_virtual": True,
            "is_featured": True,
            "banner_image_url": "/images/challenges/yoga-run-combo.jpg"
        }
    ]

    created_events = []
    for event_data in sample_events:
        # Check if event already exists
        existing = db.query(Event).filter(Event.slug == event_data["slug"]).first()
        if existing:
            print(f"Event '{event_data['name']}' already exists, skipping...")
            continue

        event = Event(**event_data)
        db.add(event)
        created_events.append(event_data["name"])

    db.commit()
    return created_events


def main():
    """Main function"""
    print("🌱 Adding sample events to database...")

    db = SessionLocal()
    try:
        created = create_sample_events(db)
        print(f"\n✅ Successfully created {len(created)} events:")
        for name in created:
            print(f"  - {name}")
        print("\n🎉 Done!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
