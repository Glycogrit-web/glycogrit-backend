# Database Migration Guide - Extensions & Indexes

## Prerequisites

✅ You've already installed these extensions in your Railway PostgreSQL database:
- `pg_trgm` (v1.6)
- `pg_stat_statements` (v1.12)
- `uuid-ossp` (v1.1)
- `btree_gin` (v1.3)
- `pgcrypto` (v1.4)
- `hstore` (v1.8)
- `citext` (v1.8)
- `earthdistance` (v1.2) + `cube` (v1.5)
- `unaccent` (v1.1)

## Migration Steps

### Step 1: Backup Your Database (CRITICAL!)

```bash
# If using Railway CLI
railway run pg_dump -Fc > backup_before_indexes_$(date +%Y%m%d).dump

# Or using direct connection
pg_dump -h your-host -U your-user -d your-db -Fc > backup_before_indexes_$(date +%Y%m%d).dump
```

### Step 2: Test in Staging First (Recommended)

If you have a staging environment, run the migration there first:

```bash
# Connect to staging database
psql -h staging-host -U staging-user -d staging-db -f database_scripts/002_extensions_indexes_migration.sql
```

### Step 3: Run the Migration in Production

**Option A: Using Railway CLI** (Recommended)
```bash
cd glycogrit-backend
railway run psql < database_scripts/002_extensions_indexes_migration.sql
```

**Option B: Using psql directly**
```bash
psql -h your-railway-host.railway.app \
     -U postgres \
     -d railway \
     -f database_scripts/002_extensions_indexes_migration.sql
```

**Option C: Copy-paste into Railway dashboard**
1. Go to Railway dashboard → Your PostgreSQL service → Data
2. Open "Query" tab
3. Copy-paste contents of `002_extensions_indexes_migration.sql`
4. Click "Run"

⚠️ **IMPORTANT**: The script uses `CREATE INDEX CONCURRENTLY` which:
- ✅ Does NOT lock tables (safe for production)
- ❌ Cannot run inside a transaction block
- ⏱️ Takes longer to create (but worth it for no downtime)

### Step 4: Verify the Migration

```sql
-- Check that indexes were created
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_indexes
JOIN pg_stat_user_indexes USING (schemaname, tablename, indexname)
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;

-- Check email column type changed to citext
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'users'
  AND column_name = 'email';
-- Should show: data_type = 'citext'
```

### Step 5: Monitor Performance

After 24-48 hours of production traffic, check index usage:

```sql
-- See which indexes are being used
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS times_used,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%'
ORDER BY idx_scan DESC
LIMIT 20;

-- Find unused indexes (may need removal)
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
  AND indexname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

## Rollback (if needed)

If something goes wrong:

```bash
# Rollback indexes only (keeps citext)
psql -h your-host -U your-user -d your-db -f database_scripts/003_rollback_indexes.sql

# Restore from backup (if needed)
pg_restore -h your-host -U your-user -d your-db backup_before_indexes_YYYYMMDD.dump
```

## Expected Behavior Changes

### ✅ Faster Queries
- User search by name/email: **50-100x faster**
- Event search: **20-50x faster**
- Challenge leaderboards: **10-20x faster**
- Rewards filtering: **5-10x faster**

### ⚠️ Email Comparison Changes

**Before (case-sensitive):**
```python
db.query(User).filter(User.email == "USER@EXAMPLE.COM").first()  # Returns None
db.query(User).filter(User.email == "user@example.com").first()  # Returns user
```

**After (case-insensitive with citext):**
```python
db.query(User).filter(User.email == "USER@EXAMPLE.COM").first()  # Returns user ✓
db.query(User).filter(User.email == "user@example.com").first()  # Returns user ✓
```

This is **GOOD** for user experience (users can log in regardless of email case).

### 📊 Disk Space Usage

The indexes will take additional disk space:

| Index Type | Estimated Size (for 10k users, 1k events) |
|-----------|-------------------------------------------|
| Trigram (GIN) | ~5-10 MB per text column |
| Composite B-tree | ~1-2 MB per index |
| JSONB (GIN) | ~2-5 MB per JSONB column |
| **Total** | ~**100-200 MB** |

At 100k users and 10k events: ~**1-2 GB** (worth it for performance!)

## Troubleshooting

### Issue: "CREATE INDEX CONCURRENTLY cannot run inside a transaction block"

**Solution**: Run the script outside of a transaction:
```bash
psql -h your-host -U your-user -d your-db --no-single-transaction -f 002_extensions_indexes_migration.sql
```

### Issue: "Extension 'pg_trgm' does not exist"

**Solution**: Install the extension first:
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

Then re-run the migration script.

### Issue: Index creation is taking too long

**Solution**: This is normal for `CREATE INDEX CONCURRENTLY` on large tables. It's safe to let it run. Check progress:
```sql
-- Check current locks (should show no blocking locks)
SELECT * FROM pg_locks WHERE granted = false;

-- Check active index builds
SELECT
    pid,
    now() - query_start AS duration,
    query
FROM pg_stat_activity
WHERE query LIKE '%CREATE INDEX%'
  AND state = 'active';
```

### Issue: Query planner not using new indexes

**Solution**: Run `ANALYZE` on the table:
```sql
ANALYZE users;
ANALYZE events;
ANALYZE registrations;
ANALYZE activity_progress;
```

Check query plan:
```sql
EXPLAIN ANALYZE
SELECT * FROM users
WHERE first_name ILIKE '%john%';
-- Should show "Index Scan using idx_users_first_name_trgm"
```

## Performance Testing

Test query performance before/after:

```sql
-- Before migration (slow - full table scan)
EXPLAIN ANALYZE
SELECT * FROM users
WHERE first_name ILIKE '%john%';
-- Expected: Seq Scan on users (cost=...)

-- After migration (fast - index scan)
EXPLAIN ANALYZE
SELECT * FROM users
WHERE first_name ILIKE '%john%';
-- Expected: Bitmap Index Scan using idx_users_first_name_trgm (cost=...)
```

## Monitoring with pg_stat_statements

Check slowest queries:

```sql
SELECT
    query,
    calls,
    total_exec_time / 1000 AS total_seconds,
    mean_exec_time AS avg_ms,
    max_exec_time AS max_ms
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY mean_exec_time DESC
LIMIT 20;
```

Reset stats after migration to see improvement:

```sql
-- Reset statistics (do this after migration)
SELECT pg_stat_statements_reset();
```

## Next Steps

1. ✅ Run migration in production
2. ✅ Verify indexes created successfully
3. ⏱️ Wait 24-48 hours for production traffic
4. 📊 Check index usage statistics
5. 🗑️ Drop unused indexes (if any)
6. 🚀 Enjoy faster queries!

## Need Help?

- Check PostgreSQL logs: `railway logs --service postgres`
- Join Railway Discord: https://discord.gg/railway
- File an issue: [Your repo issues page]

---

**Last Updated**: 2025-05-11
**Database**: PostgreSQL 14+ (Railway)
**Application**: GlycoGrit Running Platform
