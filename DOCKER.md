# Docker & Deployment Guide

Complete guide for running GlycoGrit Backend with Docker locally and deploying to production.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development with Docker](#local-development-with-docker)
3. [Production Deployment](#production-deployment)
4. [Docker Commands Reference](#docker-commands-reference)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Docker Desktop** (v20.10+)
   - Download: https://www.docker.com/products/docker-desktop
   - Includes Docker Engine and Docker Compose

2. **Git** (v2.x+)
   - For cloning the repository

### Optional Tools

- **Doppler CLI** - For secrets management (recommended for production-like local setup)
- **pgAdmin** - For database management (included in docker-compose)

---

## Local Development with Docker

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/glycogrit-team/glycogrit-backend.git
cd glycogrit-backend

# 2. Start all services (backend + PostgreSQL)
docker-compose up

# 3. Access the services
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# pgAdmin (optional): http://localhost:5050
```

### Detailed Setup

#### Option 1: Using Docker Compose (Recommended)

```bash
# Start services in detached mode
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Stop and remove volumes (⚠️ deletes database data)
docker-compose down -v
```

#### Option 2: Using Docker Only

```bash
# Build the image
docker build -t glycogrit-backend .

# Run the container
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e SECRET_KEY=your-secret-key \
  --name glycogrit-backend \
  glycogrit-backend

# View logs
docker logs -f glycogrit-backend

# Stop container
docker stop glycogrit-backend
docker rm glycogrit-backend
```

### Development with Hot Reload

```bash
# Use the development Dockerfile
docker-compose -f docker-compose.yml up

# Or build dev image manually
docker build -f Dockerfile.dev -t glycogrit-backend:dev .
docker run -p 8000:8000 -v $(pwd)/app:/app/app glycogrit-backend:dev
```

### Running Database Migrations

```bash
# Run migrations in the backend container
docker-compose exec backend alembic upgrade head

# Create a new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Rollback last migration
docker-compose exec backend alembic downgrade -1
```

### Accessing the Database

```bash
# Connect to PostgreSQL using psql
docker-compose exec db psql -U postgres -d glycogrit_dev

# Or use pgAdmin
# 1. Start with tools profile: docker-compose --profile tools up -d
# 2. Open http://localhost:5050
# 3. Login with admin@glycogrit.com / admin123
# 4. Add server:
#    - Host: db
#    - Port: 5432
#    - Username: postgres
#    - Password: postgres123
```

---

## Production Deployment

### Railway Deployment

The backend is automatically deployed to Railway using Docker.

#### Configuration

1. **railway.json** - Deployment configuration
   ```json
   {
     "build": {
       "builder": "DOCKERFILE",
       "dockerfilePath": "Dockerfile"
     },
     "deploy": {
       "healthcheckPath": "/health",
       "healthcheckTimeout": 100,
       "restartPolicyType": "ON_FAILURE",
       "restartPolicyMaxRetries": 3
     }
   }
   ```

2. **Environment Variables** - Managed via Doppler integration
   - DATABASE_URL
   - SECRET_KEY
   - ALLOWED_ORIGINS
   - ENVIRONMENT

#### Deployment Process

```bash
# Option 1: Deploy via Git push (automatic)
git push origin main

# Option 2: Deploy via Railway CLI
railway up

# Option 3: Redeploy via Railway dashboard
# Go to https://railway.app → Your Project → Redeploy
```

#### Health Checks

Railway automatically monitors the `/health` endpoint:
- **Interval**: Every 30 seconds
- **Timeout**: 100 seconds for initial startup
- **Retries**: 3 failed checks trigger restart

### Other Platforms

#### AWS ECS (Elastic Container Service)

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t glycogrit-backend .
docker tag glycogrit-backend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/glycogrit-backend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/glycogrit-backend:latest

# Create ECS task definition and service
# See AWS documentation for complete setup
```

#### Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT-ID/glycogrit-backend
gcloud run deploy glycogrit-backend \
  --image gcr.io/PROJECT-ID/glycogrit-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Azure Container Instances

```bash
# Build and push to ACR
az acr build --registry <registry-name> --image glycogrit-backend:latest .

# Deploy to ACI
az container create \
  --resource-group myResourceGroup \
  --name glycogrit-backend \
  --image <registry-name>.azurecr.io/glycogrit-backend:latest \
  --dns-name-label glycogrit-backend \
  --ports 8000
```

---

## Docker Commands Reference

### Building Images

```bash
# Build production image
docker build -t glycogrit-backend:latest .

# Build with custom tag
docker build -t glycogrit-backend:v1.0.0 .

# Build development image
docker build -f Dockerfile.dev -t glycogrit-backend:dev .

# Build with no cache
docker build --no-cache -t glycogrit-backend .
```

### Running Containers

```bash
# Run container with environment variables
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e SECRET_KEY=... \
  glycogrit-backend

# Run with volume mount (development)
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/app:/app/app \
  glycogrit-backend:dev

# Run with custom command
docker run -it glycogrit-backend bash
```

### Managing Containers

```bash
# List running containers
docker ps

# List all containers
docker ps -a

# View logs
docker logs glycogrit-backend
docker logs -f glycogrit-backend  # Follow logs
docker logs --tail 100 glycogrit-backend  # Last 100 lines

# Execute command in running container
docker exec -it glycogrit-backend bash
docker exec glycogrit-backend python --version

# Stop container
docker stop glycogrit-backend

# Remove container
docker rm glycogrit-backend

# Remove all stopped containers
docker container prune
```

### Managing Images

```bash
# List images
docker images

# Remove image
docker rmi glycogrit-backend:latest

# Remove all unused images
docker image prune -a

# Tag image
docker tag glycogrit-backend:latest glycogrit-backend:v1.0.0

# Push to registry
docker push glycogrit-backend:latest
```

### Docker Compose Commands

```bash
# Start services
docker-compose up
docker-compose up -d  # Detached mode
docker-compose up --build  # Rebuild images

# Stop services
docker-compose stop
docker-compose down  # Stop and remove containers
docker-compose down -v  # Also remove volumes

# View logs
docker-compose logs
docker-compose logs -f backend  # Follow specific service
docker-compose logs --tail=100  # Last 100 lines

# Execute commands
docker-compose exec backend bash
docker-compose exec db psql -U postgres

# Scale services
docker-compose up -d --scale backend=3

# View running services
docker-compose ps
```

---

## Troubleshooting

### Issue: Container Exits Immediately

**Check logs:**
```bash
docker logs glycogrit-backend
```

**Common causes:**
1. Missing environment variables
2. Database connection failure
3. Port already in use

**Solution:**
```bash
# Check if port is in use
lsof -i :8000

# Verify environment variables
docker exec glycogrit-backend env | grep DATABASE_URL

# Test database connection
docker-compose exec backend python -c "from app.core.database import engine; engine.connect()"
```

### Issue: Database Connection Refused

**Error:**
```
psycopg2.OperationalError: connection to server at "db" (172.18.0.2), port 5432 failed
```

**Solution:**
```bash
# Check if database is running
docker-compose ps

# Check database health
docker-compose exec db pg_isready -U postgres

# Wait for database to be ready (it takes ~10 seconds on first start)
docker-compose up -d db
sleep 10
docker-compose up backend
```

### Issue: Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
# Rebuild image with no cache
docker-compose build --no-cache backend

# Or rebuild specific service
docker build --no-cache -t glycogrit-backend .
```

### Issue: Port Already in Use

**Error:**
```
Error starting userland proxy: listen tcp 0.0.0.0:8000: bind: address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port in docker-compose.yml
ports:
  - "8001:8000"
```

### Issue: Hot Reload Not Working

**Cause:** Volume mount not configured correctly

**Solution:**
```bash
# Ensure volume mount in docker-compose.yml
volumes:
  - ./app:/app/app

# Restart with docker-compose
docker-compose down
docker-compose up
```

### Issue: Out of Disk Space

**Check disk usage:**
```bash
docker system df
```

**Clean up:**
```bash
# Remove unused containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything unused
docker system prune -a --volumes
```

---

## Best Practices

### Security

1. **Never commit secrets** - Use Doppler or environment files
2. **Run as non-root user** - Production Dockerfile uses `appuser`
3. **Multi-stage builds** - Reduces image size and attack surface
4. **Health checks** - Ensure service reliability
5. **Resource limits** - Prevent resource exhaustion

### Performance

1. **Layer caching** - Order Dockerfile commands from least to most frequently changed
2. **.dockerignore** - Exclude unnecessary files from build context
3. **Multi-stage builds** - Separate build and runtime dependencies
4. **Connection pooling** - SQLAlchemy pool configured for Docker
5. **Workers** - Production uses 4 workers (configurable)

### Development

1. **Volume mounts** - Enable hot reload
2. **docker-compose** - Simplify multi-service setup
3. **Health checks** - Ensure services are ready before testing
4. **Logging** - Use structured logging for debugging

---

## Additional Resources

- **Docker Documentation**: https://docs.docker.com/
- **Docker Compose Documentation**: https://docs.docker.com/compose/
- **Railway Documentation**: https://docs.railway.app/
- **FastAPI + Docker**: https://fastapi.tiangolo.com/deployment/docker/
- **PostgreSQL Docker**: https://hub.docker.com/_/postgres

---

**Last Updated**: April 17, 2026
**Maintained By**: GlycoGrit Team
