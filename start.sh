#!/bin/bash
# Startup script for Railway deployment
# Handles PORT environment variable properly

# Use Railway's PORT if set, otherwise default to 8080
PORT=${PORT:-8080}

# Start uvicorn with the resolved port
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
