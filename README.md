# GlycoGrit Backend

Minimal FastAPI backend deployed on Railway.

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - API documentation (Swagger UI)

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000
```

## Environment Variables

```
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=development
ALLOWED_ORIGINS=*
```

## Railway Deployment

Push to master branch - Railway will automatically deploy.

Health check endpoint: `/health`
