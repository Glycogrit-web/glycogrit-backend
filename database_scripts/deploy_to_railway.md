# Deploying Database Schema to Railway

## Quick Deploy Guide

### Step 1: Commit All Changes

```bash
git add database_scripts/
git commit -m "Add database schema and migration scripts"
git push origin master
```

### Step 2: Run Migrations on Railway

You have three options:

#### Option A: Using Railway CLI (Recommended)

```bash
# Install Railway CLI if not already installed
npm install -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Run migrations
railway run python database_scripts/run_migrations.py migrate

# Seed test data (optional)
railway run python database_scripts/db_manager.py seed
```

#### Option B: Temporary API Endpoint (Quick Test)

We can add a temporary endpoint to run migrations via HTTP request.

1. Add this endpoint to `app/main.py`:

```python
@app.post("/api/v1/admin/run-migrations")
async def run_migrations():
    """TEMPORARY: Run database migrations (remove after first use)"""
    try:
        from database_scripts.run_migrations import MigrationRunner
        runner = MigrationRunner(settings.DATABASE_URL)
        runner.run_all_migrations()
        return {"status": "success", "message": "Migrations completed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

2. After deployment, call: `POST https://your-app.railway.app/api/v1/admin/run-migrations`

3. **IMPORTANT: Remove this endpoint after use!**

#### Option C: Manual SQL Execution

1. Go to Railway Dashboard → Postgres service → Data tab
2. Copy the contents of `database_scripts/001_initial_schema.sql`
3. Paste and execute in the Query tab

### Step 3: Verify Database Schema

```bash
# Check tables were created
railway run python database_scripts/db_manager.py tables

# Check migration status
railway run python database_scripts/run_migrations.py status

# View database stats
railway run python database_scripts/db_manager.py stats
```

### Step 4: Test Database Connection

Visit your app's `/api/v1/db-test` endpoint to verify the connection still works with the new schema.

## Common Issues

### Issue: "railway: command not found"
**Solution**: Install Railway CLI:
```bash
npm install -g @railway/cli
```

### Issue: "Could not find project"
**Solution**: Link your project:
```bash
railway link
# Then select your project from the list
```

### Issue: Migration fails with connection error
**Solution**: Verify DATABASE_URL is set correctly in Railway dashboard

## Next Steps

After successful migration:

1. ✅ Database schema is created
2. ✅ All tables, indexes, and constraints are in place
3. ✅ Ready to build API endpoints
4. 🎯 Start implementing user authentication
5. 🎯 Create event management endpoints
6. 🎯 Build registration system

## Need Help?

Check Railway logs:
```bash
railway logs
```

Or review the main README: [database_scripts/README.md](README.md)
