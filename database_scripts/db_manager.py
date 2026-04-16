#!/usr/bin/env python3
"""
Database Management Utilities
Provides commands for database backup, restore, reset, and seeding
"""
import os
import sys
import psycopg2
from psycopg2 import sql
from pathlib import Path
from datetime import datetime
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.scripts_dir = Path(__file__).parent

    def get_connection(self):
        """Create a database connection"""
        return psycopg2.connect(self.database_url)

    def reset_database(self, confirm: bool = False):
        """Drop all tables and reset database"""
        if not confirm:
            print("⚠️  WARNING: This will delete ALL data in the database!")
            response = input("Type 'yes' to confirm: ")
            if response.lower() != 'yes':
                print("❌ Database reset cancelled")
                return

        print("\n🔄 Resetting database...")

        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Drop all tables
                cur.execute("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public')
                        LOOP
                            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                        END LOOP;
                    END $$;
                """)

                # Drop all types
                cur.execute("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT typname FROM pg_type WHERE typnamespace = 'public'::regnamespace AND typtype = 'e')
                        LOOP
                            EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
                        END LOOP;
                    END $$;
                """)

                # Drop all functions
                cur.execute("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT proname, oidvectortypes(proargtypes) as argtypes
                                  FROM pg_proc INNER JOIN pg_namespace ns ON (pg_proc.pronamespace = ns.oid)
                                  WHERE ns.nspname = 'public')
                        LOOP
                            EXECUTE 'DROP FUNCTION IF EXISTS ' || quote_ident(r.proname) || '(' || r.argtypes || ') CASCADE';
                        END LOOP;
                    END $$;
                """)

                conn.commit()
                print("✅ Database reset complete")

        except Exception as e:
            conn.rollback()
            print(f"❌ Error resetting database: {e}")
            raise
        finally:
            conn.close()

    def seed_test_data(self):
        """Insert test/sample data"""
        print("\n🌱 Seeding test data...")

        seed_file = self.scripts_dir / "seed_data.sql"
        if not seed_file.exists():
            print("⚠️  No seed_data.sql file found. Creating basic test data...")
            self._create_basic_test_data()
        else:
            with open(seed_file, 'r') as f:
                content = f.read()

            conn = self.get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(content)
                    conn.commit()
                    print("✅ Test data seeded successfully")
            except Exception as e:
                conn.rollback()
                print(f"❌ Error seeding data: {e}")
                raise
            finally:
                conn.close()

    def _create_basic_test_data(self):
        """Create basic test data if seed file doesn't exist"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Insert test admin user
                cur.execute("""
                    INSERT INTO users (email, password_hash, first_name, last_name, role, email_verified)
                    VALUES ('admin@glycogrit.com', '$2b$12$KIXxkqLQvhBqWkZvQ2zJKuFTzQxQN4p0YrQvZJQzQxQN4p0YrQvZJ', 'Admin', 'User', 'admin', TRUE)
                    ON CONFLICT (email) DO NOTHING;
                """)

                # Insert test regular user
                cur.execute("""
                    INSERT INTO users (email, password_hash, first_name, last_name, role, email_verified)
                    VALUES ('test@example.com', '$2b$12$KIXxkqLQvhBqWkZvQ2zJKuFTzQxQN4p0YrQvZJQzQxQN4p0YrQvZJ', 'Test', 'User', 'participant', TRUE)
                    ON CONFLICT (email) DO NOTHING;
                """)

                conn.commit()
                print("✅ Basic test data created")
        except Exception as e:
            conn.rollback()
            print(f"❌ Error creating test data: {e}")
            raise
        finally:
            conn.close()

    def show_tables(self):
        """Show all tables in database"""
        print("\n📋 Database Tables:")
        print("=" * 60)

        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        schemaname,
                        tablename,
                        tableowner
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY tablename;
                """)

                tables = cur.fetchall()
                if tables:
                    for schema, table, owner in tables:
                        # Get row count
                        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
                        count = cur.fetchone()[0]
                        print(f"   {table:30} ({count:6} rows)")
                else:
                    print("   (no tables found)")

        finally:
            conn.close()

        print()

    def show_stats(self):
        """Show database statistics"""
        print("\n📊 Database Statistics:")
        print("=" * 60)

        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Database size
                cur.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size;
                """)
                db_size = cur.fetchone()[0]
                print(f"   Database Size: {db_size}")

                # Table count
                cur.execute("""
                    SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';
                """)
                table_count = cur.fetchone()[0]
                print(f"   Tables: {table_count}")

                # Total rows across all tables
                cur.execute("""
                    SELECT
                        SUM(n_live_tup)
                    FROM pg_stat_user_tables;
                """)
                total_rows = cur.fetchone()[0] or 0
                print(f"   Total Rows: {total_rows}")

                # Indexes
                cur.execute("""
                    SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';
                """)
                index_count = cur.fetchone()[0]
                print(f"   Indexes: {index_count}")

        finally:
            conn.close()

        print()

    def backup_database(self, output_file: str = None):
        """Create database backup"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"backup_{timestamp}.sql"

        print(f"\n💾 Creating backup: {output_file}")

        try:
            # Use pg_dump for backup
            from urllib.parse import urlparse
            parsed = urlparse(self.database_url)

            env = os.environ.copy()
            env['PGPASSWORD'] = parsed.password

            cmd = [
                'pg_dump',
                '-h', parsed.hostname,
                '-p', str(parsed.port or 5432),
                '-U', parsed.username,
                '-d', parsed.path.lstrip('/'),
                '-F', 'p',  # Plain text format
                '-f', output_file
            ]

            subprocess.run(cmd, env=env, check=True)
            print(f"✅ Backup created successfully: {output_file}")

        except subprocess.CalledProcessError as e:
            print(f"❌ Backup failed: {e}")
            raise
        except Exception as e:
            print(f"❌ Error: {e}")
            raise


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Database Management Utilities')
    parser.add_argument(
        'command',
        choices=['reset', 'seed', 'tables', 'stats', 'backup'],
        help='Command to run'
    )
    parser.add_argument(
        '--database-url',
        help='Database URL (overrides environment variable)',
        default=None
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompts'
    )
    parser.add_argument(
        '--output',
        help='Output file for backup',
        default=None
    )

    args = parser.parse_args()

    # Get database URL
    database_url = args.database_url or settings.DATABASE_URL

    if not database_url or database_url == "postgresql://user:password@localhost:5432/dbname":
        print("❌ Error: DATABASE_URL not set or using default value")
        print("   Set DATABASE_URL environment variable or use --database-url flag")
        sys.exit(1)

    # Create manager and execute command
    manager = DatabaseManager(database_url)

    try:
        if args.command == 'reset':
            manager.reset_database(confirm=args.yes)
        elif args.command == 'seed':
            manager.seed_test_data()
        elif args.command == 'tables':
            manager.show_tables()
        elif args.command == 'stats':
            manager.show_stats()
        elif args.command == 'backup':
            manager.backup_database(args.output)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
