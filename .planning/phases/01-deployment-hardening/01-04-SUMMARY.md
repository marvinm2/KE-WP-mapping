---
phase: 01-deployment-hardening
plan: 04
subsystem: infra
tags: [gunicorn, preload_app, biobert, embedding, warmup, flask]

# Dependency graph
requires:
  - plan: 01-03
    provides: "NPZ embedding file format; ServiceContainer.embedding_service lazy property wired to BioBERT loader"
  - plan: 01-02
    provides: "gunicorn.conf.py with preload_app=True enabling master-process model loading"
provides:
  - "Module-level production-guarded embedding warm-up call in app.py"
  - "BioBERT loads in Gunicorn master process before workers fork when FLASK_ENV=production"
  - "Non-fatal guard: warm-up failure does not prevent app startup"
affects:
  - "Production deployment: FLASK_ENV must be set to 'production' in Docker env to activate warm-up"
  - "Test suite: FLASK_ENV=testing (set by TestingConfig) prevents warm-up from firing"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level warm-up pattern: access lazy service after create_app() guarded by FLASK_ENV=production"
    - "Non-fatal warm-up: try/except wraps the service access so startup failure does not prevent app from running"
    - "Underscore-prefixed temps: _svc and _e minimize module namespace pollution"

key-files:
  created: []
  modified:
    - app.py

key-decisions:
  - "Guard warm-up with os.getenv('FLASK_ENV') == 'production' — prevents BioBERT load during pytest (FLASK_ENV=testing) and plain python app.py (FLASK_ENV defaults to development)"
  - "Use try/except Exception so warm-up failure is non-fatal — workers lazy-load BioBERT on first request if master-process preload fails"
  - "Access embedding_service property directly (not call a method) — ServiceContainer.embedding_service is a lazy @property that loads BioBERT on first access"

patterns-established:
  - "Gunicorn preload chain: preload_app=True in gunicorn.conf.py + FLASK_ENV=production warm-up in app.py = single BioBERT load in master, shared across workers via copy-on-write fork"

requirements-completed:
  - DEPLOY-02
  - DEPLOY-04

# Metrics
duration: 2min
completed: 2026-02-19
---

# Phase 01 Plan 04: Embedding Warm-up Summary

**Production-guarded module-level warm-up call in app.py forces BioBERT to load in the Gunicorn master process before workers fork, completing the preload_app=True memory-sharing chain**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-19T21:44:15Z
- **Completed:** 2026-02-19T21:45:50Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added warm-up block in app.py after `app = create_app()` that accesses `app.service_container.embedding_service`
- Guarded by `if os.getenv("FLASK_ENV") == "production"` — BioBERT does not load during tests or dev server startup
- Wrapped in try/except so a warm-up failure (missing embedding files, insufficient memory) is non-fatal
- All 45 existing tests continue to pass with FLASK_ENV=testing bypassing the warm-up guard

## Task Commits

Each task was committed atomically:

1. **Task 1: Add production-guarded embedding warm-up call in app.py** - `12c3eea` (feat)

**Plan metadata:** (final docs commit — see below)

## Files Created/Modified

- `app.py` — Added 13-line warm-up block between `app = create_app()` and the `if __name__ == "__main__"` block; guard prevents BioBERT from loading in non-production environments

## Decisions Made

- **FLASK_ENV guard over TESTING flag:** Using `os.getenv("FLASK_ENV") == "production"` is simpler and more explicit than checking `app.config.get("TESTING")`. The value must be set in the Docker environment (already required for other production settings).
- **try/except Exception scope:** Catches all exceptions (not just specific ones) because warm-up failure modes are varied (missing files, OOM, config errors) and all are non-fatal — the app can start and workers will lazy-load BioBERT on first request.
- **No new imports required:** `os` and `logger` are already defined at module level in app.py, so the warm-up block adds no new import overhead.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. The verification checks all passed on the first attempt:
- `grep -n "FLASK_ENV.*production|embedding_service|preload"` confirmed the block is present at the correct location
- `FLASK_ENV=testing python -c "from src.core.config import TestingConfig; ..."` confirmed clean import
- Guard logic check confirmed warm-up does not fire in testing
- Full test suite: 45 tests passed (coverage at 36% is a pre-existing condition unrelated to this plan)

## User Setup Required

No new setup required for this plan. However, the combined effect of Plans 01-02, 01-03, and 01-04 requires:

1. **Regenerate embedding files in NPZ format** (from Plan 03 — old .npy files will not load):
   ```bash
   python scripts/precompute_ke_embeddings.py
   python scripts/precompute_pathway_title_embeddings.py
   python scripts/precompute_go_embeddings.py
   python scripts/precompute_pathway_embeddings.py
   ```
2. **Set FLASK_ENV=production in production Docker environment** — this activates the warm-up call and triggers BioBERT preloading in the Gunicorn master before workers fork.

## Next Phase Readiness

- Phase 1 Deployment Hardening is complete: Docker hardening (01-02), NPZ embedding migration (01-03), and Gunicorn preload chain (01-04) are all in place.
- The preload chain is only effective after embedding files are regenerated as NPZ (see User Setup above).
- Phase 2 can proceed once embedding files on disk are confirmed working in the production environment.

---
*Phase: 01-deployment-hardening*
*Completed: 2026-02-19*
