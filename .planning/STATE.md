# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.
**Current focus:** Phase 1 — Deployment Hardening

## Current Position

Phase: 1 of 6 (Deployment Hardening)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-02-19 — Roadmap created; all 25 v1 requirements mapped across 6 phases

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Research]: Dual-Blueprint split — keep existing `api_bp` for UI-internal endpoints; new `v1_api_bp` with `/api/v1` prefix for the stable public API
- [Research]: Phase 1 (deployment) must precede all other work; data loss and memory blow-up are irreversible and block curator onboarding
- [Research]: Data provenance columns (CURAT-01, EXPLO-04) must be added in Phase 2 before any curation feeds publication figures

### Pending Todos

None yet.

### Blockers/Concerns

- [Pre-Phase 1]: Database path must be changed to `/app/data/ke_wp_mapping.db` and mounted as a Docker volume before any external user submits data — data loss risk is irreversible
- [Pre-Phase 2]: Verify whether `curator_github` is already stored at approval time in `src/blueprints/admin.py` before designing Phase 2 schema additions
- [Pre-Phase 4]: Explore filter by `aop_id` requires a design decision — pre-compute AOP membership into the database (preferred) vs. live SPARQL join per request

## Session Continuity

Last session: 2026-02-19
Stopped at: Roadmap and STATE.md written; REQUIREMENTS.md traceability updated; ready to plan Phase 1
Resume file: None
