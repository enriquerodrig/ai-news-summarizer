#!/bin/bash
# Startup script for Railway deployment

# Railway provides PORT as an environment variable
# If not set (local development), default to 8080
if [ -z "$PORT" ]; then
    PORT=8080
fi

echo "Starting application on port $PORT"

# Start uvicorn
exec python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
