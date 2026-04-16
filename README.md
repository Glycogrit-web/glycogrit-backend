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

This project uses **Doppler** for centralized secrets management. The app automatically detects which environment it's running in based on the Doppler config.

### How It Works

- **Locally**: Run `./start-dev.sh` → Uses Doppler `dev_personal` config → Sets `ENVIRONMENT=development`
- **On Railway (Staging)**: Doppler integration → Uses `stg_backend` config → Sets `ENVIRONMENT=staging`
- **On Railway (Production)**: Doppler integration → Uses `prd_backend` config → Sets `ENVIRONMENT=production`

The app reads the `ENVIRONMENT` variable from Doppler to determine behavior (CORS, debug mode, etc).

### Local Development

```bash
# Start with development secrets (recommended)
./start-dev.sh

# Or manually
doppler run --config dev_personal -- python -m uvicorn app.main:app --reload
```

### Testing Other Environments Locally

```bash
# Test with staging configuration
./start-staging.sh

# Test with production configuration (⚠️ uses production database!)
./start-production.sh
```

## Environment Variables

All environments use these variables (managed in Doppler):

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
```

## Railway Deployment

### Setup Doppler Integration

1. Go to Railway project settings
2. Add Doppler integration
3. Select project: `glycogrit-backend`
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
