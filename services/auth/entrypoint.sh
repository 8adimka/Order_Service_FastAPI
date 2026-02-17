#!/bin/bash
set -e

echo "Applying database migrations..."
cd /app/alembic
if ! alembic upgrade head; then
    echo "Migration failed, but continuing..."
fi

echo "Starting FastAPI application..."
cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
