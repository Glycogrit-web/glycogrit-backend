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
# Trigger redeploy to pick up Doppler ENVIRONMENT variable correctly
