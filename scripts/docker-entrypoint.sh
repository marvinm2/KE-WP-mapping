#!/bin/bash
# /app/scripts/docker-entrypoint.sh
# Start cron for scheduled backups, then exec the main process (gunicorn).
# Using exec ensures gunicorn receives Docker stop signals correctly.
set -e

# Start cron daemon in background for backup scheduling
service cron start || true

# Hand off to gunicorn (or whatever CMD is passed)
exec "$@"
