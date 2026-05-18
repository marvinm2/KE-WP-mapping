# gunicorn.conf.py
# Gunicorn configuration for KE-WP Mapping application.
# Source: https://gunicorn.org/reference/settings
#
# Worker count: 3 workers for crash resilience. Session state (CSRF
# tokens, OAuth state) lives in the Flask signed session cookie, not
# server-side, so it is safe across workers. With preload_app=True the
# BioBERT model is loaded once in the master and shared via fork COW, so
# extra workers cost little memory. Trade-off: the in-memory rate limiter
# becomes per-worker (effective limits scale with worker count).

bind = "0.0.0.0:5000"
workers = 3          # 3 workers: a crashing worker no longer blanks the service
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
