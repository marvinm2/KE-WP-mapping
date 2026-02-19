---
phase: 01-deployment-hardening
plan: "02"
subsystem: infra
tags: [docker, gunicorn, sqlite, cron, backup]

requires: []
provides:
  - Working docker-compose.yml with only the web service, env_file directive, and backups volume
  - gunicorn.conf.py with preload_app=True and 2-worker conservative config for BioBERT memory safety
  - scripts/backup_db.sh using sqlite3 Online Backup API with integrity check and 7-day retention
  - scripts/docker-entrypoint.sh that starts cron then exec's gunicorn for correct signal handling
  - scripts/ke-wp-backup crontab file for daily 02:00 backup
affects:
  - 01-deployment-hardening (subsequent plans building on this container foundation)
  - All future phases that deploy or test via Docker

tech-stack:
  added: [gunicorn-conf-file, sqlite3-online-backup-api, cron]
  patterns:
    - "preload_app=True pattern: load BioBERT once in master process, workers inherit via Linux fork COW"
    - "Docker entrypoint exec pattern: run sidecar (cron) then exec main process to preserve PID 1 signal handling"
    - "env_file directive: secrets loaded from host .env, not hardcoded in docker-compose.yml"
    - "sqlite3 .backup: always use Online Backup API for consistent snapshots during active writes"

key-files:
  created:
    - gunicorn.conf.py
    - scripts/backup_db.sh
    - scripts/docker-entrypoint.sh
    - scripts/ke-wp-backup
  modified:
    - docker-compose.yml
    - Dockerfile

key-decisions:
  - "Start with 2 Gunicorn workers (not 4) — conservative for BioBERT ~440MB model; scale up after measuring docker stats"
  - "Use appuser in cron.d entry (not root) — appuser owns /app/data and /app/logs"
  - "HEALTHCHECK start-period increased from 20s to 60s — BioBERT preload_app=True takes ~30-40s at startup"
  - "Retain backups for 7 days — balances storage cost against recovery window before external curators submit data"

patterns-established:
  - "exec $@ in entrypoint: ensures CMD process gets PID 1 and receives Docker SIGTERM correctly"

requirements-completed:
  - DEPLOY-03

duration: 1min
completed: 2026-02-19
---

# Phase 1 Plan 2: Docker Hardening and Backup System Summary

**Cleaned docker-compose.yml (removed dead redis/nginx services), version-controlled gunicorn.conf.py with preload_app=True for BioBERT memory sharing, and container-internal cron backup using sqlite3 Online Backup API with integrity check and 7-day retention.**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-19T21:36:58Z
- **Completed:** 2026-02-19T21:38:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Removed non-functional redis and nginx service blocks from docker-compose.yml (neither existed in the codebase — nginx had no config file, redis was unused); container can now start
- Created version-controlled gunicorn.conf.py with preload_app=True so BioBERT loads once in the master process and workers inherit the model via Linux fork copy-on-write (~80MB overhead per extra worker instead of ~440MB)
- Implemented daily SQLite backup using the Online Backup API (`.backup` command) which creates a consistent snapshot even during active writes, with integrity check and 7-day rolling retention
- Wired Dockerfile to use entrypoint script that starts cron then exec's gunicorn, ensuring Docker SIGTERM reaches gunicorn correctly

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix docker-compose.yml and create gunicorn.conf.py** - `6105100` (chore)
2. **Task 2: Create backup script, entrypoint, and update Dockerfile** - `eceacfc` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified

- `docker-compose.yml` - Replaced: removed redis/nginx services, replaced environment: with env_file: .env, added backups volume mount
- `gunicorn.conf.py` - Created: version-controlled Gunicorn config with preload_app=True, workers=2, 120s timeout, rotating log paths
- `scripts/backup_db.sh` - Created: SQLite Online Backup API backup script with integrity check and 7-day retention pruning
- `scripts/docker-entrypoint.sh` - Created: starts cron daemon then exec's CMD (gunicorn) for correct PID 1 signal handling
- `scripts/ke-wp-backup` - Created: cron.d file scheduling daily backup at 02:00 as appuser
- `Dockerfile` - Updated: added cron to apt-get, mkdir logs and backups, chmod scripts, ENTRYPOINT and CMD updated, HEALTHCHECK start-period 20s -> 60s

## Decisions Made

- **2 Gunicorn workers, not 4:** The existing Dockerfile had 4 workers inline. Research showed BioBERT is ~440MB — with preload_app=True, marginal cost per worker is ~80MB (fork COW sharing), so 4 workers is ~800MB on top of the model. Conservative start at 2 workers; scale after measuring with `docker stats`.
- **appuser in crontab:** The cron.d file uses `appuser` as the cron user (not root) because appuser owns /app/data and /app/logs — the backup script writes to both.
- **HEALTHCHECK start-period 60s:** BioBERT loads during master process startup with preload_app=True, typically 30-40s. 20s was too short and would cause false health failures on cold start.
- **7-day backup retention:** Sufficient recovery window before external curators begin submitting data (DEPLOY-03 prerequisite).

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required beyond the existing .env file.

## Next Phase Readiness

- Docker deployment foundation is complete and functional
- The container can now start (dead services removed), will load BioBERT efficiently (preload_app=True), and will back up the database daily
- Next step: database path hardening (move ke_wp_mapping.db to /app/data/ mount point — DEPLOY-01 blocker documented in STATE.md)
- Before deploying: ensure ./backups/ directory exists on host (Docker will create it but permissions should be checked)

---
*Phase: 01-deployment-hardening*
*Completed: 2026-02-19*

## Self-Check: PASSED

- FOUND: docker-compose.yml
- FOUND: gunicorn.conf.py
- FOUND: scripts/backup_db.sh
- FOUND: scripts/docker-entrypoint.sh
- FOUND: scripts/ke-wp-backup
- FOUND: .planning/phases/01-deployment-hardening/01-02-SUMMARY.md
- FOUND: commit 6105100 (Task 1)
- FOUND: commit eceacfc (Task 2)
