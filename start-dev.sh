#!/bin/bash
# Start backend for local development
# Automatically uses Doppler dev_personal config

source venv/bin/activate
doppler run --config dev_personal -- python -m uvicorn app.main:app --reload --port 8000
