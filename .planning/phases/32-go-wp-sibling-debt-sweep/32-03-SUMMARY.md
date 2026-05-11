---
phase: 32-go-wp-sibling-debt-sweep
plan: 03
subsystem: database
tags: [sqlite, partial-unique-index, race-condition, h2-port, wp-proposals, integrity-error]

requires:
  - phase: 25-reactome-suggestions-review-port
    provides: canonical H-2 partial-unique-index + DUPLICATE_PENDING sentinel template (ReactomeProposalModel)
provides:
  - "Partial-unique index idx_proposals_pending_pair on proposals(ke_id, wp_id) WHERE status='pending' AND mapping_id IS NULL"
  - "Pre-migration cleanup pass that auto-resolves legacy duplicate pending+new-pair rows (created_at ASC, id ASC keeper-selection)"
  - "ProposalModel.DUPLICATE_PENDING sentinel + sqlite3.IntegrityError branch in create_new_pair_proposal"
  - "/submit 409 response with check_mapping_exists_with_proposals shape on duplicate-pending race"
  - "check_mapping_exists_with_proposals Check 0 branch for pending new-pair proposals (mapping_id IS NULL)"
affects: [32-04-debt-03-go-h2, 32-05-debt-05-wp-rdf, 32-06-debt-06-go-rdf, phase-33-baseline-cleanup]

tech-stack:
  added: []
  patterns:
    - "Partial-unique index migration with pre-cleanup transaction (legacy-table H-2 port)"
    - "Keeper-selection by ORDER BY created_at ASC, id ASC (primary + fallback) — locked-in by ordering-invariant tests"
    - "Route-test fixture that repoints blueprint-bound models to a file-backed SQLite (TestingConfig :memory: is per-connection)"

key-files:
  created:
    - tests/test_proposal_models.py
  modified:
    - src/core/models.py
    - src/blueprints/api.py

key-decisions:
  - "Pre-migration cleanup keeper-selection MUST use ORDER BY created_at ASC, id ASC — NOT MIN(p.id) — because production data may have id/created_at disagreement from manual fixes/restores/imports; locked in by two ordering-invariant regression tests"
  - "/submit duplicate-pending response REUSES the existing check_mapping_exists_with_proposals shape ({pair_exists, blocking_type, existing, actions}) — NOT Reactome's verbatim {error, blocking_type} shape — existing WP UI clients already handle this shape via /check"
  - "Migration SQL targets the actual table name 'proposals' (NOT 'ke_wp_proposals' despite REQUIREMENTS.md label) — same applies to the partial-unique index name idx_proposals_pending_pair"
  - "check_mapping_exists_with_proposals extended with a Check 0 branch for pending new-pair proposals (mapping_id IS NULL) — Rule 2 deviation, mirrors the existing GO equivalent; without it the /submit IntegrityError branch could not produce the expected shape"
  - "Cleanup pass runs unconditionally (no 'if duplicates detected' gate) so the migration path is exercised in every environment; locally a no-op (0 duplicates), in prod the safety net"

patterns-established:
  - "Legacy-table H-2 port pattern: pre-migration cleanup (auto-reject duplicates with system: prefix) + CREATE UNIQUE INDEX IF NOT EXISTS, wrapped in one transaction with rollback-on-failure"
  - "Created_at-vs-id ordering invariant tests: any new keeper-selection migration must include a disagreement test and a tied-fallback test, otherwise a MIN(id) shortcut would silently pass"
  - "Route-test integration fixture (auth_client_filedb) monkey-patching blueprint-bound model.db onto a file-backed Database instance for multi-call /submit flows"

requirements-completed: [DEBT-04]

duration: 9min
completed: 2026-05-11
---

# Phase 32 Plan 03: KE-WP Race-Safe Pending-Duplicate Handling Summary

