# GlycoGrit Backend

FastAPI backend deployed on Railway with Doppler secrets management.

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - API documentation (Swagger UI)
- `GET /api/v1/events` - List events with filters (pagination, category, difficulty, is_featured)
- `GET /api/v1/events/{id}` - Get event details
- `POST /api/v1/events/{id}/register` - Register for event (requires auth)
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration

## Secrets Management with Doppler

**All secrets are stored in Doppler** - no secrets in `.env` files or git. Both backend and frontend secrets are stored in a single unified Doppler project (`glycogrit`) for single source of truth.

### Doppler Project Structure

- **Project**: `glycogrit` (unified backend + frontend secrets)
- **Configs**:
  - `dev_personal` - Development environment
  - `stg_backend` - Staging environment
  - `prd_backend` - Production environment

### How It Works

```bash
# Run with any environment - script picks the right Doppler config
./start.sh [development|staging|production]
```

| Command | Doppler Config | Environment |
|---------|----------------|-------------|
| `./start.sh` or `./start.sh development` | `dev_personal` | development |
| `./start.sh staging` | `stg_backend` | staging |
| `./start.sh production` | `prd_backend` | production |

The script automatically:
1. Maps your environment choice to the correct Doppler config
2. Injects all secrets from Doppler (backend + frontend)
3. Starts the server with appropriate settings (reload for dev/staging, workers for production)

### Local Development

```bash
# Development (default)
./start.sh

# Or explicitly
./start.sh development
```

### Testing Other Environments Locally

```bash
# Test with staging configuration
./start.sh staging

# Test with production configuration (⚠️ uses production database!)
./start.sh production
```

## Environment Variables

All environments use these variables (managed in unified Doppler project):

### Backend Variables
```
ENVIRONMENT=development|staging|production
PORT=8000
HOST=0.0.0.0
DATABASE_URL=postgresql://...
ALLOWED_ORIGINS=comma,separated,urls
JWT_SECRET_KEY=unique-per-environment
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True|False
RAILWAY_PUBLIC_URL=https://web-production-188d1.up.railway.app
RAILWAY_PRIVATE_URL=web.railway.internal
```

### Frontend Variables (also in same Doppler project)
```
VITE_API_BASE_URL=http://localhost:8000|https://staging-api.glycogrit.com|https://api.glycogrit.com
VITE_APP_NAME=GlycoGrit (Dev)|GlycoGrit (Staging)|GlycoGrit
VITE_ENABLE_ANALYTICS=true|false
VITE_ENABLE_DEBUG_MODE=true|false
VITE_ENVIRONMENT=development|staging|production
VITE_INSTAGRAM_ACCESS_TOKEN=...
```

## Railway Deployment

### Railway URLs

- **Public Networking**: `https://web-production-188d1.up.railway.app`
- **Private Networking**: `web.railway.internal`

Both URLs are stored in Doppler for reference.

### Setup Doppler Integration

1. Go to Railway project settings
2. Add Doppler integration
3. Select project: `glycogrit` (unified backend + frontend)
4. Select config:
   - Production service: `prd_backend`
   - Staging service: `stg_backend`

### Manual Deployment

```bash
railway up
```

Health check endpoint: `/health`

## Database

All environments share the same Railway PostgreSQL database:
- Host: `nozomi.proxy.rlwy.net:29493`
- Database: `railway`
- Connection managed via Doppler `DATABASE_URL` secret

---

## 🚀 Running Locally

### Prerequisites

1. **Python 3.10+** installed
2. **Doppler CLI** installed and authenticated
3. **Virtual environment** (venv) set up

### Setup Steps

```bash
# 1. Clone the repository
cd glycogrit-backend

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Authenticate with Doppler (one-time setup)
doppler login

# 6. Setup Doppler for this project (one-time setup)
doppler setup --project glycogrit --config dev_personal
```

### Starting the Server

**⚠️ CRITICAL: Always use Doppler to inject environment variables!**

```bash
# CORRECT WAY - Start server with Doppler
doppler run -- uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# WRONG WAY - This will use fallback defaults and FAIL!
uvicorn app.main:app --reload  # ❌ DON'T DO THIS
```

### Why Doppler is Required

The application uses `os.getenv()` to read environment variables with fallback defaults:

```python
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/dbname"  # Fallback (won't work!)
)
```

