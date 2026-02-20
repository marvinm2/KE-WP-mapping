# gunicorn.conf.py
# Gunicorn configuration for KE-WP Mapping application.
# Source: https://gunicorn.org/reference/settings
#
# Worker count: start with 2 (conservative for BioBERT ~440MB model).
# After deployment, measure with `docker stats ke-wp-mapping-web-1`.
# Increase to 3 or 4 if total RAM stays under 4GB.

bind = "0.0.0.0:5000"
workers = 2          # Each marginal worker adds ~80MB overhead (model shared via fork COW)
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