**Partial-unique pending index + DUPLICATE_PENDING sentinel ported from Reactome to the `proposals` table, with a pre-migration cleanup pass that honours `created_at` over `id` as keeper-selection key.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-05-11T10:45:05Z
- **Completed:** 2026-05-11T10:54:31Z
- **Tasks:** 3
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `idx_proposals_pending_pair` partial-unique index on `proposals(ke_id, wp_id) WHERE status='pending' AND mapping_id IS NULL` — DB-layer guarantee against duplicate pending+new-pair rows from concurrent /submit races.
- Pre-migration cleanup auto-resolves legacy duplicates (oldest pending row per pair kept by `created_at ASC, id ASC`; losers marked `rejected_by='system:phase-32-migration'` with deterministic `admin_notes`) — production-safe on existing data, idempotent on re-run.
- `ProposalModel.DUPLICATE_PENDING` sentinel + `sqlite3.IntegrityError` branch in `create_new_pair_proposal` so the model layer surfaces the race in a distinguishable way.
- `/submit` returns HTTP 409 with the existing `check_mapping_exists_with_proposals` shape on duplicate-pending, so no client-side change is needed.
- Seven regression tests (six model + one route) including two ordering-invariant tests that lock in `created_at` as the primary keeper-selection key.

## Task Commits

1. **Task 1: Write H-2 regression tests (RED state)** — `7f08d68` (test)
2. **Task 2: Add partial-unique index + DUPLICATE_PENDING sentinel** — `7dce19c` (feat)
3. **Task 3: Wire /submit → 409 with check_mapping shape** — `c55bcf6` (feat)

## Files Created/Modified

- `tests/test_proposal_models.py` (created) — six model tests (partial-unique index existence, concurrent inserts blocked, post-rejection resubmit, pre-migration cleanup baseline + created_at-vs-id disagreement + tied-created_at fallback) plus one route-level integration test.
- `src/core/models.py` (modified) — added `_migrate_proposals_pending_unique_index` method (cleanup + index in one transaction), `ProposalModel.DUPLICATE_PENDING` class constant, `sqlite3.IntegrityError` branch in `create_new_pair_proposal`, and a new Check 0 branch in `MappingModel.check_mapping_exists_with_proposals` for pending new-pair detection.
- `src/blueprints/api.py` (modified) — `/submit` handler maps `ProposalModel.DUPLICATE_PENDING` sentinel to 409 using `mapping_model.check_mapping_exists_with_proposals(ke_id, wp_id)` as the response body.

## Decisions Made

- **Keeper-selection algorithm:** `ORDER BY created_at ASC, id ASC LIMIT 1` (created_at primary, id tiebreaker / NULL fallback per CONTEXT.md L27 locked decision). Explicitly rejected the `MIN(p.id)` shortcut because production data may have id/created_at disagreement from manual fixes, restores, or imports. Two ordering-invariant regression tests lock this in.
- **Response shape:** /submit duplicate-pending response reuses the existing `check_mapping_exists_with_proposals` shape (`{pair_exists, blocking_type, existing, actions}`) instead of Reactome's verbatim `{error, blocking_type}` shape — existing WP UI clients already handle this shape via /check, no client-side change required.
- **Cleanup unconditional:** The cleanup SELECT-and-mark pass runs every startup (logs `auto-rejected 0 duplicate pending new-pair rows` locally) rather than being gated on a "duplicates detected" check — keeps the migration path exercised in every environment.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing Critical Functionality] Extended `check_mapping_exists_with_proposals` with a pending new-pair Check 0 branch**

- **Found during:** Task 3 (Wire /submit route — when planning to call `mapping_model.check_mapping_exists_with_proposals(ke_id, wp_id)` per the plan instructions)
- **Issue:** The existing WP function only detected pending proposals via `JOIN proposals p ON p.mapping_id = m.id`, which excludes new-pair proposals (where `mapping_id IS NULL`). On a duplicate-pending race the function would have returned `{ke_exists: False, pair_exists: False, message: "new entries"}` — neither the route layer's 409 contract nor the test's `pair_exists=True` assertion could have been satisfied.
- **Fix:** Added a Check 0 branch at the start of `check_mapping_exists_with_proposals` that queries `proposals` directly by `(ke_id, wp_id, mapping_id IS NULL, status='pending')`, returning the same `pair_exists/blocking_type/existing/actions` shape. Mirrors the long-standing equivalent in `MappingModel.check_go_mapping_exists_with_proposals` (Check 0 at line 1931) and `ReactomeMappingModel.check_reactome_mapping_exists_with_proposals`.
- **Files modified:** `src/core/models.py` (added ~30 lines in `check_mapping_exists_with_proposals`)
- **Verification:** route test `test_submit_returns_409_with_check_shape_on_duplicate_pending` asserts `pair_exists=True`, `blocking_type='pending_proposal'`, and `existing.ke_id` / `existing.wp_id` match the submitted pair — would have failed without this branch.
- **Committed in:** `c55bcf6` (Task 3 commit)

