# --- Build stage ---
FROM python:3.14-slim-bookworm AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install \
    torch==2.6.0+cpu \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# --- Runtime stage ---
FROM python:3.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FLASK_APP=app.py FLASK_ENV=production
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl sqlite3 cron \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY . .
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
RUN mkdir -p /app/static/css /app/static/js /app/data /app/logs /app/data/backups \
    && chown -R appuser:appuser /app/logs /app/data
# Install backup crontab
COPY scripts/ke-wp-backup /etc/cron.d/ke-wp-backup
RUN chmod 0644 /etc/cron.d/ke-wp-backup
# Make scripts executable
RUN chmod +x /app/scripts/backup_db.sh /app/scripts/docker-entrypoint.sh
USER appuser
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
