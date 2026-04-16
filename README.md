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

**All secrets are stored in Doppler** - no secrets in `.env` files or git. The single `start.sh` script automatically uses the correct Doppler configuration based on the environment you specify.

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
2. Injects all secrets from Doppler
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