**2. [Rule 3 — Blocking] Added route-test fixture `auth_client_filedb` for file-backed DB**

- **Found during:** Task 3 (route-test execution)
- **Issue:** TestingConfig sets `DATABASE_PATH = ":memory:"`, and SQLite `:memory:` databases are per-connection — each `Database.get_connection()` opens a fresh empty in-memory DB so tables/migrations from one connection are invisible to the next. The `client` conftest fixture's `Database(db_path).init_db()` call also creates a separate in-memory DB that the blueprint-bound `proposal_model`/`mapping_model` never see (they were wired during `create_app()` at module import time, before the fixture ran).
- **Fix:** New fixture `auth_client_filedb` instantiates `Database(tmp_path/route_test.db)` (file-backed, all migrations run) and uses `monkeypatch.setattr` to repoint the blueprint-bound model instances' `.db` attribute. Restored automatically by pytest.
- **Files modified:** `tests/test_proposal_models.py` (fixture only, no production-code change)
- **Verification:** route test passes 7/7 with the fixture; without it the test failed with `sqlite3.OperationalError: no such table: proposals`.
- **Committed in:** `c55bcf6` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical functionality, 1 blocking test-infrastructure gap)
**Impact on plan:** Both auto-fixes essential. Rule 2 deviation closes a long-standing parity gap with the GO equivalent and is required for the plan's specified response shape to work at all. Rule 3 deviation is a test-only addition with no production impact. No scope creep — both stay strictly within DEBT-04.

## Issues Encountered

- **Pre-existing test failures (NOT caused by this plan):** `tests/test_app.py::TestRoutes::test_login_redirect` (404 vs 302) and `tests/test_app.py::TestGuestAuth::test_guest_login_page_renders`. Confirmed via `git stash` that both fail on `main` before this plan's changes. Tracked as Phase 33 backlog in STATE.md.
- The acceptance-criteria grep in PLAN's `<acceptance_criteria>` block used a literal pattern `p[0-9]+\.created_at ASC, p[0-9]+\.id ASC` on the same line — passes when extracting via `awk '/def …/,/^class /'` rather than `/^    def [a-z_]+\(/` (the latter terminator didn't match because the next sibling after `_migrate_proposals_pending_unique_index` is `class MappingModel:`, not another `def`). Confirmed both required `ORDER BY` lines exist; no `MIN(p\.id)` shortcut.

## User Setup Required

None — purely internal DB migration + route refinement. The next app startup will run the cleanup pass + create the index automatically. No env vars, no manual SQL, no client-side changes.

## Next Phase Readiness

- DEBT-04 satisfied. Phase 32 Plan 04 (DEBT-03: GO H-2 port) can now follow the same pattern verbatim against `ke_go_proposals` (already has `rejected_by`/`rejected_at` columns from its CREATE TABLE — no Phase-2 migration prerequisite).
- Phase 32 Plan 05 (DEBT-05) and Plan 06 (DEBT-06) are independent and unblocked.
- The legacy-table H-2 cleanup pattern (`ORDER BY created_at ASC, id ASC` + ordering-invariant tests) is now an established convention — reuse for GO; do NOT regress to `MIN(id)`.

## Self-Check

- File `tests/test_proposal_models.py`: FOUND
- File `src/core/models.py`: FOUND (modified)
- File `src/blueprints/api.py`: FOUND (modified)
- Commit `7f08d68`: FOUND (Task 1: test RED)
- Commit `7dce19c`: FOUND (Task 2: migration + sentinel)
- Commit `c55bcf6`: FOUND (Task 3: route 409)
- All 7 tests in `tests/test_proposal_models.py` pass (verified with `pytest --no-cov`)
- Keeper-selection SQL contains `ORDER BY p2.created_at ASC, p2.id ASC` and `ORDER BY p3.created_at ASC, p3.id ASC`; no `MIN(p\d\.id)` shortcut

## Self-Check: PASSED

---
*Phase: 32-go-wp-sibling-debt-sweep*
*Completed: 2026-05-11*
