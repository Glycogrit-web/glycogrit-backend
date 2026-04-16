# Database Setup - Quick Guide

## What We Have

### Database Schema
- **File**: `database_scripts/001_initial_schema.sql`
- **18+ tables**: users, events, registrations, payments, results, certificates, etc.
- Complete with indexes, triggers, and sample functions

### Migration System
- **run_migrations.py**: Execute SQL migrations in order
- **db_manager.py**: Database utilities (reset, seed, backup, stats)

### Monitoring
- **database_monitor.py**: Health checks, pool stats, table sizes

### Admin Endpoints (Temporary)
- `POST /api/v1/admin/run-migrations` - Run migrations
- `POST /api/v1/admin/seed-data` - Insert test data
- `GET /api/v1/admin/db-tables` - List tables

## Deploy to Railway

### 1. Push Changes
```bash
git push origin master
# Railway will auto-deploy
```

### 2. Run Migrations
Once deployed, visit in your browser or use curl:
```
https://your-app.railway.app/api/v1/admin/run-migrations
```

### 3. Verify Setup
```
https://your-app.railway.app/api/v1/admin/db-tables
```

### 4. (Optional) Seed Test Data
```
https://your-app.railway.app/api/v1/admin/seed-data
```

This will create:
- Admin user: admin@glycogrit.com / admin123
- Organizer: organizer@glycogrit.com / organizer123
- 4 test participants
- 3 sample events

### 5. Clean Up
After setup, remove the admin endpoints from `app/main.py`:
- Delete `run_migrations_endpoint()`
- Delete `seed_data_endpoint()`
- Delete `list_tables_endpoint()`

Redeploy to Railway.

## Database Schema Overview

**Core Tables**:
- `users` - User accounts with authentication
- `events` - Running/cycling events
- `event_categories` - Distance categories (5K, 10K, Marathon, etc.)
- `registrations` - Event registrations with BIB numbers
- `payments` - Payment transactions
- `event_results` - Race timings and rankings
- `certificates` - Digital certificates

**Supporting Tables**:
- `event_checkpoints` - Route timing points
- `checkpoint_timings` - Participant timing data
- `leaderboards` - Cached rankings
- `event_sponsors`, `event_photos` - Event details
- `virtual_challenges`, `challenge_participations` - Virtual events
- `user_achievements` - Gamification

## Local Development

```bash
# Check migration status
python database_scripts/run_migrations.py status

# Run migrations
python database_scripts/run_migrations.py migrate

# Seed data
python database_scripts/db_manager.py seed

# View tables
python database_scripts/db_manager.py tables

# Database stats
python database_scripts/db_manager.py stats

# Reset (⚠️ destroys all data)
python database_scripts/db_manager.py reset
```

## Next Steps

1. ✅ Database schema created
2. ✅ Migration system ready
3. ✅ Basic monitoring in place
4. 🎯 Build authentication endpoints
5. 🎯 Create event management API
6. 🎯 Implement registration system

## Advanced Patterns

For advanced database patterns (async operations, caching, optimization), see:
`.claude/skills/database-patterns.md`

These patterns are for **future implementation** when scaling is needed.
