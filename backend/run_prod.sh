#!/bin/bash
# Production server with Gunicorn and Uvicorn workers

# Number of worker processes
WORKERS=${WORKERS:-4}

# Bind address
BIND=${BIND:-"0.0.0.0:8000"}

# Run Gunicorn with Uvicorn workers
exec gunicorn app.main:app \
    --workers $WORKERS \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind $BIND \
    --access-logfile - \
    --error-logfile - \
    --log-level info