**Without Doppler:**
- Environment variables are NOT loaded
- Application falls back to `localhost` database (which doesn't exist)
- Database connections will fail with: `FATAL: role "user" does not exist`

**With Doppler:**
- All secrets are injected from Doppler (`DATABASE_URL`, `SECRET_KEY`, etc.)
- Application connects to the correct Railway PostgreSQL database
- Everything works as expected

---

## 🔧 Troubleshooting

### Issue: Database Connection Failed - "role 'user' does not exist"

**Symptoms:**
```
Database connection failed: (psycopg2.OperationalError) connection to server at "localhost" (127.0.0.1), port 5432 failed: FATAL: role "user" does not exist
```

**Cause:**
Server was started WITHOUT Doppler, so it's using the fallback `DATABASE_URL`:
```
postgresql://user:password@localhost:5432/dbname
```

**Solution:**
Always start the server with Doppler:
```bash
# Stop the current server (Ctrl+C)

# Restart with Doppler
doppler run --project glycogrit --config dev_personal -- uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Verification:**
Check the startup logs. You should see:
```
DATABASE_URL: postgresql://postgres:***@nozomi.proxy.rlwy.net:29493/railway
```

NOT:
```
DATABASE_URL: postgresql://user:***@localhost:5432/dbname
```

---

### Issue: Health Check Returns "unhealthy" Status

**Check 1: Verify Doppler is Running**
```bash
# Your server logs should show the Railway database URL
# Look for: nozomi.proxy.rlwy.net:29493
# NOT: localhost:5432
```

**Check 2: Test Database Connection Manually**
```bash
# With virtual environment activated
doppler run -- python -c "
import psycopg2
import os
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
print('✅ Database connection successful!')
conn.close()
"
```

**Check 3: Test Detailed Health Check**
```bash
# Simple health check (no DB connection)
curl http://localhost:8000/health

# Detailed health check (includes DB, system resources)
curl http://localhost:8000/health?detailed=true
```

---

### Issue: "ModuleNotFoundError" or Import Errors

**Cause:** Dependencies not installed or virtual environment not activated

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep fastapi
pip list | grep psycopg2
pip list | grep psutil
```

---

### Issue: Multiple Database Environments

**Current Setup:**
All environments (dev, staging, production) use the **same Railway PostgreSQL database**:
```bash
# Check current setup
echo "DEV:" && doppler secrets get DATABASE_URL --project glycogrit --config dev_personal --plain
echo "STG:" && doppler secrets get DATABASE_URL --project glycogrit --config stg_backend --plain
echo "PRD:" && doppler secrets get DATABASE_URL --project glycogrit --config prd_backend --plain
```

**⚠️ WARNING:**
This means dev/staging changes can affect production data!

**Recommended Solution:**
Create separate databases for each environment:
1. Create separate Railway PostgreSQL instances for staging and production
2. Update Doppler secrets with different `DATABASE_URL` for each config
3. This ensures data isolation and safe testing

---

## 📊 Health Check Endpoints

### Simple Health Check (Fast, No DB)
```bash
curl http://localhost:8000/health
```

Returns:
```json
{
  "status": "healthy",
  "message": "Application is running",
  "uptime_seconds": 120,
  "timestamp": "2026-04-17T09:37:54.524789",
  "application": "GlycoGrit Backend API",
  "version": "1.0.0",
  "environment": "development"
}
```

### Detailed Health Check (Comprehensive)
```bash
curl http://localhost:8000/health?detailed=true
```

Returns comprehensive metrics:
- **Database**: Connection status, query performance, pool statistics
- **System Resources**: CPU, memory, disk usage
- **Uptime**: Application start time and uptime
- **HTTP Status Codes**:
  - `200 OK`: Healthy or degraded
  - `503 Service Unavailable`: Unhealthy (database down, critical failures)

---

## 🐛 Debugging Tips

### Check Loaded Environment Variables
```bash
# Start server and check what DATABASE_URL is loaded
doppler run -- python -c "
import os
from app.core.config import settings
print(f'Environment: {settings.ENVIRONMENT}')
print(f'Database: {settings.DATABASE_URL[:50]}...')
print(f'Host: {settings.HOST}:{settings.PORT}')
"
```

### View All Doppler Secrets
```bash
# List all secrets (values are masked)
doppler secrets --project glycogrit --config dev_personal

# Get specific secret value
doppler secrets get DATABASE_URL --project glycogrit --config dev_personal --plain
```

### Test Database Connection
```bash
# Quick connection test
doppler run -- python -c "
from sqlalchemy import create_engine, text
from app.core.config import settings
engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text('SELECT current_database(), current_user'))
    print(f'✅ Connected to: {result.fetchone()}')
"
```

---

## 📝 Quick Reference Commands

### Development Workflow
```bash
# Activate virtual environment
source venv/bin/activate

# Start server (dev mode with auto-reload)
doppler run -- uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run database migrations
doppler run -- alembic upgrade head

# Create new migration
doppler run -- alembic revision --autogenerate -m "description"

# Access API docs
open http://localhost:8000/docs
```

### Testing
```bash
# Run tests
doppler run -- pytest

# Run tests with coverage
doppler run -- pytest --cov=app

# Run specific test file
doppler run -- pytest tests/test_auth.py
```

---

## 🔐 Security Best Practices

1. **Never commit secrets** - All secrets in Doppler only
2. **Always use Doppler** - Don't create `.env` files manually
3. **Separate databases** - Use different databases for dev/staging/prod
4. **Rotate secrets regularly** - Update JWT secrets, API keys periodically
5. **Use private networking** - Railway services communicate via internal URLs

---

## 📚 Additional Documentation

- **API Endpoints**: See `API_ENDPOINTS.md`
- **Database Setup**: See `DATABASE_SETUP.md`
- **Alembic Migrations**: See `alembic/README.md`
- **Database Scripts**: See `database_scripts/README.md`

---

**Last Updated**: April 17, 2026
