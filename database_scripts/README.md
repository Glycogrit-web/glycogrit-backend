# Database Management Scripts

This directory contains all database migration scripts, utilities, and seed data for the GlycoGrit platform.

## Directory Structure

```
database_scripts/
├── README.md                    # This file
├── run_migrations.py            # Migration runner
├── db_manager.py                # Database management utilities
├── 001_initial_schema.sql       # Initial database schema
└── seed_data.sql                # Sample/test data
```

## Quick Start

### 1. Run Migrations (Setup Database Schema)

```bash
# From project root
python database_scripts/run_migrations.py migrate

# Or from database_scripts directory
cd database_scripts
python run_migrations.py migrate
```

### 2. Seed Test Data

```bash
python database_scripts/db_manager.py seed
```

### 3. Check Database Status

```bash
# View migration status
python database_scripts/run_migrations.py status

# View all tables
python database_scripts/db_manager.py tables

# View database statistics
python database_scripts/db_manager.py stats
```

## Migration System

### How It Works

The migration system tracks which SQL files have been applied to your database using a `schema_migrations` table. Each migration file is:
- Named with a numeric prefix (e.g., `001_initial_schema.sql`, `002_add_feature.sql`)
- Executed only once
- Tracked with a checksum to ensure integrity

### Running Migrations

```bash
# Apply all pending migrations
python database_scripts/run_migrations.py migrate

# Check migration status
python database_scripts/run_migrations.py status

# Use custom database URL
python database_scripts/run_migrations.py migrate --database-url "postgresql://user:pass@host:5432/dbname"
```

### Creating New Migrations

1. Create a new SQL file with a numeric prefix:
   ```bash
   # Example: 002_add_user_preferences.sql
   touch database_scripts/002_add_user_preferences.sql
   ```

2. Add your SQL commands:
   ```sql
   -- Add user preferences table
   CREATE TABLE user_preferences (
       id SERIAL PRIMARY KEY,
       user_id INTEGER NOT NULL REFERENCES users(id),
       theme VARCHAR(50) DEFAULT 'light',
       notifications_enabled BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

3. Run migrations:
   ```bash
   python database_scripts/run_migrations.py migrate
   ```

## Database Management

### Available Commands

#### Reset Database (⚠️ DESTRUCTIVE)
Drops all tables, types, and functions. Use with caution!

```bash
# Interactive prompt
python database_scripts/db_manager.py reset

# Skip confirmation (dangerous!)
python database_scripts/db_manager.py reset --yes
```

#### Seed Test Data
Insert sample data for development and testing:

```bash
python database_scripts/db_manager.py seed
```

#### View Tables
List all tables with row counts:

```bash
python database_scripts/db_manager.py tables
```

#### View Statistics
Show database size, table count, and other stats:

```bash
python database_scripts/db_manager.py stats
```

#### Backup Database
Create a SQL backup file:

```bash
# Auto-generated filename
python database_scripts/db_manager.py backup

