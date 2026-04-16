#!/bin/bash
# Start backend with Doppler secrets for development

# Activate virtual environment
source venv/bin/activate

# Run with Doppler
doppler run --config dev_personal -- python -m uvicorn app.main:app --reload --port 8000
