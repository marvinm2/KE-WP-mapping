# External Integrations

**Analysis Date:** 2026-02-19

## APIs & External Services

**SPARQL Endpoints (Knowledge Graphs):**
- AOP-Wiki SPARQL - Gene extraction from Key Events
  - Endpoint: `https://aopwiki.rdf.bigcat-bioinformatics.org/sparql`
  - Used by: `src/suggestions/ke_genes.py` (extract genes from KE IDs)
  - Used by: `src/suggestions/pathway.py`, `src/suggestions/go.py` (via get_genes_from_ke)
  - Method: POST requests with SPARQL queries
  - Caching: Results cached in SQLite `sparql_cache` table (24-hour TTL)
  - SDK/Client: `requests` library

- WikiPathways SPARQL - Pathway-gene relationships
  - Endpoint: `https://sparql.wikipathways.org/sparql`
  - Used by: `src/suggestions/pathway.py` (find pathways containing genes)
  - Method: POST with SPARQL PREFIX queries
  - Caching: Results cached (24-hour TTL via `CacheModel`)
  - SDK/Client: `requests` library

**Authentication & OAuth:**
- GitHub OAuth 2.0
  - Provider: GitHub (`https://github.com/login/oauth/`)
  - Config: `src/services/container.py` (OAuth initialization)
  - Blueprint: `src/blueprints/auth.py` (login/callback flows)
  - Scope: `user:email` (read user email)
  - Access Token URL: `https://github.com/login/oauth/access_token`
  - Authorize URL: `https://github.com/login/oauth/authorize`
  - API Base: `https://api.github.com/`
  - Credentials:
    - `GITHUB_CLIENT_ID` env var
    - `GITHUB_CLIENT_SECRET` env var
  - Used for: User authentication, session management
  - Library: `authlib` (Flask integration)

## Data Storage

**Databases:**
- SQLite (file-based, embedded)
  - Location: `ke_wp_mapping.db` (default, configurable via `DATABASE_PATH` env var)
  - Connection: Python `sqlite3` module (built-in)
  - Models: `src/core/models.py`
  - Tables:
    - `mappings` - KE-WP associations (id, ke_id, wp_id, confidence, connection_type)
    - `proposals` - User-submitted changes/deletions to mappings
    - `ke_go_mappings` - KE-GO associations
    - `ke_go_proposals` - User proposals for GO mappings
    - `sparql_cache` - Cached SPARQL query responses (24h TTL)
    - `guest_codes` - Workshop guest access codes
  - Initialization: Auto-migration on app startup (`Database.init_db()`)
  - Testing: In-memory database (`:memory:`) for test suite

**File Storage:**
- Local filesystem only
  - Pre-computed embeddings: `data/*.npy` (NumPy binary format)
  - Metadata: `data/*.json` (GO, KE, pathway term definitions)
  - Embeddings loaded once at app startup via `BiologicalEmbeddingService`
  - Database file: `ke_wp_mapping.db` (SQLite)
  - No cloud storage (S3, GCS, etc.)

**Caching:**
- SQLite `sparql_cache` table
  - Stores SPARQL query results with 24-hour expiration
  - Keyed by `endpoint` + `query_hash` (UNIQUE constraint)
  - Avoids redundant external API calls
  - Clearable via: `sqlite3 ke_wp_mapping.db "DELETE FROM sparql_cache;"`

- In-memory LRU caches
  - BioBERT embedding cache (1000 items, recent encodings)
  - Service container singleton pattern (metrics, models)

## Authentication & Identity

**Auth Provider:**
- GitHub OAuth 2.0 (via Authlib)
  - Implementation: `src/blueprints/auth.py`
  - Login flow: `/login` → authorize → `/callback` → session
  - Endpoints:
    - `GET /login` - Initiate OAuth
    - `GET /callback` - OAuth callback from GitHub
    - `GET /logout` - Clear session
  - Session storage: Flask session (server-side)
  - User data stored:
    - `username` (GitHub login)
    - `email` (from GitHub API)
    - `is_guest` (workshop access flag)

