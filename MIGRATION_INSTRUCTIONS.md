# Database Migration Instructions

**Date:** 2026-05-26
**Migration:** Rename `fitness_connections` → `fitness_tracker_connections`
**Status:** Ready to apply to production

---

## Problem

Production database has a table name mismatch:
- **Production DB:** `fitness_connections` (old name)
- **Code expects:** `fitness_tracker_connections` (current model definition)

This causes errors like:
```
sqlalchemy.exc.ProgrammingError: relation "fitness_connections" does not exist
```

---

## Solution

Created Alembic migration to rename the table safely with:
- ✅ Check if table exists before renaming
- ✅ Rollback capability
- ✅ Safe for production (no data loss)

---

## Migration Files Created

1. **`20260526_0350_64cec31dd3a1_merge_migration_heads.py`**
   - Merges two divergent migration heads
   - Must be applied first

2. **`20260526_0350_bb7b4d03c40d_rename_fitness_connections_to_fitness_.py`**
   - Renames the table
   - Includes safety checks
   - Reversible with downgrade

---

## Pre-Migration Checklist

Before applying to production:

- [ ] Verify database connection string is correct
- [ ] Backup production database
- [ ] Check current Alembic migration state
- [ ] Ensure no active connections to the table
- [ ] Have rollback plan ready

---

## Step 1: Backup Production Database

```bash
# Set connection string
export DATABASE_URL="postgresql://postgres:AXAVbrPvtStBmpObpiyoQufpkPtAvmeI@nozomi.proxy.rlwy.net:29493/railway"

# Create backup
pg_dump $DATABASE_URL > backup_before_rename_$(date +%Y%m%d_%H%M%S).sql

# Verify backup was created
ls -lh backup_before_rename_*.sql
```

---

## Step 2: Check Current Migration State

```bash
cd glycogrit-backend

# Check current revision
alembic current

# Check pending migrations
alembic history | head -20
```

---

## Step 3: Apply Migrations to Production

```bash
cd glycogrit-backend

# Apply merge migration first
alembic upgrade 64cec31dd3a1

# Then apply table rename
alembic upgrade bb7b4d03c40d

# Or apply both at once
alembic upgrade head
```

Expected output:
```
✅ Renamed fitness_connections -> fitness_tracker_connections
```

---

## Step 4: Verify Migration Success

```bash
# Check if table was renamed
psql $DATABASE_URL -c "\dt fitness*"

# Should show: fitness_tracker_connections
# Should NOT show: fitness_connections

# Check table structure
psql $DATABASE_URL -c "\d fitness_tracker_connections"

# Verify data is intact
psql $DATABASE_URL -c "SELECT COUNT(*) FROM fitness_tracker_connections;"
```

---

## Step 5: Restart Application

After migration, restart the backend application:

```bash
# Railway will auto-deploy when you push the migration

# Or manually trigger:
railway up
```

---

## Step 6: Test Endpoints

Test the fitness tracker endpoints:

```bash
# Get Strava connection status
curl https://web-production-188d1.up.railway.app/api/v1/fitness/strava/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# Should return 200 OK with connection status
# NOT 500 Internal Server Error
```

---

## Rollback Plan

If something goes wrong:

### Option 1: Rollback Migration
```bash
# Rollback to previous state
alembic downgrade -1

# This will rename the table back to fitness_connections
```

### Option 2: Restore from Backup
```bash
# Drop current database (CAREFUL!)
psql $DATABASE_URL -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Restore from backup
psql $DATABASE_URL < backup_before_rename_YYYYMMDD_HHMMSS.sql
```

### Option 3: Quick Fix (Emergency)
If production is broken and you need immediate fix:

```python
# Temporarily change model back to old table name
# In app/modules/fitness_trackers/domain/connection.py:
__tablename__ = "fitness_connections"  # Revert to old name

# Push hotfix to production
git commit -am "hotfix: Revert to old table name"
git push
```

---

## Post-Migration Verification

After successful migration, verify:

1. **Application starts without errors**
   - Check Railway logs for startup
   - No SQLAlchemy errors

2. **Fitness tracker endpoints work**
   - GET `/api/v1/fitness/strava/status` returns 200
   - GET `/api/v1/fitness/connections` returns 200
   - No CORS errors
   - No "table does not exist" errors

3. **Existing connections preserved**
   - Users can see their connected trackers
   - OAuth tokens still valid
   - No data loss

4. **New connections work**
   - Users can connect new trackers
   - Authorization flow completes
   - Connection saved to database

---

## Timeline

**Estimated downtime:** < 5 seconds
**Migration duration:** Instant (table rename is atomic)
**Risk level:** Low (reversible, no data changes)

**Best time to run:**
- Off-peak hours (late night/early morning)
- When fewest users are active
- Have someone monitoring after deployment

---

## Common Issues

### Issue 1: Table doesn't exist
```
relation "fitness_connections" does not exist
```
**Solution:** Table might already be renamed. Check with `\dt fitness*`

### Issue 2: Multiple heads
```
Multiple heads are present
```
**Solution:** Already fixed with merge migration `64cec31dd3a1`

### Issue 3: Migration stuck
```
alembic upgrade hangs
```
**Solution:** Check for active connections locking the table
```bash
psql $DATABASE_URL -c "SELECT * FROM pg_locks WHERE relation::regclass::text = 'fitness_connections';"
```

---

## Support

If issues occur during migration:
1. Check Railway logs: `railway logs`
2. Check database: `psql $DATABASE_URL`
3. Verify migration state: `alembic current`
4. Rollback if needed: `alembic downgrade -1`

---

## Success Criteria

Migration is successful when:
- ✅ `alembic current` shows revision `bb7b4d03c40d`
- ✅ Table `fitness_tracker_connections` exists
- ✅ Table `fitness_connections` does NOT exist
- ✅ Application starts without errors
- ✅ Fitness endpoints return 200
- ✅ No data loss (row count matches)

---

**Ready to proceed?** Follow the steps above in order.
