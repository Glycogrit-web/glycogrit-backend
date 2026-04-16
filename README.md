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

This project uses **Doppler** for managing secrets across environments.

### Doppler Setup

All secrets are stored in Doppler with three environments:
- `dev_personal` - Local development
- `stg_backend` - Staging environment
- `prd_backend` - Production environment

### Local Development with Doppler

```bash
# Option 1: Use the startup script (recommended)
./start-dev.sh

# Option 2: Run manually
doppler run --config dev_personal -- python -m uvicorn app.main:app --reload --port 8000
```

### Testing Different Environments Locally

```bash
# Test with staging secrets
./start-staging.sh

# Test with production secrets (use with caution!)
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
