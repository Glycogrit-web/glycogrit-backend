#!/usr/bin/env python3
"""
Database Management Script
Convenient wrapper for Alembic commands
"""
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))


def print_help():
    """Print help message"""
    print("""
Database Management Commands:

  python manage_db.py migrate [message]   - Create new migration (autogenerate)
  python manage_db.py upgrade             - Apply all pending migrations
  python manage_db.py downgrade [steps]   - Rollback migrations (default: 1 step)
  python manage_db.py current             - Show current migration
  python manage_db.py history             - Show migration history
  python manage_db.py seed                - Seed database with sample data
  python manage_db.py reset               - Reset database (⚠️  DESTRUCTIVE)

Examples:
  python manage_db.py migrate "add user table"
  python manage_db.py upgrade
  python manage_db.py seed
    """)


def run_alembic_command(command: str):
    """Run alembic command"""
    import subprocess
    result = subprocess.run(f"alembic {command}", shell=True)
    return result.returncode


def create_migration(message: str):
    """Create a new migration"""
    print(f"🔧 Creating migration: {message}")
    return run_alembic_command(f'revision --autogenerate -m "{message}"')


def upgrade_database():
    """Upgrade database to latest"""
    print("⬆️  Upgrading database to latest version...")
    return run_alembic_command("upgrade head")


def downgrade_database(steps: int = 1):
    """Downgrade database"""
    print(f"⬇️  Downgrading database by {steps} step(s)...")
    target = f"-{steps}"
    return run_alembic_command(f"downgrade {target}")


def show_current():
    """Show current migration"""
    print("📍 Current migration:")
    return run_alembic_command("current")


def show_history():
    """Show migration history"""
    print("📜 Migration history:")
    return run_alembic_command("history")


def seed_database():
    """Seed database with sample data"""
    print("🌱 Seeding database with sample data...")

    from sqlalchemy.orm import Session
    from app.core.database import engine, SessionLocal
    from app.models import User, Event, EventCategory, Registration
    import bcrypt

    def hash_password(password: str) -> str:
        """Hash password using bcrypt directly"""
        # Encode password to bytes, truncate if needed (bcrypt max is 72 bytes)
        password_bytes = password.encode('utf-8')[:72]
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    db = SessionLocal()
    try:
        # Check if data already exists
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"⚠️  Database already has {existing_users} users. Skipping seed.")
            return 0

        # Create admin user
        admin = User(
            email="admin@glycogrit.com",
            password_hash=hash_password("admin123"),
            first_name="Admin",
            last_name="User",
            city="Bangalore",
            state="Karnataka",
            country="India",
            is_active=True,
            email_verified=True
        )
        db.add(admin)
        db.flush()
        print("✅ Created admin user: admin@glycogrit.com / admin123")

        # Create organizer user
        organizer = User(
            email="organizer@glycogrit.com",
            password_hash=hash_password("organizer123"),
            first_name="Event",
            last_name="Organizer",
            city="Mumbai",
            state="Maharashtra",
            country="India",
            is_active=True,
            email_verified=True
        )
        db.add(organizer)
        db.flush()
        print("✅ Created organizer: organizer@glycogrit.com / organizer123")

        # Create test participants
        participants = [
            ("john.doe@example.com", "John", "Doe", "Delhi"),
            ("jane.smith@example.com", "Jane", "Smith", "Pune"),
        ]

        for email, first, last, city in participants:
            user = User(
                email=email,
                password_hash=hash_password("test123"),
                first_name=first,
                last_name=last,
                city=city,
                state="Maharashtra",
                country="India",
                is_active=True,
                email_verified=True
            )
            db.add(user)
        db.flush()
        print(f"✅ Created {len(participants)} test participants (password: test123)")

        # Create sample event
        from datetime import datetime, timedelta
        event_date = datetime.now() + timedelta(days=60)
        reg_start = datetime.now()
        reg_end = event_date - timedelta(days=5)

        event = Event(
            name="Bangalore Marathon 2026",
            slug="bangalore-marathon-2026",
            description="Join us for the annual Bangalore Marathon! Experience the joy of running through the Garden City.",
            event_type="running",
            status="upcoming",
            start_date=event_date.date(),
            end_date=event_date.date(),
            event_date=event_date,
            registration_start_date=reg_start,
            registration_end_date=reg_end,
            location="Cubbon Park, Bangalore",
            location_name="Cubbon Park",
            city="Bangalore",
            state="Karnataka",
            country="India",
            total_distance=42.195,
            max_participants=5000,
            current_participants=0,
            registration_fee=1200.00,
            currency="INR",
            organizer_id=organizer.id,
            is_featured=True,
            difficulty_level="advanced",
            goals=["Complete 42.195 km", "Finish under 4 hours", "Beat personal record"],
            rewards=["Finisher Medal", "Certificate", "Official T-shirt"],
            banner_image_url="https://example.com/marathon-banner.jpg",
            rules="Must be 18+ years old. Medical certificate required. No refunds after registration."
        )
        db.add(event)
        db.flush()
        print("✅ Created sample event: Bangalore Marathon 2026")

        # Create event categories
        categories = [
            ("Full Marathon", 42.195, 1200.00),
            ("Half Marathon", 21.0975, 900.00),
            ("10K Run", 10.0, 600.00),
        ]

        for name, distance, fee in categories:
            category = EventCategory(
                event_id=event.id,
                name=name,
                distance=distance,
                registration_fee=fee,
                max_participants=2000,
                current_participants=0
            )
            db.add(category)
        db.flush()
        print(f"✅ Created {len(categories)} event categories")

        db.commit()
        print("\n🎉 Database seeded successfully!")
        print("\nTest Accounts:")
        print("  Admin:     admin@glycogrit.com / admin123")
        print("  Organizer: organizer@glycogrit.com / organizer123")
        print("  User:      john.doe@example.com / test123")
        return 0

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


def reset_database():
    """Reset database (drop all tables and recreate)"""
    print("⚠️  WARNING: This will DELETE ALL DATA!")
    response = input("Type 'yes' to confirm: ")
    if response.lower() != 'yes':
        print("❌ Reset cancelled")
        return 1

    print("🗑️  Dropping all tables...")
    from app.core.database import Base, engine
    Base.metadata.drop_all(bind=engine)
    print("✅ All tables dropped")

    print("📋 Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created")

    print("🌱 Seeding database...")
    return seed_database()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print_help()
        return 1

    command = sys.argv[1].lower()

    if command == "help" or command == "-h" or command == "--help":
        print_help()
        return 0

    elif command == "migrate":
        message = sys.argv[2] if len(sys.argv) > 2 else "migration"
        return create_migration(message)

    elif command == "upgrade":
        return upgrade_database()

    elif command == "downgrade":
        steps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        return downgrade_database(steps)

    elif command == "current":
        return show_current()

    elif command == "history":
        return show_history()

    elif command == "seed":
        return seed_database()

    elif command == "reset":
        return reset_database()

    else:
        print(f"❌ Unknown command: {command}")
        print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