- Admin Access
  - Role-based: `ADMIN_USERS` env var (comma-separated GitHub usernames)
  - Check: Context processor `is_admin` available in all templates
  - Used for: Proposal review, access to admin dashboard

- Guest Access (Workshop Mode)
  - Feature: `src/blueprints/auth.py` (guest code validation)
  - Model: `GuestCodeModel` (database of guest codes)
  - Codes: Admin-generated, expiring, limited uses
  - Used for: Workshop participants without GitHub accounts

## Monitoring & Observability

**Error Tracking:**
- Not detected - No Sentry, Rollbar, or similar integration
- Internal error handling: `src/core/error_handlers.py` (ApplicationError base class)
- Logging to console/files via Python `logging` module

**Logs:**
- Standard Python logging
  - Level: INFO (production), DEBUG (development)
  - Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
  - Output: Console (stdout)
  - Files: `logs/` directory (created in Docker, if needed)
  - No centralized log aggregation (ELK, CloudWatch, etc.)

**Metrics:**
- Internal metrics collection: `src/services/monitoring.py`
  - `MetricsCollector` class
  - Tracks endpoint performance, request counts, response times
  - Exposed via `/metrics` and `/metrics/<endpoint_name>` endpoints
  - Stored in SQLite (separate table pattern)

**Health Check:**
- `GET /health` endpoint
  - Returns: `{"status": "healthy|degraded|unhealthy", "timestamp": ..., "version": "2.0.0", "services": {...}}`
  - Checks: Database connectivity, OAuth config, service availability
  - Docker HEALTHCHECK: `curl -f http://localhost:5000/health` (30s interval, 120s timeout)

## CI/CD & Deployment

**Hosting:**
- Docker containerization (Dockerfile, docker-compose.yml)
  - Base: `python:3.12-slim-bookworm`
  - Runtime user: `appuser` (non-root for security)
  - Exposed port: 5000
  - Orchestration: Gunicorn (4 workers, sync, 120s timeout)
  - Volumes: Mount for SQLite database, data/, logs/ (if needed)

**CI Pipeline:**
- Not detected - No GitHub Actions, GitLab CI, or Jenkins
- Testing: Manual via `make test`, `pytest`
- Linting: Manual via `make lint` (placeholder)

**Package Distribution:**
- No package registry (PyPI, etc.)
- Dependency pinning: requirements.txt versions locked

## Environment Configuration

**Required env vars (production must-haves):**
- `FLASK_SECRET_KEY` - Session encryption key (validated at startup)
- `GITHUB_CLIENT_ID` - OAuth client ID (validated at startup)
- `GITHUB_CLIENT_SECRET` - OAuth client secret (validated at startup)
- `DATABASE_PATH` - Path to SQLite database (default: `ke_wp_mapping.db`)
- `ADMIN_USERS` - Comma-separated admin GitHub usernames (default: empty)

**Optional env vars:**
- `FLASK_ENV` - `development|production|testing` (default: development)
- `FLASK_DEBUG` - Debug mode `true|false` (default: false)
- `PORT` - Server port (default: 5000)
- `HOST` - Bind address (default: 127.0.0.1)
- `RATELIMIT_STORAGE_URL` - Rate limit backend (default: `memory://`)

**Secrets location:**
- `.env` file (local development, not committed)
- Environment variables (production deployments)
- Docker secrets/env file at runtime

## Webhooks & Callbacks

**Incoming Webhooks:**
- Not detected - No GitHub webhooks, external event triggers

**Outgoing Webhooks:**
- Not detected - No outbound notifications to Slack, Teams, etc.

**OAuth Callbacks:**
- GitHub OAuth callback: `GET /callback` (Flask auth blueprint)
  - Receives `code` and `state` from GitHub
  - Exchanges code for access token
  - Fetches user info and email
  - Stores in session

---

*Integration audit: 2026-02-19*
