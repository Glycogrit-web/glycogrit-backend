# Database Setup Guide

## Overview

The GlycoGrit backend now has a complete database schema and migration system ready to deploy on Railway.

## What Was Created

### 1. Database Schema (`database_scripts/001_initial_schema.sql`)

Complete PostgreSQL schema with:
- **18 tables** covering all platform features
- **Custom ENUM types** for status fields
- **Indexes** for performance optimization
- **Triggers** for automatic timestamp updates
- **Functions** for business logic (registration numbers, BIB numbers)
- **Views** for common queries

### 2. Migration System (`database_scripts/run_migrations.py`)

Python-based migration runner that:
- Tracks applied migrations in `schema_migrations` table
- Executes SQL files in order (001_, 002_, etc.)
- Calculates checksums to detect changes
- Provides migration status reporting
- Supports rollback tracking

### 3. Database Management Tools (`database_scripts/db_manager.py`)

Utility script for:
- Resetting database (drop all tables)
- Seeding test data
- Viewing tables and statistics
- Creating backups
- Database maintenance

### 4. Test Data (`database_scripts/seed_data.sql`)

Sample data including:
- Admin user (admin@glycogrit.com / admin123)
- Organizer user (organizer@glycogrit.com / organizer123)
- 4 test participants
- 3 sample events (marathon, 10K, cycling)
- Event categories and registrations
- Virtual challenges

### 5. API Endpoints for Setup

Temporary admin endpoints in `app/main.py`:
- `POST /api/v1/admin/run-migrations` - Run database migrations
- `POST /api/v1/admin/seed-data` - Insert test data
- `GET /api/v1/admin/db-tables` - List all tables

**⚠️ Important**: Remove these endpoints after initial setup for security!

## Quick Start on Railway

### Step 1: Deploy Code

```bash
# Commit and push changes
git add .
git commit -m "Add database schema and migration system"
git push origin master
```

Railway will automatically redeploy your app.

### Step 2: Run Migrations

Once deployed, use the temporary API endpoints:

```bash
# Replace with your Railway app URL
RAILWAY_URL="https://your-app.railway.app"

# Run migrations
curl -X POST "$RAILWAY_URL/api/v1/admin/run-migrations"

# Check tables were created
curl "$RAILWAY_URL/api/v1/admin/db-tables"

# Seed test data (optional)
curl -X POST "$RAILWAY_URL/api/v1/admin/seed-data"
```

Or visit these URLs in your browser:
- Run migrations: `https://your-app.railway.app/api/v1/admin/run-migrations` (POST)
- View tables: `https://your-app.railway.app/api/v1/admin/db-tables`
- Seed data: `https://your-app.railway.app/api/v1/admin/seed-data` (POST)

### Step 3: Verify Setup

Visit the Swagger docs: `https://your-app.railway.app/docs`

Test endpoints:
- `GET /health` - Should return healthy status
- `GET /api/v1/db-test` - Should connect successfully
- `GET /api/v1/admin/db-tables` - Should show all 18+ tables

### Step 4: Remove Admin Endpoints

After successful setup, remove the temporary admin endpoints from [app/main.py](app/main.py):
- Delete the `run_migrations_endpoint()` function
- Delete the `seed_data_endpoint()` function
- Delete the `list_tables_endpoint()` function

Redeploy to Railway.

## Database Schema Summary

### Core Tables

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `users` | User accounts | email, role, profile info |
| `events` | Running/cycling events | name, date, location, organizer |
| `event_categories` | Distance categories | name, distance, capacity |
| `registrations` | Event registrations | user, event, bib_number, status |
| `payments` | Payment transactions | amount, status, transaction_id |
| `event_results` | Race results | timings, rankings, splits |
| `certificates` | Digital certificates | certificate_url, verification_code |

### Additional Tables

- `event_checkpoints` - Route timing points
- `checkpoint_timings` - Participant timing data
- `leaderboards` - Cached leaderboard data
- `event_sponsors` - Sponsor information
- `event_photos` - Event photography
- `virtual_challenges` - Virtual running challenges
- `challenge_participations` - Challenge tracking
- `user_achievements` - Gamification badges

## Next Steps

After database setup is complete:

### 1. Build Authentication System
- JWT token generation
- User registration endpoint
- Login endpoint
- Password reset flow

### 2. Event Management API
- Create/update/delete events
- Event listing with filters
- Event details endpoint
- Event search functionality

### 3. Registration System
- Event registration endpoint
- Registration status management
- BIB number generation
- Registration confirmation emails

### 4. Payment Integration
- Payment gateway integration (Razorpay/Stripe)
- Payment webhook handling
- Refund processing
- Payment status tracking

### 5. Results Management
- Result upload system
- Leaderboard generation
- Certificate generation
- Result verification

## Documentation

- [Database Scripts README](database_scripts/README.md) - Detailed migration system docs
- [Railway Deployment Guide](database_scripts/deploy_to_railway.md) - Railway-specific instructions
- [API Documentation](https://your-app.railway.app/docs) - Swagger UI (after deployment)

## Troubleshooting

### Migration Fails

1. Check Railway logs: `railway logs`
2. Verify DATABASE_URL is set correctly
3. Check database connection: `GET /api/v1/db-test`
4. Review migration file for SQL errors

### Tables Not Created

1. Verify migration ran successfully
2. Check `GET /api/v1/admin/db-tables` endpoint
3. Connect to database directly via Railway dashboard
4. Run `SELECT * FROM schema_migrations;` to see applied migrations

### Connection Issues

1. Verify using private networking URL (`postgres.railway.internal`)
2. Check that DATABASE_URL reference variable is set correctly
3. Test connection with `/api/v1/db-test` endpoint

## Security Notes

1. ⚠️ **Remove admin endpoints** after initial setup
2. ⚠️ **Change default passwords** in seed data for production
3. ⚠️ **Use environment variables** for sensitive data
4. ⚠️ **Implement authentication** before exposing endpoints
5. ⚠️ **Add rate limiting** to prevent abuse

## Support

For issues or questions:
- Review Railway logs
- Check database connection in Railway dashboard
- Verify environment variables are set
- Review the [database scripts README](database_scripts/README.md)
