#!/bin/bash
# Start backend with Doppler secrets for staging

# Activate virtual environment
source venv/bin/activate

# Run with Doppler
doppler run --config stg_backend -- python -m uvicorn app.main:app --reload --port 8000
