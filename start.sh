#!/bin/bash
# Universal start script for all environments
# Usage: ./start.sh [development|staging|production]

# Default to development if no argument provided
ENV=${1:-development}

# Map environment to Doppler config
case $ENV in
  development|dev)
    DOPPLER_CONFIG="dev_personal"
    ;;
  staging|stg)
    DOPPLER_CONFIG="stg_backend"
    ;;
  production|prod|prd)
    DOPPLER_CONFIG="prd_backend"
    ;;
  *)
    echo "❌ Invalid environment: $ENV"
    echo "Usage: ./start.sh [development|staging|production]"
    exit 1
    ;;
esac

echo "🚀 Starting backend with environment: $ENV"
echo "📦 Using Doppler config: $DOPPLER_CONFIG"

# Activate virtual environment
source venv/bin/activate

# Run with Doppler
if [ "$ENV" = "production" ] || [ "$ENV" = "prod" ] || [ "$ENV" = "prd" ]; then
  # Production: use workers, no reload
  echo "⚠️  Production mode: 4 workers, no auto-reload"
  doppler run --config $DOPPLER_CONFIG -- python -m uvicorn app.main:app --port 8000 --workers 4
else
  # Development/Staging: use reload
  echo "🔄 Development mode: auto-reload enabled"
  doppler run --config $DOPPLER_CONFIG -- python -m uvicorn app.main:app --reload --port 8000
fi
