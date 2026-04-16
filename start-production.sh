#!/bin/bash
# Start backend with Doppler secrets for production

# Activate virtual environment
source venv/bin/activate

# Run with Doppler (without reload for production)
doppler run --config prd_backend -- python -m uvicorn app.main:app --port 8000 --workers 4
