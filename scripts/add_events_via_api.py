#!/usr/bin/env python3
"""
Script to add sample events via API calls
Run this from anywhere: python scripts/add_events_via_api.py
"""

import requests
from datetime import datetime, timedelta
import json

# API Configuration
API_BASE_URL = "https://web-production-188d1.up.railway.app"
# Login credentials (admin user)
ADMIN_EMAIL = "admin@glycogrit.com"
ADMIN_PASSWORD = "admin123"


def get_auth_token():
    """Login and get authentication token"""
    print("🔐 Logging in as admin...")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        print("✅ Successfully authenticated")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None


def create_events(token):
    """Create sample events via API"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    today = datetime.now().date()

    sample_events = [
        {
            "name": "30-Day Running Challenge",
            "slug": "30-day-running-challenge",
            "description": "Build your running habit with our 30-day challenge. Run at least 3km every day for 30 days.",
            "event_type": "running",
            "status": "registration_open",
            "start_date": str(today),
            "end_date": str(today + timedelta(days=30)),
            "location": "Virtual - Anywhere",
            "total_distance": 90.0,
            "max_participants": 1000,
            "registration_fee": 0.0,
            "currency": "INR",
            "difficulty_level": "beginner",
            "goals": ["Run 3km daily", "Complete 30 consecutive days", "Build a running habit"],
            "rewards": ["Digital certificate", "30-Day Runner badge", "Entry into prize draw"],
            "rules": "Must log at least 3km run each day\nRest days allowed with prior notification\nActivity must be verified via tracking app",
            "is_virtual": True,
            "is_featured": True
        },
        {
            "name": "Mumbai Half Marathon Training",
            "slug": "mumbai-half-marathon-training",
            "description": "12-week structured training program to prepare you for a half marathon (21.1km). Perfect for intermediate runners.",
            "event_type": "marathon",
            "status": "registration_open",
            "start_date": str(today + timedelta(days=7)),
            "end_date": str(today + timedelta(days=91)),
            "location": "Mumbai, Maharashtra",
            "total_distance": 21.1,
            "max_participants": 500,
            "registration_fee": 1500.0,
            "currency": "INR",
            "difficulty_level": "intermediate",
            "goals": ["Complete 21.1km race", "Improve endurance", "Follow structured training plan"],
            "rewards": ["Race entry included", "Training plan access", "Finisher medal"],
            "rules": "Must complete weekly long runs\nFollow the provided training schedule\nParticipate in group runs (optional)",
            "is_virtual": False,
            "is_featured": True
        },
        {
            "name": "Cycling Century Challenge",
            "slug": "cycling-century-challenge",
            "description": "Ride 100km in a single day! Join cyclists across India in this epic one-day challenge.",
            "event_type": "cycling",
            "status": "registration_open",
            "start_date": str(today + timedelta(days=14)),
            "end_date": str(today + timedelta(days=14)),
            "location": "Multiple cities - Virtual",
            "total_distance": 100.0,
            "max_participants": 2000,
            "registration_fee": 500.0,
            "currency": "INR",
            "difficulty_level": "advanced",
            "goals": ["Complete 100km in one day", "Join the Century Club", "Push your limits"],
            "rewards": ["Century Club badge", "Digital finisher certificate", "Exclusive jersey (top 100)"],
            "rules": "Must complete 100km within 24 hours\nActivity must be GPS tracked\nSafety gear mandatory",
            "is_virtual": True,
            "is_featured": True
        },
        {
            "name": "5K for Beginners",
            "slug": "5k-for-beginners",
            "description": "Never run before? Start here! An 8-week program designed to take you from couch to running 5km.",
            "event_type": "running",
            "status": "registration_open",
            "start_date": str(today + timedelta(days=3)),
            "end_date": str(today + timedelta(days=59)),
            "location": "Virtual - Anywhere",
            "total_distance": 5.0,
            "max_participants": 1500,
            "registration_fee": 0.0,
            "currency": "INR",
            "difficulty_level": "beginner",
            "goals": ["Run 5km continuously", "Build fitness foundation", "Enjoy running"],
            "rewards": ["5K Finisher badge", "Training guide", "Community support"],
            "rules": "Follow the couch-to-5k program\nProgress at your own pace\nLog all activities",
            "is_virtual": True,
            "is_featured": False
        },
        {
            "name": "Delhi 10K Trail Run",
            "slug": "delhi-10k-trail-run",
            "description": "Experience the beauty of Delhi Ridge on this scenic 10km trail run. Mix of terrain and challenge.",
            "event_type": "running",
            "status": "registration_open",
            "start_date": str(today + timedelta(days=21)),
            "end_date": str(today + timedelta(days=21)),
            "location": "Delhi Ridge, New Delhi",
            "total_distance": 10.0,
            "max_participants": 300,
            "registration_fee": 800.0,
            "currency": "INR",
            "difficulty_level": "intermediate",
            "goals": ["Complete the trail run", "Experience nature", "Challenge yourself on varied terrain"],
            "rewards": ["Finisher medal", "Event t-shirt", "Refreshments and breakfast"],
            "rules": "Trail running shoes recommended\nCarry water bottle\nFollow trail markers",
            "is_virtual": False,
            "is_featured": False
        },
        {
            "name": "Ultimate Fitness Challenge",
            "slug": "ultimate-fitness-challenge",
            "description": "A 6-week multi-sport challenge combining running, cycling, and strength training. For the serious fitness enthusiast.",
            "event_type": "mixed",
            "status": "registration_open",
            "start_date": str(today + timedelta(days=10)),
            "end_date": str(today + timedelta(days=52)),
            "location": "Virtual - Anywhere",
            "total_distance": 200.0,
            "max_participants": 500,
            "registration_fee": 2000.0,
            "currency": "INR",
            "difficulty_level": "advanced",
            "goals": ["Complete 100km running", "Complete 100km cycling", "30 strength sessions"],
            "rewards": ["Ultimate Fitness badge", "Personalized report", "Premium finisher kit"],
            "rules": "Must complete all three disciplines\nLog all activities with proof\nMinimum weekly targets must be met",
            "is_virtual": True,
            "is_featured": True
        },
        {
            "name": "Bangalore Night Riders - 50K",
            "slug": "bangalore-night-riders-50k",
            "description": "Join us for a thrilling 50km night cycling event through Bangalore's illuminated streets. Starts at 9 PM!",
            "event_type": "cycling",
            "status": "registration_open",
            "start_date": str(today + timedelta(days=28)),
            "end_date": str(today + timedelta(days=28)),
            "location": "Bangalore, Karnataka",
            "total_distance": 50.0,
            "max_participants": 400,
            "registration_fee": 600.0,
            "currency": "INR",
            "difficulty_level": "intermediate",
            "goals": ["Complete 50km night ride", "Experience Bangalore by night", "Group cycling fun"],
            "rewards": ["Night Rider badge", "Event jersey", "Midnight refreshments"],
            "rules": "Working lights on bike mandatory\nReflective gear required\nStay with the group",
            "is_virtual": False,
            "is_featured": False
        },
        {
            "name": "21-Day Yoga & Run Combo",
            "slug": "21-day-yoga-run-combo",
            "description": "Perfect balance of flexibility and endurance. Combine daily yoga sessions with progressive running for holistic fitness.",
            "event_type": "mixed",
            "status": "registration_open",
            "start_date": str(today + timedelta(days=5)),
            "end_date": str(today + timedelta(days=26)),
            "location": "Virtual - Anywhere",
            "total_distance": 42.0,
            "max_participants": 800,
            "registration_fee": 500.0,
            "currency": "INR",
            "difficulty_level": "beginner",
            "goals": ["Practice yoga daily", "Run 2km daily", "Build mind-body connection"],
            "rewards": ["Wellness Warrior badge", "Yoga video library access", "Nutrition guide"],
            "rules": "Complete both yoga and run each day\nMinimum 20 minutes yoga\nLog all activities",
            "is_virtual": True,
            "is_featured": True
        }
    ]

    created = []
    skipped = []

    print(f"\n📝 Creating {len(sample_events)} sample events...")

    for event_data in sample_events:
        print(f"\n  Creating '{event_data['name']}'...")

        response = requests.post(
            f"{API_BASE_URL}/api/v1/events",
            headers=headers,
            json=event_data
        )

        if response.status_code == 201:
            created.append(event_data['name'])
            print(f"    ✅ Created successfully")
        elif response.status_code == 400 and "already exists" in response.text.lower():
            skipped.append(event_data['name'])
            print(f"    ⏭️  Already exists, skipping")
        else:
            print(f"    ❌ Failed: {response.status_code}")
            print(f"       {response.text}")

    return created, skipped


def main():
    """Main function"""
    print("🌱 Adding sample events via API...")
    print(f"   Target: {API_BASE_URL}")

    # Get auth token
    token = get_auth_token()
    if not token:
        print("\n❌ Authentication failed. Cannot proceed.")
        return

    # Create events
    created, skipped = create_events(token)

    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"✅ Created: {len(created)} events")
    if created:
        for name in created:
            print(f"   - {name}")

    if skipped:
        print(f"\n⏭️  Skipped: {len(skipped)} events (already exist)")
        for name in skipped:
            print(f"   - {name}")

    print(f"\n🎉 Done! Total events in database: {len(created) + len(skipped) + 1}")  # +1 for existing Bangalore Marathon


if __name__ == "__main__":
    main()