# Custom filename
python database_scripts/db_manager.py backup --output my_backup.sql
```

## Database Schema Overview

### Core Tables

- **users** - User accounts (participants, organizers, admins)
- **events** - Running/cycling events and races
- **event_categories** - Distance categories within events (5K, 10K, Marathon, etc.)
- **registrations** - Event registrations and participant details
- **payments** - Payment transactions and refunds
- **event_results** - Race results, timings, and rankings
- **certificates** - Digital certificates for participants

### Supporting Tables

- **event_checkpoints** - Route checkpoints for timing
- **checkpoint_timings** - Participant timing at each checkpoint
- **leaderboards** - Cached leaderboard data
- **event_sponsors** - Event sponsor information
- **event_photos** - Event photography
- **virtual_challenges** - Virtual running/cycling challenges
- **challenge_participations** - User participation in challenges
- **user_achievements** - Gamification badges and achievements

### Enums

- `user_role` - admin, organizer, participant, volunteer
- `event_type` - running, cycling, triathlon, marathon, etc.
- `event_status` - draft, published, registration_open, completed, etc.
- `registration_status` - pending, confirmed, payment_completed, etc.
- `payment_status` - pending, completed, failed, refunded
- `result_status` - not_started, in_progress, finished, dnf, dns

## Railway Deployment

### Running Migrations on Railway

1. **Option 1: Via Railway CLI**
   ```bash
   railway run python database_scripts/run_migrations.py migrate
   ```

2. **Option 2: One-time Deploy Job**
   Create a one-time service in Railway:
   - Command: `python database_scripts/run_migrations.py migrate`
   - Run once during deployment

3. **Option 3: Add to Startup**
   Add to your application startup in [main.py](../app/main.py):
   ```python
   @app.on_event("startup")
   async def run_migrations():
       from database_scripts.run_migrations import MigrationRunner
       runner = MigrationRunner(settings.DATABASE_URL)
       runner.run_all_migrations()
   ```

### Seeding Data on Railway

```bash
# Via Railway CLI
railway run python database_scripts/db_manager.py seed

# Or set environment variable
railway run python database_scripts/db_manager.py seed --database-url $DATABASE_URL
```

## Best Practices

### Migrations

1. ✅ **Always test migrations locally first**
2. ✅ **Make migrations atomic** - each file should be a complete unit
3. ✅ **Never modify existing migration files** - create new ones instead
4. ✅ **Include rollback instructions** in comments if needed
5. ✅ **Use transactions** - migrations run in a transaction automatically

### Schema Design

1. ✅ **Use indexes** on foreign keys and frequently queried columns
2. ✅ **Add timestamps** (created_at, updated_at) to most tables
3. ✅ **Use ENUM types** for fixed sets of values
4. ✅ **Add constraints** to maintain data integrity
5. ✅ **Use CASCADE** carefully on foreign keys

### Development Workflow

1. **Make schema changes**
   ```bash
   # Create new migration file
   touch database_scripts/002_add_feature.sql
   ```

2. **Test locally**
   ```bash
   # Reset and rebuild
   python database_scripts/db_manager.py reset --yes
   python database_scripts/run_migrations.py migrate
   python database_scripts/db_manager.py seed
   ```

3. **Verify changes**
   ```bash
   python database_scripts/db_manager.py tables
   python database_scripts/db_manager.py stats
   ```

4. **Deploy to Railway**
   ```bash
   git add database_scripts/
   git commit -m "Add new migration"
   git push
   railway run python database_scripts/run_migrations.py migrate
   ```

## Troubleshooting

### Migration Already Applied

If a migration shows as applied but you need to rerun it:

```sql
-- Connect to database and remove the migration record
DELETE FROM schema_migrations WHERE migration_file = '001_initial_schema.sql';
```

### Database Connection Issues

1. Verify `DATABASE_URL` is set:
   ```bash
   echo $DATABASE_URL
   ```

2. Test connection manually:
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```

3. Check Railway logs for connection errors

### Reset Everything

```bash
# Nuclear option - destroys all data
python database_scripts/db_manager.py reset --yes
python database_scripts/run_migrations.py migrate
python database_scripts/db_manager.py seed
```

## Environment Variables

The scripts use these environment variables:

- `DATABASE_URL` - PostgreSQL connection string (required)
  - Format: `postgresql://user:password@host:port/database`
  - Railway provides this automatically

## Sample Data

The `seed_data.sql` file includes:

- 1 admin user (admin@glycogrit.com / admin123)
- 1 organizer user (organizer@glycogrit.com / organizer123)
- 4 test participants (all with password: test123)
- 3 sample events (marathon, 10K run, cycling)
- Event categories and sample registrations
- 3 virtual challenges

**Note**: Passwords are bcrypt hashed. Use the credentials above for testing.

## Support

For issues or questions:
- Check Railway logs: `railway logs`
- Review database connections in Railway dashboard
- Verify environment variables are set correctly
