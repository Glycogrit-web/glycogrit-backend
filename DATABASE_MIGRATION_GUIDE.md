# Database Migration Guide

**Status**: Ready to generate migrations for DDD modules
**Date**: 2026-05-21

---

## Overview

The backend has been migrated to DDD architecture. All new module models have been imported into Alembic's `env.py` for automatic migration detection.

---

## New Models Added to Alembic

The following DDD module models are now tracked:

### User Management
- `User` (DDD version)

### Activities
- `UserActivityLog` (DDD version)
- `ActivityProgress` (DDD version)

### Registrations
- `Registration` (DDD version)
- `EventRegistrationTier`
- `RegistrationTier`

### Events
- `Event` (DDD version)
- `EventActivity` (DDD version)

### Payments
- `Payment` (DDD version)
- `PaymentLink`
- `Settlement`
- `PaymentSettlement`
- `WebhookEvent` (payments)

### Fitness Trackers
- `FitnessConnection` (replaces separate Strava, Garmin, etc. tables)

### Certificates & Rewards
- `UserReward` (unified model for certificates and physical rewards)

### Gallery
- `GalleryPhoto`

### Webhooks
- `WebhookEvent` (unified webhook tracking)

### Shipping
- `ShiprocketOrder`

---

## Generating Migrations

### Step 1: Check Current State

```bash
cd glycogrit-backend

# See current migration version
alembic current

# Check pending changes
alembic check
```

### Step 2: Generate Migration

```bash
# Auto-generate migration based on model changes
alembic revision --autogenerate -m "Add DDD module models"

# This will create a file like:
# alembic/versions/xxxx_add_ddd_module_models.py
```

### Step 3: Review Migration

```bash
# Open the generated migration file
cat alembic/versions/xxxx_add_ddd_module_models.py
```

**Important**: Review the migration to ensure:
- ✅ No duplicate table creations (if old models exist)
- ✅ Proper foreign keys
- ✅ Correct column types
- ✅ No data loss operations

### Step 4: Apply Migration

```bash
# Apply to database
alembic upgrade head

# Verify
alembic current
```

---

## Expected Changes

### New Tables

If these tables don't exist yet:
- `fitness_connections` - Unified fitness tracker connections
- `user_rewards` - Certificates and physical rewards
- `gallery_photos` - Photo gallery
- `webhook_events` - Webhook tracking
- `event_registration_tiers` - Event pricing tiers
- `registration_tiers` - User tier selections
- `payment_links` - Payment link generation
- `settlements` - Payment settlements
- `payment_settlements` - Settlement tracking

### Modified Tables

Some tables may need updates:
- `payments` - Additional fields for new payment features
- `registrations` - Multi-tier support fields
- `events` - Additional event lifecycle fields

### Deprecated Tables

These tables may be replaced:
- `strava_connections` → `fitness_connections` (provider='strava')
- `garmin_connections` → `fitness_connections` (provider='garmin')
- `fitbit_connections` → `fitness_connections` (provider='fitbit')

---

## Migration Strategy

### Option 1: Fresh Database (Recommended for Development)

If you can recreate the database:

```bash
# Drop all tables
alembic downgrade base

# Recreate from scratch
alembic upgrade head
```

### Option 2: Incremental Migration (Production)

If you have existing data:

1. **Backup First**:
   ```bash
   pg_dump glycogrit > backup_$(date +%Y%m%d).sql
   ```

2. **Generate Migration**:
   ```bash
   alembic revision --autogenerate -m "Add DDD modules"
   ```

3. **Review Carefully**:
   - Check for data migration needs
   - Ensure no data loss
   - Test on staging first

4. **Create Data Migration** (if needed):
   ```python
   # In migration file
   def upgrade():
       # Create new tables
       op.create_table('fitness_connections', ...)

       # Migrate old data
       op.execute("""
           INSERT INTO fitness_connections
           (user_id, provider, athlete_id, access_token, ...)
           SELECT user_id, 'strava', athlete_id, access_token, ...
           FROM strava_connections
       """)

       # Drop old tables (optional, can keep for rollback)
       # op.drop_table('strava_connections')
   ```

5. **Test on Staging**:
   ```bash
   # On staging
   alembic upgrade head

   # Verify data
   psql glycogrit -c "SELECT COUNT(*) FROM fitness_connections"
   ```

6. **Apply to Production**:
   ```bash
   # On production
   alembic upgrade head
   ```

---

## Rollback Plan

If migration fails:

```bash
# Rollback last migration
alembic downgrade -1

# Or restore from backup
psql glycogrit < backup_YYYYMMDD.sql
```

---

## Common Issues

### Issue: Duplicate table error
```
Table 'xyz' already exists
```

**Solution**:
- Check if old and new models share same table name
- May need to manually edit migration to skip creation
- Or rename old table first

### Issue: Foreign key constraint error
```
Foreign key constraint fails
```

**Solution**:
- Ensure parent tables are created first
- Check migration order in `upgrade()` function
- May need to create tables in specific order

### Issue: Column type mismatch
```
Cannot alter column type
```

**Solution**:
- May need explicit type casting in migration
- Example: `ALTER COLUMN status TYPE varchar USING status::varchar`

---

## Verification Checklist

After migration, verify:

- [ ] All tables exist: `\dt` in psql
- [ ] Foreign keys correct: `\d table_name` in psql
- [ ] Indexes created: `\di` in psql
- [ ] Data migrated (if applicable): Run count queries
- [ ] App starts successfully: `uvicorn app.main:app`
- [ ] Endpoints work: Test with `/docs`

---

## Notes

1. **Old Models**: The old models in `app/models/` still exist for backward compatibility. They point to the same tables as DDD models.

2. **Table Naming**: DDD models may use same table names as old models (e.g., both use `users` table).

3. **Data Migration**: If tables already exist with data, no migration needed - just ensure schema matches.

4. **Testing**: Always test migrations on development/staging before production.

---

## Next Steps

1. Review current database schema
2. Generate migration with `alembic revision --autogenerate`
3. Review generated migration file
4. Test on development database
5. Apply to staging
6. Monitor for issues
7. Apply to production

---

**Status**: Ready to generate migrations
**Updated**: 2026-05-21
**Alembic Config**: [alembic/env.py](alembic/env.py:1) - All DDD models imported
