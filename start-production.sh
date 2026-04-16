#!/bin/bash
# Start backend for production (local testing with production secrets)
# ⚠️  Use with caution - uses production database!
# Uses Doppler prd_backend config

source venv/bin/activate
doppler run --config prd_backend -- python -m uvicorn app.main:app --port 8000 --workers 4
