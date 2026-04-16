#!/bin/bash
# Start backend for staging (local testing with staging secrets)
# Uses Doppler stg_backend config

source venv/bin/activate
doppler run --config stg_backend -- python -m uvicorn app.main:app --reload --port 8000
