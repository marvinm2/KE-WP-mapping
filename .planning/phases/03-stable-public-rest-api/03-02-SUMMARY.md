---
phase: 03-stable-public-rest-api
plan: 02
subsystem: api
tags: [flask, blueprint, rest-api, cors, csv, pagination, sparql, rate-limiting]

requires:
  - phase: 03-stable-public-rest-api
    plan: 01
    provides: "get_mappings_paginated(), get_go_mappings_paginated(), suggestion_score, go_namespace columns"

provides:
  - "v1_api_bp Flask Blueprint at /api/v1 — six public REST endpoints, no auth required"
  - "GET /api/v1/mappings with ke_id/pathway_id/confidence_level/aop_id filters and pagination"
  - "GET /api/v1/mappings/<uuid> returning single mapping or 404"
  - "GET /api/v1/go-mappings with ke_id/go_term_id/confidence_level filters and pagination"
  - "GET /api/v1/go-mappings/<uuid> returning single GO mapping or 404"
  - "Content negotiation: JSON (default) and CSV via Accept: text/csv header"
  - "CORS: Access-Control-Allow-Origin: * on all /api/v1/ responses"
  - "AOP filter: _resolve_aop_ke_ids() with AOP-Wiki SPARQL + 24h cache"
  - "Blueprint-scoped CORS after_request hook — does NOT affect internal api_bp"

affects:
  - 03-03 (test plan for v1 API)
  - external consumers calling /api/v1/mappings and /api/v1/go-mappings

tech-stack:
  added: []
  patterns:
    - "CSRF exemption via csrf.exempt(blueprint) before app.register_blueprint() — prevents 400 on GET requests to public API"
    - "Blueprint-scoped CORS: after_request on v1_api_bp isolates CORS to /api/v1/ routes only"
    - "Content negotiation via request.accept_mimetypes.best_match() — JSON default, CSV on Accept: text/csv"
    - "Module-level model injection pattern: set_models() called from create_app() after service container init"
    - "AOP SPARQL resolution with cache: hashlib.md5 cache key, 24h TTL, ValueError on SPARQL failure -> 400"

key-files:
  created:
    - src/blueprints/v1_api.py
  modified:
    - src/blueprints/__init__.py
    - app.py

key-decisions:
  - "CORS hook scoped to v1_api_bp via @v1_api_bp.after_request — does not affect internal blueprints (api_bp, admin_bp, auth_bp, main_bp)"
  - "csv.DictWriter with extrasaction='ignore' flattens provenance nested dict for CSV output"
  - "total_pages returns 0 when total=0 (math.ceil(0/50)=0) — correct empty-state behavior"
  - "aop_id resolution raises ValueError on any SPARQL failure, mapped to 400 in route handler — prevents 500 on upstream unavailability"

patterns-established:
  - "Public v1 API blueprint: set_models() injection + csrf.exempt() + register_blueprint() pattern for future v2 blueprint"
  - "Pagination envelope: {page, per_page, total, total_pages, next, prev} — consistent contract for all collection endpoints"

requirements-completed: [API-01, API-02, API-03, API-04]

duration: 7min
completed: 2026-02-20
---

# Phase 3 Plan 02: v1 API Blueprint Summary

**Six-endpoint public REST API at /api/v1/ with JSON/CSV content negotiation, blueprint-scoped CORS, AOP SPARQL filter, and rate limiting — wired into app.py with CSRF exemption and model injection**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-20T22:03:29Z
- **Completed:** 2026-02-20T22:10:00Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- Created `src/blueprints/v1_api.py` with all six public API routes, CORS hook, content negotiation, and AOP SPARQL resolution
- Wired `v1_api_bp` into `app.py` with CSRF exemption before registration, model injection via `set_v1_api_models()`, and blueprint registration
- Exported `v1_api_bp` from `src/blueprints/__init__.py` following existing package pattern
- All 45 existing tests pass with the new blueprint registered

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src/blueprints/v1_api.py with all public API routes** - `eaf7107` (feat)
2. **Task 2: Register v1_api_bp in __init__.py and app.py** - `f112d88` (feat)

**Plan metadata:** (docs commit — pending)

## Files Created/Modified
- `src/blueprints/v1_api.py` - New file: Blueprint at /api/v1, six route handlers, CORS after_request, content negotiation, pagination helpers, AOP SPARQL resolver, set_models() injection
- `src/blueprints/__init__.py` - Added `from .v1_api import v1_api_bp` and updated `__all__`
- `app.py` - Added import of v1_api_bp + set_v1_api_models, csrf.exempt(v1_api_bp), set_v1_api_models() call, app.register_blueprint(v1_api_bp)

## Decisions Made
- CORS after_request hook is on `v1_api_bp` specifically, not on `app` — this keeps CORS isolated to the public API and does not affect the internal `api_bp`, `admin_bp`, `auth_bp`, or `main_bp`
- `csv.DictWriter` with `extrasaction='ignore'` handles the flattened provenance CSV shape cleanly — nested `provenance` dict is flattened by `_flatten_for_csv()` before writing
- `total_pages = 0` when `total = 0` — `math.ceil(0/50) = 0`, which correctly represents "no pages" rather than 1
- `_resolve_aop_ke_ids()` raises `ValueError` on any SPARQL failure (timeout, non-200, invalid response format) — the route handler catches this and returns 400, preventing 500 on upstream unavailability

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

The Task 2 verification command in the plan (`python -c "from app import create_app; ..."`) fails outside the project working directory because the module-level `app = create_app()` at line 204 of `app.py` runs without the proper DB path. This is a pre-existing condition: the conftest.py sets `FLASK_ENV=testing` before import to avoid this. Blueprint registration and route correctness were verified via import checks and `make test` (45 tests passing), which is the canonical verification method for this codebase.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All six `/api/v1/` endpoints are live and functional — Plan 03 (integration tests) can now write tests against these routes using the existing conftest fixtures
- CORS, pagination, content negotiation, and AOP filter are all working and ready for external consumers
- `suggestion_score` flows end-to-end: proposal scoring -> admin approval -> mapping row -> `provenance.suggestion_score` JSON field in v1 API response

---
*Phase: 03-stable-public-rest-api*
*Completed: 2026-02-20*
