---
phase: 01-deployment-hardening
plan: 01
subsystem: database
tags: [sqlite, wal, docker, database-path, concurrent-writes]

# Dependency graph
requires: []
provides:
  - Docker-safe absolute DATABASE_PATH default (/app/data/ke_wp_mapping.db)
  - SQLite WAL mode on every connection (PRAGMA journal_mode=WAL)
  - SQLite busy timeout 5000ms (PRAGMA busy_timeout=5000)
  - NORMAL synchronous mode for WAL durability/performance balance
affects: [02-data-integrity, 03-public-api, all-phases-using-database]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SQLite WAL mode: set via PRAGMA on every get_connection() call — idempotent, safe to repeat"
    - "Docker volume path: /app/data/ prefix for all persistent data files"

key-files:
  created: []
  modified:
    - src/core/config.py
    - src/core/models.py
    - tests/conftest.py

key-decisions:
  - "DATABASE_PATH default is /app/data/ke_wp_mapping.db — must match Docker volume mount point"
  - "WAL mode set via PRAGMA on every connection (not once at DB creation) — idempotent and ensures mode survives reconnects"
  - "busy_timeout=5000ms SQLite-level + timeout=30 Python-level — two-layer protection against lock contention"
  - "FLASK_ENV must be set before app import in conftest to prevent module-level create_app() using wrong config"

patterns-established:
  - "Database connection pattern: connect with timeout=30, then apply WAL/synchronous/busy_timeout PRAGMAs before returning conn"
  - "Test environment bootstrap: set FLASK_ENV=testing before importing app module to avoid module-level instantiation with prod config"

requirements-completed: [DEPLOY-01]

# Metrics
duration: 12min
completed: 2026-02-19
---

# Phase 1 Plan 01: Database Path and WAL Mode Summary

**SQLite WAL mode with 5s busy timeout enabled on every connection and DATABASE_PATH fixed to /app/data/ke_wp_mapping.db for Docker volume persistence**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-19T00:00:00Z
- **Completed:** 2026-02-19T00:12:00Z
- **Tasks:** 2 (+ 1 auto-fix deviation)
- **Files modified:** 3

## Accomplishments
- DATABASE_PATH default changed from relative `ke_wp_mapping.db` to absolute `/app/data/ke_wp_mapping.db`, preventing data loss on container recreation
- DATABASE_URL updated to four-slash SQLite URI `sqlite:////app/data/ke_wp_mapping.db` for ORM compatibility
- WAL journal mode, NORMAL synchronous, and 5000ms busy timeout applied on every `Database.get_connection()` call — eliminates "database is locked" errors under concurrent curator writes
- All 45 tests pass; TestingConfig `:memory:` override untouched

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix DATABASE_PATH default** - `a5e203e` (fix)
2. **Task 2: Enable WAL mode and busy timeout** - `8ca58ed` (fix)
3. **Deviation: Fix conftest FLASK_ENV before import** - `82bfeb9` (fix)

**Plan metadata:** (docs commit — see Final Commit below)

## Files Created/Modified
- `src/core/config.py` - DATABASE_URL and DATABASE_PATH defaults changed to /app/data/ absolute paths
- `src/core/models.py` - get_connection() now applies WAL/synchronous/busy_timeout PRAGMAs on every connection
- `tests/conftest.py` - FLASK_ENV=testing set before app import to use TestingConfig at module load time

## Decisions Made
- WAL PRAGMAs are applied on every connection call (not once at DB init) — idempotent and guarantees mode is active regardless of connection origin
- Two-layer timeout: `timeout=30` in `sqlite3.connect()` (Python retry) + `PRAGMA busy_timeout=5000` (SQLite-level wait) for belt-and-suspenders protection
- `os.environ.setdefault()` used in conftest (not `os.environ[]=`) to avoid overriding values already set by the test runner environment

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test suite failure caused by module-level app instantiation with wrong config**
- **Found during:** Overall verification (pytest run after Task 2)
- **Issue:** `app.py:196` executes `app = create_app()` at module import time. Before this plan, the relative path `ke_wp_mapping.db` was created silently in the cwd. After changing to `/app/data/ke_wp_mapping.db`, SQLite raised `unable to open database file` because `/app/data/` does not exist in the dev/test environment. The conftest set env vars inside fixture bodies — too late, after the module-level import had already run with dev config.
- **Fix:** Added `os.environ.setdefault("FLASK_ENV", "testing")` (plus OAuth env vars) before `from app import app` in `tests/conftest.py`. This ensures `create_app()` at module level uses `TestingConfig` with `DATABASE_PATH=":memory:"`.
- **Files modified:** `tests/conftest.py`
- **Verification:** All 45 tests pass after fix
- **Committed in:** `82bfeb9` (separate fix commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - latent bug exposed by correct absolute path)
**Impact on plan:** The auto-fix was necessary for the test suite to pass. The underlying bug (conftest importing app before setting FLASK_ENV) was always present but hidden by the relative path behavior. No scope creep.

## Issues Encountered
- Coverage threshold (80%) fails at 36% — pre-existing project condition unrelated to this plan. All 45 functional tests pass.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Database is now safe for Docker deployment: path mounts correctly as a volume, WAL mode handles concurrent curator writes
- TestingConfig `:memory:` path confirmed working with proper conftest bootstrap
- Phase 2 (data integrity) can proceed — schema additions will go through the same hardened `get_connection()` path

---
*Phase: 01-deployment-hardening*
*Completed: 2026-02-19*

## Self-Check: PASSED

- FOUND: src/core/config.py
- FOUND: src/core/models.py
- FOUND: tests/conftest.py
- FOUND: .planning/phases/01-deployment-hardening/01-01-SUMMARY.md
- FOUND commit a5e203e: fix(01-01): change DATABASE_PATH default to Docker-safe absolute path
- FOUND commit 8ca58ed: fix(01-01): enable SQLite WAL mode and busy timeout on every connection
- FOUND commit 82bfeb9: fix(01-01): set FLASK_ENV=testing before app import in conftest
