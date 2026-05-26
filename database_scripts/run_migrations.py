#!/usr/bin/env python3
"""
Database Migration Runner
Executes SQL migration scripts in order
"""

import re
import sys
from datetime import datetime
from pathlib import Path

import psycopg2

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


class MigrationRunner:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent

    def get_connection(self):
        """Create a database connection"""
        return psycopg2.connect(self.database_url)

    def create_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id SERIAL PRIMARY KEY,
                        migration_file VARCHAR(255) UNIQUE NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        checksum VARCHAR(64),
                        execution_time_ms INTEGER
                    )
                """)
                conn.commit()
                print("✅ Migrations tracking table ready")
        except Exception as e:
            conn.rollback()
            print(f"❌ Error creating migrations table: {e}")
            raise
        finally:
            conn.close()

    def get_applied_migrations(self):
        """Get list of already applied migrations"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT migration_file FROM schema_migrations ORDER BY id")
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_migration_files(self):
        """Get all SQL migration files in order"""
        files = []
        for file in self.migrations_dir.glob("*.sql"):
            # Only include files that start with numbers (migration pattern)
            if re.match(r"^\d+_", file.name):
                files.append(file)
        return sorted(files, key=lambda x: x.name)

    def calculate_checksum(self, content: str) -> str:
        """Calculate checksum for migration content"""
        import hashlib

        return hashlib.sha256(content.encode()).hexdigest()

    def run_migration(self, migration_file: Path):
        """Run a single migration file"""
        print(f"\n📝 Running migration: {migration_file.name}")

        # Read migration content
        with open(migration_file) as f:
            content = f.read()

        checksum = self.calculate_checksum(content)

        conn = self.get_connection()
        start_time = datetime.now()

        try:
            with conn.cursor() as cur:
                # Execute migration
                cur.execute(content)

                # Record migration
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                cur.execute(
                    """
                    INSERT INTO schema_migrations (migration_file, checksum, execution_time_ms)
                    VALUES (%s, %s, %s)
                    """,
                    (migration_file.name, checksum, execution_time),
                )

                conn.commit()
                print(f"✅ Migration completed in {execution_time}ms")

        except Exception as e:
            conn.rollback()
            print(f"❌ Migration failed: {e}")
            raise
        finally:
            conn.close()

    def run_all_migrations(self):
        """Run all pending migrations"""
        print("=" * 60)
        print("🚀 Starting Database Migrations")
        print("=" * 60)
        print(
            f"Database: {self.database_url.split('@')[1] if '@' in self.database_url else 'local'}"
        )
        print()

        # Ensure migrations table exists
        self.create_migrations_table()

        # Get applied and pending migrations
        applied = set(self.get_applied_migrations())
        all_migrations = self.get_migration_files()

        pending = [m for m in all_migrations if m.name not in applied]

        print("📊 Migration Status:")
        print(f"   - Total migrations: {len(all_migrations)}")
        print(f"   - Already applied: {len(applied)}")
        print(f"   - Pending: {len(pending)}")
        print()

        if not pending:
            print("✅ No pending migrations. Database is up to date!")
            return

        # Run pending migrations
        for migration in pending:
            self.run_migration(migration)

        print()
        print("=" * 60)
        print("✅ All migrations completed successfully!")
        print("=" * 60)

    def show_status(self):
        """Show migration status"""
        print("=" * 60)
        print("📊 Database Migration Status")
        print("=" * 60)

        self.create_migrations_table()

        applied = self.get_applied_migrations()
        all_migrations = self.get_migration_files()

        print(f"\n✅ Applied Migrations ({len(applied)}):")
        for migration in applied:
            print(f"   - {migration}")

        pending = [m.name for m in all_migrations if m.name not in applied]
        print(f"\n⏳ Pending Migrations ({len(pending)}):")
        if pending:
            for migration in pending:
                print(f"   - {migration}")
        else:
            print("   (none)")

        print()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Database Migration Runner")
    parser.add_argument(
        "command",
        choices=["migrate", "status"],
        help="Command to run: migrate (run all pending migrations) or status (show migration status)",
    )
    parser.add_argument(
        "--database-url", help="Database URL (overrides environment variable)", default=None
    )

    args = parser.parse_args()

    # Get database URL
    database_url = args.database_url or settings.DATABASE_URL

    if not database_url or database_url == "postgresql://user:password@localhost:5432/dbname":
        print("❌ Error: DATABASE_URL not set or using default value")
        print("   Set DATABASE_URL environment variable or use --database-url flag")
        sys.exit(1)

    # Create runner and execute command
    runner = MigrationRunner(database_url)

    try:
        if args.command == "migrate":
            runner.run_all_migrations()
        elif args.command == "status":
            runner.show_status()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
