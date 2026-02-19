# Phase 1: Deployment Hardening - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the application production-safe before any external curator submits data — database survives container recreation, memory stays within bounds, concurrent curator writes do not corrupt data, and embedding files load reliably without pickle. This phase covers infrastructure and configuration only; no user-facing feature changes.

</domain>

<decisions>
## Implementation Decisions

### Deployment target
- Self-hosted VPS with Docker Compose — existing `Dockerfile` and `docker-compose.yml` are modified, not created from scratch
- Database file lives at `/app/data/ke_wp_mapping.db` inside the container, mounted as a Docker volume from the host
- Environment secrets (GitHub OAuth, Flask secret key) managed via a `.env` file on the host, loaded via Docker Compose `env_file` directive

### Backup strategy
- Backups stored to a local directory on the VPS (not cloud storage)
- Backup triggered by a cron job inside the container (container-internal scheduling)
- Use SQLite's online backup API (`sqlite3 .backup`) for consistent snapshots safe to run during active writes
- Backup frequency and retention: Claude's discretion (pick a sensible default for a small research database)

### Embedding migration
- No existing production data to protect — regenerate all embedding files from scratch
- Update precompute scripts (`scripts/precompute_*.py`) to output NPZ format directly; no separate one-time migration script needed
- Old `.npy` pickle files deleted once NPZ format confirmed working in the new deployment
- Normalization happens at precompute time only — trust the scripts; no load-time assertion needed
- The `data/` directory (embedding files) mounted as a Docker volume from the host, not baked into the image

### Worker memory model
- Target: 4 Gunicorn workers if memory allows (aspirational, not a hard constraint — adjust based on BioBERT's actual footprint)
- Model sharing: `preload_app=True` in Gunicorn config — model loaded once in master process, inherited by workers via fork
- Gunicorn configuration in a `gunicorn.conf.py` file committed to the repo (version-controlled, not inline in docker-compose)
- SQLite WAL mode set via application startup code (`PRAGMA wal_mode=WAL` on each connection) — idempotent and ensures WAL regardless of database origin

### Claude's Discretion
- Backup frequency and retention policy (e.g. daily backups, keep 7 days)
- Worker count if BioBERT footprint makes 4 workers exceed available RAM
- Connection pool size for SQLite WAL mode

</decisions>

<specifics>
## Specific Ideas

- The STATE.md blocker explicitly notes: database path must be `/app/data/ke_wp_mapping.db` and mounted as a Docker volume — this is a firm path, not a convention
- `gunicorn.conf.py` should be discoverable and clear for ops — not buried in a startup script

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-deployment-hardening*
*Context gathered: 2026-02-19*
