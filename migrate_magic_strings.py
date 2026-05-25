#!/usr/bin/env python3
"""
Magic String Migration Script

This script helps identify and report magic strings that should be replaced
with constants from the app.core.constants module.

Usage:
    python migrate_magic_strings.py --scan       # Scan for magic strings
    python migrate_magic_strings.py --report     # Generate detailed report
    python migrate_magic_strings.py --validate   # Validate migrations
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

# Magic string patterns to find
MAGIC_STRING_PATTERNS = {
    "payment_status": [
        r'["\']pending["\']',
        r'["\']authorized["\']',
        r'["\']completed["\']',
        r'["\']failed["\']',
        r'["\']refunded["\']',
        r'["\']voided["\']',
    ],
    "registration_status": [
        r'["\']confirmed["\']',
        r'["\']payment_completed["\']',
        r'["\']cancelled["\']',
    ],
    "event_status": [
        r'["\']draft["\']',
        r'["\']published["\']',
        r'["\']upcoming["\']',
        r'["\']ongoing["\']',
        r'["\']completed["\']',
    ],
    "http_headers": [
        r'["\']X-Request-ID["\']',
        r'["\']X-Process-Time["\']',
        r'["\']X-RateLimit-Limit["\']',
        r'["\']X-RateLimit-Remaining["\']',
        r'["\']X-RateLimit-Reset["\']',
        r'["\']X-Razorpay-Signature["\']',
        r'["\']Authorization["\']',
        r'["\']Content-Type["\']',
    ],
    "error_messages": [
        r'["\'].*not found["\']',
        r'["\']Invalid.*["\']',
        r'["\'].*already exists["\']',
        r'["\']Not authorized["\']',
        r'["\']Unauthorized["\']',
    ],
    "webhook_events": [
        r'["\']payment\.captured["\']',
        r'["\']payment\.failed["\']',
        r'["\']payment\.authorized["\']',
        r'["\']order\.paid["\']',
        r'["\']refund\.processed["\']',
    ],
    "mime_types": [
        r'["\']image/jpeg["\']',
        r'["\']image/png["\']',
        r'["\']image/webp["\']',
        r'["\']application/json["\']',
        r'["\']application/pdf["\']',
    ],
    "fitness_trackers": [
        r'["\']strava["\']',
        r'["\']google_fit["\']',
        r'["\']apple_health["\']',
        r'["\']nike_run_club["\']',
        r'["\']garmin["\']',
        r'["\']wahoo["\']',
        r'["\']fitbit["\']',
    ],
    "activity_types": [
        r'["\']running["\']',
        r'["\']cycling["\']',
        r'["\']walking["\']',
        r'["\']swimming["\']',
        r'["\']hiking["\']',
    ],
    "shipment_status": [
        r'["\']NEW["\']',
        r'["\']PENDING["\']',
        r'["\']PICKUP_SCHEDULED["\']',
        r'["\']IN_TRANSIT["\']',
        r'["\']DELIVERED["\']',
    ],
}

# Replacement suggestions
REPLACEMENTS = {
    "payment_status": "from app.core.enums import PaymentStatus",
    "registration_status": "from app.core.enums import RegistrationStatus",
    "event_status": "from app.core.enums import EventStatus",
    "http_headers": "from app.core.constants import HTTPHeaders",
    "error_messages": "from app.core.constants import ErrorMessages",
    "webhook_events": "from app.core.constants import RazorpayEvents",
    "mime_types": "from app.core.constants import MimeTypes",
    "fitness_trackers": "from app.core.enums import FitnessTrackerProvider",
    "activity_types": "from app.core.enums import ActivityType",
    "shipment_status": "from app.core.enums import ShipmentStatus",
}

# Files to exclude from scanning
EXCLUDE_PATTERNS = [
    r"\.pyc$",
    r"__pycache__",
    r"\.git",
    r"\.venv",
    r"venv/",
    r"node_modules",
    r"migrations/",
    r"alembic/versions/",
    r"app/core/constants/",
    r"app/core/enums\.py",
    r"migrate_magic_strings\.py",
    r"test_.*\.py",
]


class MagicStringScanner:
    """Scans Python files for magic strings."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.findings: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
        self.file_count = 0
        self.magic_string_count = 0

    def should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded from scanning."""
        path_str = str(file_path)
        return any(re.search(pattern, path_str) for pattern in EXCLUDE_PATTERNS)

    def scan_file(self, file_path: Path) -> None:
        """Scan a single file for magic strings."""
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, start=1):
                # Skip comments and docstrings
                if line.strip().startswith("#") or '"""' in line or "'''" in line:
                    continue

                for category, patterns in MAGIC_STRING_PATTERNS.items():
                    for pattern in patterns:
                        if re.search(pattern, line):
                            self.findings[category].append(
                                (str(file_path.relative_to(self.root_dir)), line_num, line.strip())
                            )
                            self.magic_string_count += 1

            self.file_count += 1

        except Exception as e:
            print(f"Error scanning {file_path}: {e}", file=sys.stderr)

    def scan_directory(self) -> None:
        """Recursively scan directory for Python files."""
        print(f"Scanning {self.root_dir} for magic strings...")

        for file_path in self.root_dir.rglob("*.py"):
            if not self.should_exclude(file_path):
                self.scan_file(file_path)

        print(f"\nScanned {self.file_count} files")
        print(f"Found {self.magic_string_count} potential magic strings\n")

    def generate_report(self, output_file: str = "magic_strings_report.md") -> None:
        """Generate a detailed report of findings."""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Magic Strings Migration Report\n\n")
            f.write(f"**Generated**: {self._get_timestamp()}\n\n")
            f.write(f"**Files Scanned**: {self.file_count}\n")
            f.write(f"**Magic Strings Found**: {self.magic_string_count}\n\n")
            f.write("---\n\n")

            for category, findings in sorted(self.findings.items()):
                if not findings:
                    continue

                f.write(f"## {category.replace('_', ' ').title()}\n\n")
                f.write(f"**Import Required**: `{REPLACEMENTS.get(category, 'N/A')}`\n\n")
                f.write(f"**Occurrences**: {len(findings)}\n\n")

                # Group by file
                by_file = defaultdict(list)
                for file_path, line_num, line in findings:
                    by_file[file_path].append((line_num, line))

                for file_path, lines in sorted(by_file.items()):
                    f.write(f"### {file_path}\n\n")
                    for line_num, line in lines:
                        f.write(f"- Line {line_num}: `{line}`\n")
                    f.write("\n")

                f.write("---\n\n")

        print(f"Report generated: {output_file}")

    def print_summary(self) -> None:
        """Print summary of findings to console."""
        print("=" * 70)
        print("MAGIC STRINGS SUMMARY")
        print("=" * 70)

        for category, findings in sorted(self.findings.items()):
            count = len(findings)
            if count > 0:
                print(f"\n{category.replace('_', ' ').title()}: {count} occurrences")
                print(f"  → {REPLACEMENTS.get(category, 'N/A')}")

        print("\n" + "=" * 70)
        print(f"Total: {self.magic_string_count} magic strings in {self.file_count} files")
        print("=" * 70)

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_migration_guide():
    """Generate a step-by-step migration guide."""
    guide = """
# Magic Strings Migration Guide

## Step-by-Step Migration Process

### 1. Import the Constants/Enums

Add the appropriate import at the top of your file:

```python
# For status values (database models, business logic)
from app.core.enums import (
    PaymentStatus,
    RegistrationStatus,
    EventStatus,
    ActivityType,
    FitnessTrackerProvider,
)

# For infrastructure strings (headers, errors, etc.)
from app.core.constants import (
    HTTPHeaders,
    ErrorMessages,
    RazorpayEvents,
    MimeTypes,
)
```

### 2. Replace Magic Strings

#### Example 1: Payment Status
```python
# Before
if payment.status == "completed":
    send_confirmation()

# After
if payment.status == PaymentStatus.COMPLETED:
    send_confirmation()
```

#### Example 2: HTTP Headers
```python
# Before
request_id = request.headers.get("X-Request-ID")

# After
request_id = request.headers.get(HTTPHeaders.X_REQUEST_ID)
```

#### Example 3: Error Messages
```python
# Before
raise HTTPException(status_code=404, detail="User not found")

# After
raise HTTPException(status_code=404, detail=ErrorMessages.USER_NOT_FOUND)
```

#### Example 4: Webhook Events
```python
# Before
if event_type == "payment.captured":
    process_payment()

# After
if event_type == RazorpayEvents.PAYMENT_CAPTURED:
    process_payment()
```

### 3. Update Model Definitions

```python
# Before
class Payment(Base):
    status: str = Column(String, default="pending")

# After
from app.core.enums import PaymentStatus

class Payment(Base):
    status: str = Column(String, default=PaymentStatus.PENDING)
```

### 4. Update API Endpoints

```python
# Before
@router.post("/api/v1/events")
async def create_event():
    pass

# After
from app.core.constants import APIVersion, APIRoutes, build_route

@router.post(build_route(APIVersion.V1, APIRoutes.EVENTS))
async def create_event():
    pass
```

## Migration Priority

### High Priority (Do First)
1. Status enums in models
2. Payment and registration status checks
3. Error messages in exception handlers
4. Webhook event type comparisons

### Medium Priority
1. HTTP header names
2. MIME type validations
3. API route definitions
4. Database field names in queries

### Low Priority
1. Logging messages
2. Test fixtures
3. Documentation examples

## Testing Your Changes

After migration, ensure:
1. All tests pass
2. Database operations work correctly
3. API responses are unchanged
4. Webhook processing works
5. File upload validations work

## Common Patterns

### Pattern 1: Status Comparison
```python
# Old
if obj.status == "pending" or obj.status == "authorized":

# New
if obj.status in [PaymentStatus.PENDING, PaymentStatus.AUTHORIZED]:
```

### Pattern 2: Default Values
```python
# Old
status: str = "pending"

# New
status: PaymentStatus = PaymentStatus.PENDING
```

### Pattern 3: Dictionary Keys
```python
# Old
headers = {"X-Request-ID": request_id}

# New
headers = {HTTPHeaders.X_REQUEST_ID: request_id}
```

### Pattern 4: Error Messages with Parameters
```python
# Old
raise HTTPException(404, f"{resource_type} not found")

# New
from app.core.constants import ErrorMessages
error_msg = ErrorMessages.format_message(
    ErrorMessages.RESOURCE_NOT_FOUND,
    resource=resource_type
)
raise HTTPException(404, error_msg)
```

## Verification

Run these checks after migration:
```bash
# Check for common magic strings
grep -r '"pending"' app/ --include="*.py"
grep -r '"completed"' app/ --include="*.py"
grep -r '"X-Request-ID"' app/ --include="*.py"

# Run tests
pytest

# Check for import errors
python -m py_compile app/**/*.py
```
"""

    with open("MIGRATION_GUIDE.md", "w") as f:
        f.write(guide)

    print("Migration guide created: MIGRATION_GUIDE.md")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python migrate_magic_strings.py [--scan|--report|--validate|--guide]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "--guide":
        generate_migration_guide()
        return

    scanner = MagicStringScanner("app")
    scanner.scan_directory()

    if command == "--scan":
        scanner.print_summary()
    elif command == "--report":
        scanner.generate_report()
        scanner.print_summary()
    elif command == "--validate":
        scanner.generate_report("validation_report.md")
        if scanner.magic_string_count == 0:
            print("\n✅ No magic strings found! Migration complete.")
            sys.exit(0)
        else:
            print(f"\n⚠️  Found {scanner.magic_string_count} magic strings still to migrate")
            sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
