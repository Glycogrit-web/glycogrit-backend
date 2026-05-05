#!/usr/bin/env python3
"""
Manual Certificate System Testing Script

This script helps you test the certificate generation system manually
when database is accessible. It creates test data, generates certificates,
and verifies the system works end-to-end.

Usage:
    python test_certificate_manual.py [--cleanup]

Options:
    --cleanup    Remove all test data after running tests
"""
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.user import User
from app.models.event import Event
from app.models.registration import Registration
from app.models.activity_progress import ActivityProgress
from app.models.user_reward import UserReward
from app.models.event_registration_tier import EventRegistrationTier
from app.core.enums import RewardType, RewardStatus
from app.services.certificate_service import CertificateService


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(msg: str):
    """Print section header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_success(msg: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")


def print_error(msg: str):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")


def print_info(msg: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")


def print_warning(msg: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")


def setup_test_data(db: Session) -> dict:
    """Create test data for certificate generation."""
    print_header("Setting Up Test Data")

    # Create test user
    print_info("Creating test user...")
    test_user = User(
        email="cert_test@glycogrit.com",
        first_name="Certificate",
        last_name="Tester",
        is_active=True,
        email_verified=True,
        is_admin=False
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    print_success(f"Created user: {test_user.email} (ID: {test_user.id})")

    # Create test event
    print_info("Creating test event...")
    now = datetime.now()
    test_event = Event(
        name="Certificate Test Marathon 2024",
        slug="cert-test-marathon-2024",
        description="Test event for certificate generation",
        status="published",
        event_date=now + timedelta(days=30),
        event_end_date=now + timedelta(days=60),
        registration_start_date=now - timedelta(days=7),
        registration_end_date=now + timedelta(days=25),
        location_name="Virtual",
        city="Mumbai",
        state="Maharashtra",
        country="India",
        is_virtual=True,
        uses_tier_system=True,
        organizer_id=test_user.id
    )
    db.add(test_event)
    db.commit()
    db.refresh(test_event)
    print_success(f"Created event: {test_event.name} (ID: {test_event.id})")

    # Create tier
    print_info("Creating registration tier...")
    tier = EventRegistrationTier(
        event_id=test_event.id,
        tier_name="Test Tier",
        tier_slug="test-tier",
        tier_order=0,
        price=Decimal("0.00"),
        currency="INR",
        max_registrations=100,
        requires_payment=False
    )
    db.add(tier)
    db.commit()
    db.refresh(tier)
    print_success(f"Created tier: {tier.tier_name} (ID: {tier.id})")

    # Create completed registration
    print_info("Creating completed registration...")
    registration = Registration(
        user_id=test_user.id,
        event_id=test_event.id,
        current_tier_id=tier.id,
        registration_number=f"CERT-TEST-{test_event.id}-001",
        participant_name=f"{test_user.first_name} {test_user.last_name}",
        status="confirmed",
        uses_tier_system=True
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    print_success(f"Created registration: {registration.registration_number} (ID: {registration.id})")

    # Create completed activity
    print_info("Creating completed activity...")
    activity = ActivityProgress(
        registration_id=registration.id,
        activity_name="5K Running Challenge",
        target_distance=5.0,
        distance_completed=5.5,
        is_completed=True,
        completed_at=datetime.utcnow()
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    print_success(f"Created activity: {activity.activity_name} (completed: {activity.distance_completed}km)")

    return {
        'user': test_user,
        'event': test_event,
        'tier': tier,
        'registration': registration,
        'activity': activity
    }


def test_certificate_generation(db: Session, registration_id: int) -> bool:
    """Test single certificate generation."""
    print_header("Testing Certificate Generation")

    try:
        service = CertificateService()

        print_info(f"Generating certificate for registration {registration_id}...")
        start_time = datetime.now()

        certificate_url = service.generate_certificate(
            registration_id=registration_id,
            force_regenerate=False,
            db=db
        )

        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        print_success(f"Certificate generated in {elapsed:.0f}ms")
        print_info(f"Certificate URL: {certificate_url}")

        # Verify reward record
        reward = db.query(UserReward).filter(
            UserReward.registration_id == registration_id,
            UserReward.reward_type == RewardType.CERTIFICATE
        ).first()

        if reward:
            print_success("Reward record created successfully")
            print_info(f"Certificate Number: {reward.certificate_number}")
            print_info(f"Download Count: {reward.download_count}/{reward.download_limit}")
            print_info(f"Status: {reward.status.value}")
            return True
        else:
            print_error("Reward record not found!")
            return False

    except Exception as e:
        print_error(f"Certificate generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_caching(db: Session, registration_id: int) -> bool:
    """Test certificate caching behavior."""
    print_header("Testing Certificate Caching")

    try:
        service = CertificateService()

        # First call (should use cached)
        print_info("First call (cached retrieval)...")
        start_time = datetime.now()
        url1 = service.generate_certificate(registration_id=registration_id, force_regenerate=False, db=db)
        elapsed1 = (datetime.now() - start_time).total_seconds() * 1000

        # Second call (should also use cached)
        print_info("Second call (cached retrieval)...")
        start_time = datetime.now()
        url2 = service.generate_certificate(registration_id=registration_id, force_regenerate=False, db=db)
        elapsed2 = (datetime.now() - start_time).total_seconds() * 1000

        print_success(f"First call: {elapsed1:.0f}ms")
        print_success(f"Second call: {elapsed2:.0f}ms (should be faster)")

        if url1 == url2:
            print_success("URLs match - caching working correctly")
            return True
        else:
            print_error("URLs don't match - caching issue!")
            return False

    except Exception as e:
        print_error(f"Caching test failed: {str(e)}")
        return False


def test_download_tracking(db: Session, registration_id: int, user_id: int) -> bool:
    """Test download tracking and limits."""
    print_header("Testing Download Tracking")

    try:
        service = CertificateService()

        # Get initial count
        reward = db.query(UserReward).filter(
            UserReward.registration_id == registration_id,
            UserReward.reward_type == RewardType.CERTIFICATE
        ).first()

        if not reward:
            print_error("No reward record found")
            return False

        initial_count = reward.download_count
        print_info(f"Initial download count: {initial_count}/{reward.download_limit}")

        # Track download
        print_info("Tracking first download...")
        result = service.track_certificate_download(
            registration_id=registration_id,
            user_id=user_id,
            db=db
        )

        print_success(f"Download tracked successfully")
        print_info(f"New count: {result['download_count']}/{result['download_limit']}")
        print_info(f"Remaining: {result['remaining_downloads']}")
        print_info(f"Last downloaded: {result['last_downloaded_at']}")

        # Verify count incremented
        db.refresh(reward)
        if reward.download_count == initial_count + 1:
            print_success("Download count incremented correctly")
        else:
            print_error(f"Download count mismatch: expected {initial_count + 1}, got {reward.download_count}")
            return False

        # Test limit enforcement (set to limit first)
        print_info("\nTesting limit enforcement...")
        reward.download_count = reward.download_limit
        db.commit()

        try:
            service.track_certificate_download(
                registration_id=registration_id,
                user_id=user_id,
                db=db
            )
            print_error("Limit not enforced - download succeeded when it should have failed!")
            return False
        except ValueError as e:
            if "limit exceeded" in str(e).lower():
                print_success("Limit enforcement working correctly")
                return True
            else:
                print_error(f"Unexpected error: {str(e)}")
                return False

    except Exception as e:
        print_error(f"Download tracking test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_unlimited_downloads(db: Session, registration_id: int, user_id: int) -> bool:
    """Test unlimited downloads (limit=0)."""
    print_header("Testing Unlimited Downloads")

    try:
        # Set unlimited
        reward = db.query(UserReward).filter(
            UserReward.registration_id == registration_id,
            UserReward.reward_type == RewardType.CERTIFICATE
        ).first()

        if not reward:
            print_error("No reward record found")
            return False

        print_info("Setting download_limit to 0 (unlimited)...")
        reward.download_limit = 0
        reward.download_count = 100  # Set high count
        db.commit()

        service = CertificateService()

        print_info("Tracking download with unlimited setting...")
        result = service.track_certificate_download(
            registration_id=registration_id,
            user_id=user_id,
            db=db
        )

        if result['remaining_downloads'] == -1:
            print_success("Unlimited downloads working correctly (remaining = -1)")
            print_info(f"Download count: {result['download_count']}")
            return True
        else:
            print_error(f"Unexpected remaining_downloads: {result['remaining_downloads']}")
            return False

    except Exception as e:
        print_error(f"Unlimited downloads test failed: {str(e)}")
        return False


def cleanup_test_data(db: Session, test_data: dict):
    """Remove all test data."""
    print_header("Cleaning Up Test Data")

    try:
        # Delete in reverse order of creation
        print_info("Deleting activity progress...")
        db.delete(test_data['activity'])

        print_info("Deleting reward records...")
        rewards = db.query(UserReward).filter(
            UserReward.registration_id == test_data['registration'].id
        ).all()
        for reward in rewards:
            db.delete(reward)

        print_info("Deleting registration...")
        db.delete(test_data['registration'])

        print_info("Deleting tier...")
        db.delete(test_data['tier'])

        print_info("Deleting event...")
        db.delete(test_data['event'])

        print_info("Deleting user...")
        db.delete(test_data['user'])

        db.commit()
        print_success("All test data cleaned up successfully")

    except Exception as e:
        print_error(f"Cleanup failed: {str(e)}")
        db.rollback()


def verify_database_schema(db: Session) -> bool:
    """Verify that required database columns exist."""
    print_header("Verifying Database Schema")

    try:
        from sqlalchemy import inspect

        inspector = inspect(engine)

        # Check user_rewards table
        print_info("Checking user_rewards table...")
        columns = inspector.get_columns('user_rewards')
        column_names = [col['name'] for col in columns]

        required_columns = [
            'certificate_url',
            'certificate_number',
            'download_count',
            'download_limit',
            'last_downloaded_at'
        ]

        all_present = True
        for col in required_columns:
            if col in column_names:
                print_success(f"Column '{col}' exists")
            else:
                print_error(f"Column '{col}' missing!")
                all_present = False

        if all_present:
            print_success("All required columns present")
            return True
        else:
            print_error("Database migration may not have run correctly")
            print_warning("Run: alembic upgrade head")
            return False

    except Exception as e:
        print_error(f"Schema verification failed: {str(e)}")
        return False


def main():
    """Run all tests."""
    print_header("Certificate System Manual Testing")
    print_info("This script will test the certificate generation system end-to-end")

    cleanup = '--cleanup' in sys.argv

    db = SessionLocal()
    test_data = None

    try:
        # Verify schema first
        if not verify_database_schema(db):
            print_error("Database schema verification failed. Exiting.")
            return

        # Setup test data
        test_data = setup_test_data(db)

        # Run tests
        tests_passed = []
        tests_failed = []

        # Test 1: Certificate Generation
        if test_certificate_generation(db, test_data['registration'].id):
            tests_passed.append("Certificate Generation")
        else:
            tests_failed.append("Certificate Generation")

        # Test 2: Caching
        if test_caching(db, test_data['registration'].id):
            tests_passed.append("Caching")
        else:
            tests_failed.append("Caching")

        # Test 3: Download Tracking
        if test_download_tracking(db, test_data['registration'].id, test_data['user'].id):
            tests_passed.append("Download Tracking")
        else:
            tests_failed.append("Download Tracking")

        # Test 4: Unlimited Downloads
        if test_unlimited_downloads(db, test_data['registration'].id, test_data['user'].id):
            tests_passed.append("Unlimited Downloads")
        else:
            tests_failed.append("Unlimited Downloads")

        # Print summary
        print_header("Test Summary")
        print_info(f"Passed: {len(tests_passed)}/{len(tests_passed) + len(tests_failed)}")

        if tests_passed:
            for test in tests_passed:
                print_success(test)

        if tests_failed:
            print_info("\nFailed tests:")
            for test in tests_failed:
                print_error(test)

        # Cleanup if requested
        if cleanup and test_data:
            cleanup_test_data(db, test_data)
        else:
            print_warning("\nTest data NOT cleaned up. Use --cleanup flag to remove test data")
            print_info(f"Test User ID: {test_data['user'].id}")
            print_info(f"Test Event ID: {test_data['event'].id}")
            print_info(f"Test Registration ID: {test_data['registration'].id}")

    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    main()
