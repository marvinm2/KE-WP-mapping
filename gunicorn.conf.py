# gunicorn.conf.py
# Gunicorn configuration for KE-WP Mapping application.
# Source: https://gunicorn.org/reference/settings
#
# Worker count: 1 worker to ensure in-memory session consistency
# (CSRF tokens, OAuth state). With preload_app=True the BioBERT model
# is loaded once in the master process anyway.

bind = "0.0.0.0:5000"
workers = 1          # Single worker to ensure session consistency (CSRF, OAuth state)
worker_class = "sync"
timeout = 120        # BioBERT inference can be slow on first request
keepalive = 5
preload_app = True   # Load BioBERT model ONCE in master; workers inherit via Linux fork COW.
                     # WARNING: incompatible with --reload; never use --reload in production.
max_requests = 500   # Restart workers periodically to prevent memory fragmentation
max_requests_jitter = 50  # Stagger restarts to avoid thundering herd
accesslog = "-"   # stdout — captured by docker logs
errorlog = "-"    # stderr — captured by docker logs
loglevel = "info"
