---
phase: 03-stable-public-rest-api
plan: 03
subsystem: testing
tags: [pytest, flask-test-client, v1-api, tdd, sqlite, content-negotiation, cors, pagination]

# Dependency graph
requires:
  - phase: 03-stable-public-rest-api
    plan: 02
    provides: "v1_api_bp blueprint with six public endpoints, CORS, CSV/JSON negotiation, AOP filter"
provides:
  - "pytest test suite for /api/v1/ blueprint (19 tests, all green)"
  - "v1_client fixture that re-wires v1_api module-level models to a fresh temp-file DB per test"
  - "Regression coverage for all Phase 3 success criteria"
affects:
  - future-phases
  - 03-stable-public-rest-api

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "v1_client fixture injects fresh MappingModel/GoMappingModel into v1_api module-level singletons per test, avoiding in-memory SQLite connection isolation issues"
    - "Seed helpers as module-level functions (not fixtures) receiving model instances directly"
    - "monkeypatch on module function reference (v1_mod._resolve_aop_ke_ids) for AOP error path"

key-files:
  created:
    - tests/test_v1_api.py
  modified: []

key-decisions:
  - "v1_client fixture calls v1_mod.set_models() with fresh temp-file DB models — required because TestingConfig uses :memory: which creates separate DB per sqlite3.connect() call, making module-level models unable to share state with seeded data"
  - "Seed helpers take model instances as arguments rather than reading from flask_app.service_container — cleaner coupling, avoids cross-test contamination from shared in-memory DB"
  - "Tests restore original module-level models after each test to avoid polluting other test classes that use conftest.py client fixture"

patterns-established:
  - "Re-inject blueprint module-level models for integration tests when blueprint uses set_models() injection pattern"
  - "Per-test DB isolation via fresh Database(temp_file) + set_models() restore in fixture teardown"

requirements-completed: [API-01, API-02, API-03, API-04]

# Metrics
duration: 10min
completed: 2026-02-20
---

# Phase 3 Plan 03: v1 Public REST API Test Suite Summary

**19-test pytest suite for /api/v1/ blueprint using per-test temp-file DB injection to isolate SQLite :memory: connection issues**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-20T22:12:47Z
- **Completed:** 2026-02-20T22:22:49Z
- **Tasks:** 1 (TDD: RED + GREEN in single implementation pass)
- **Files modified:** 1

## Accomplishments
- 19 tests covering all four v1 route groups: list/get KE-WP mappings, list/get KE-GO mappings
- JSON envelope shape assertions, CSV content negotiation, CORS headers, pagination clamping
- Filter param tests (ke_id, pathway_id, confidence_level reduce result set correctly)
- UUID 404 paths for both /mappings/<uuid> and /go-mappings/<uuid>
- AOP filter 400 path via monkeypatching _resolve_aop_ke_ids
- Discovered and resolved SQLite :memory: per-connection isolation issue with v1_client fixture

## Task Commits

Each task was committed atomically:

1. **Task 1: v1 API test suite (TDD GREEN)** - `f82c1b6` (feat)

**Plan metadata:** (docs commit to follow)

_Note: RED phase confirmed 17 of 19 tests failing as expected before infrastructure fix._

## Files Created/Modified
- `tests/test_v1_api.py` - 19-test suite for /api/v1/ with v1_client fixture and seed helpers

## Decisions Made
- **v1_client fixture re-wires module-level models:** TestingConfig uses `DATABASE_PATH = ":memory:"`, and SQLite in-memory databases create a new, empty DB per `sqlite3.connect(":memory:")` call. This means the module-level `mapping_model` (set once at create_app() time) always gets a fresh empty DB on each query. Fixed by creating a temp-file Database and calling `v1_mod.set_models()` in the fixture, then restoring originals in teardown.
- **Seed helpers take model instances, not flask_app.service_container:** Cleaner isolation — each test's seed helper uses the same DB the HTTP routes are hitting, without relying on global app state.
- **Used monkeypatch for AOP ValueError test:** `monkeypatch.setattr(v1_mod, "_resolve_aop_ke_ids", raises_fn)` is cleaner than `unittest.mock.patch` for this case; matches the plan's recommended pattern.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed SQLite :memory: per-connection isolation causing "no such table" errors**
- **Found during:** Task 1 (writing and running test stubs - RED phase)
- **Issue:** `TestingConfig.DATABASE_PATH = ":memory:"` means each `sqlite3.connect(":memory:")` call returns a separate, empty database. The module-level models in v1_api.py are initialized once at create_app() time with one in-memory connection, but subsequent query calls open new connections to empty DBs. Result: every HTTP call to v1_api routes got "no such table: mappings".
- **Fix:** Created `v1_client` pytest fixture that instantiates a fresh `Database(temp_file_path)` (which calls `init_db()` on creation), wires it into v1_api via `set_models()`, and restores originals in teardown.
- **Files modified:** tests/test_v1_api.py
- **Verification:** All 19 tests pass; 64 total tests pass.
- **Committed in:** f82c1b6

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test infrastructure)
**Impact on plan:** Fix was necessary for test correctness. No production code changes. No scope creep.

## Issues Encountered
- SQLite `:memory:` connection isolation: each `sqlite3.connect(":memory:")` opens a new, empty database. The service container's lazy initialization exacerbated this because the database singleton was created on first access during the test run, but subsequent connections within the same test opened new empty DBs. Resolved by using temp-file DB in the test fixture.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 3 complete: all three plans executed (schema migrations, v1_api_bp blueprint, integration tests)
- All Phase 3 success criteria validated by tests: JSON envelope, CSV negotiation, CORS scoping, pagination clamping, filter params, UUID 404s
- Phase 4 can proceed: public API is stable, regression-tested, and documented

## Self-Check: PASSED

- tests/test_v1_api.py: FOUND
- .planning/phases/03-stable-public-rest-api/03-03-SUMMARY.md: FOUND
- Commit f82c1b6: FOUND
- All 19 new tests: PASSED
- All 64 total tests: PASSED

---
*Phase: 03-stable-public-rest-api*
*Completed: 2026-02-20*
