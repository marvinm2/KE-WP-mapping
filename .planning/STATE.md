# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.
**Current focus:** Phase 1 — Deployment Hardening

## Current Position

Phase: 1 of 6 (Deployment Hardening)
Plan: 4 of 4 in current phase
Status: In progress
Last activity: 2026-02-19 — Completed 01-04 (Gunicorn preload warm-up call)

Progress: [██░░░░░░░░] 15%

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: 5 min
- Total execution time: 0.33 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-deployment-hardening | 4 | 20 min | 5 min |

**Recent Trend:**
- Last 5 plans: 01-02 (1 min), 01-03 (5 min), 01-04 (2 min)
- Trend: Phase 1 complete

*Updated after each plan completion*
| Phase 01-deployment-hardening P01 | 12 | 2 tasks | 3 files |
| Phase 01-deployment-hardening P03 | 5 | 2 tasks | 8 files |
| Phase 01-deployment-hardening P04 | 2 | 1 task | 1 file |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Research]: Dual-Blueprint split — keep existing `api_bp` for UI-internal endpoints; new `v1_api_bp` with `/api/v1` prefix for the stable public API
- [Research]: Phase 1 (deployment) must precede all other work; data loss and memory blow-up are irreversible and block curator onboarding
- [Research]: Data provenance columns (CURAT-01, EXPLO-04) must be added in Phase 2 before any curation feeds publication figures
- [01-02]: Start with 2 Gunicorn workers (not 4) — conservative for BioBERT ~440MB model; scale up after measuring docker stats
- [01-02]: HEALTHCHECK start-period increased from 20s to 60s — BioBERT preload_app=True takes ~30-40s at startup
- [01-02]: Use appuser in crontab (not root) — appuser owns /app/data and /app/logs where backup writes
- [01-02]: Retain backups for 7 days — balances storage cost against recovery window before external curators submit data
- [Phase 01-deployment-hardening]: DATABASE_PATH default is /app/data/ke_wp_mapping.db — must match Docker volume mount point
- [Phase 01-deployment-hardening]: WAL mode set via PRAGMA on every connection (not once at DB creation) — idempotent and ensures mode survives reconnects
- [Phase 01-deployment-hardening]: FLASK_ENV must be set before app import in conftest to prevent module-level create_app() using wrong config
- [Phase 01-deployment-hardening]: NPZ matrix format with pre-normalized vectors: eliminates pickle deserialization risk; dot product equals cosine similarity after unit normalization at save time
- [01-04]: Guard warm-up with FLASK_ENV=production — prevents BioBERT load during pytest (FLASK_ENV=testing) and plain python app.py (FLASK_ENV defaults to development)
- [01-04]: try/except wraps warm-up so startup failure is non-fatal — workers still lazy-load BioBERT on first request if master-process preload fails

### Pending Todos

None yet.

### Blockers/Concerns

- [Pre-Phase 1]: Database path must be changed to `/app/data/ke_wp_mapping.db` and mounted as a Docker volume before any external user submits data — data loss risk is irreversible
- [Pre-Phase 2]: Verify whether `curator_github` is already stored at approval time in `src/blueprints/admin.py` before designing Phase 2 schema additions
- [Pre-Phase 4]: Explore filter by `aop_id` requires a design decision — pre-compute AOP membership into the database (preferred) vs. live SPARQL join per request

## Session Continuity

**Last session:** 2026-02-19T21:45:50Z
**Stopped at:** Completed 01-deployment-hardening-04-PLAN.md (Phase 1 complete)
**Resume file:** None
