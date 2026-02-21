---
phase: 03-stable-public-rest-api
plan: 04
subsystem: api, database
tags: [sqlite, proposals, flask, blueprints, gap-closure, uat]

requires:
  - phase: 03-stable-public-rest-api
    provides: "ProposalModel, MappingModel, admin blueprint with approve_proposal(), /submit route"

provides:
  - "All /submit requests create pending proposals (mapping_id=NULL) — no direct mapping creation"
  - "_migrate_proposals_new_pair_fields() adds ke_id/ke_title/wp_id/wp_title/new_pair_connection_type/new_pair_confidence_level to proposals table"
  - "ProposalModel.create_new_pair_proposal() stores new KE-WP pair data on proposal row"
  - "approve_proposal() creates mapping + writes provenance for new-pair (mapping_id=None) proposals"
  - "get_proposal_by_id() and get_all_proposals() alias m.ke_id as mapping_ke_id etc. to prevent NULL clobbering of p.ke_id"

affects: [admin-proposals-page, curator-submit-flow, UAT-test-7, phase-04]

tech-stack:
  added: []
  patterns:
    - "New-pair proposal pattern: /submit always creates proposal; mapping only created at admin approval"
    - "JOIN aliasing pattern: m.col AS mapping_col to prevent duplicate-column resolution clobbering p.col values"
    - "Temp-file DB fixture in test: re-wire blueprint module-level singletons per test to avoid :memory: per-connection isolation"

key-files:
  created: []
  modified:
    - src/core/models.py
    - src/blueprints/api.py
    - src/blueprints/admin.py
    - tests/test_app.py

key-decisions:
  - "All /submit submissions create pending proposals regardless of submitter role — closes UAT Test 7 failure"
  - "JOIN alias pattern (mapping_ke_id vs ke_id) chosen over restructuring query to preserve backwards compatibility with existing-mapping callers that already read p.ke_id correctly via p.*"
  - "submit_client fixture in test directly overwrites api_mod.proposal_model/mapping_model attributes instead of calling set_models() to avoid disturbing other model references"

patterns-established:
  - "New-pair proposals: proposals.mapping_id=NULL signals 'create mapping on approval'; approve_proposal() branches on mapping_id is None"
  - "Proposal new-pair columns: ke_id/ke_title/wp_id/wp_title stored on proposal row so approval can create mapping without losing data"

requirements-completed: [API-01, API-02, API-03, API-04]

duration: 8min
completed: 2026-02-21
---

# Phase 03 Plan 04: UAT Gap Closure — Proposal-First Submit Flow Summary

**Closed UAT Test 7: /submit now creates pending proposals for all users, approve_proposal() creates mappings with provenance, and JOIN aliasing eliminates NULL-clobbering data corruption**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-21T09:25:56Z
- **Completed:** 2026-02-21T09:33:56Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `_migrate_proposals_new_pair_fields()` migration and `ProposalModel.create_new_pair_proposal()` to store new KE-WP pair data on proposal rows (mapping_id=NULL)
- Changed `/submit` to call `create_new_pair_proposal()` instead of `create_mapping()` — all submitters now get a pending proposal that requires admin approval before the mapping appears
- Fixed `approve_proposal()` with a `mapping_id is None` branch that calls `create_mapping()` then `update_mapping()` with full provenance at approval time
- Fixed silent data-corruption bug: `get_proposal_by_id()` and `get_all_proposals()` now alias `m.ke_id` as `mapping_ke_id` etc., preventing NULL JOIN values from clobbering the `p.ke_id` columns stored on new-pair proposals
- Added `TestSubmitCreatesProposal` test class with 2 new tests verifying the proposal-first flow end-to-end

## Task Commits

1. **Task 1: Add migration + create_new_pair_proposal()** - `83bb531` (feat)
2. **Task 2: Fix JOIN aliasing, /submit, approve_proposal(), tests** - `47fd98b` (feat)

## Files Created/Modified

- `/home/marvin/Documents/Services/Ke-gene-mapping/KE-WP-mapping/src/core/models.py` - Added `_migrate_proposals_new_pair_fields()`, `create_new_pair_proposal()`, and aliased JOIN columns in `get_proposal_by_id()` / `get_all_proposals()`
- `/home/marvin/Documents/Services/Ke-gene-mapping/KE-WP-mapping/src/blueprints/api.py` - `/submit` now calls `create_new_pair_proposal()` instead of `create_mapping()`, returns `{proposal_id, message}`
- `/home/marvin/Documents/Services/Ke-gene-mapping/KE-WP-mapping/src/blueprints/admin.py` - `approve_proposal()` handles `mapping_id is None` branch: creates mapping then writes provenance
- `/home/marvin/Documents/Services/Ke-gene-mapping/KE-WP-mapping/tests/test_app.py` - Added `TestSubmitCreatesProposal` with `submit_client` fixture (temp-file DB pattern) and 2 tests

## Decisions Made

- All `/submit` submissions create pending proposals regardless of submitter role — closes UAT Test 7 failure where admin bypass allowed direct mapping creation
- JOIN alias pattern chosen (`m.ke_id AS mapping_ke_id`) to prevent sqlite3.Row dict() from resolving duplicate column names by last value (NULL from LEFT JOIN clobbers p.ke_id stored value)
- `submit_client` fixture directly overwrites api blueprint module-level model attributes per-test, following the same temp-file DB pattern established in 03-03 for v1_client

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test data used invalid schema values for connection_type and confidence_level**

- **Found during:** Task 2 (adding TestSubmitCreatesProposal tests)
- **Issue:** Plan specified `"is_associated"` for connection_type and `"High"/"Medium"` for confidence_level, but MappingSchema validates connection_type as one of `["causative", "responsive", "other", "undefined"]` and confidence_level as one of `["low", "medium", "high"]` (lowercase only). Tests returned 400 BAD REQUEST at schema validation.
- **Fix:** Changed test data to use `"causative"` for connection_type and `"high"/"medium"` for confidence_level — values the existing schema accepts.
- **Files modified:** tests/test_app.py
- **Verification:** Tests pass (200 response with proposal_id)
- **Committed in:** 47fd98b (Task 2 commit)

**2. [Rule 3 - Blocking] TestingConfig :memory: DB caused "no such table: proposals" in new tests**

- **Found during:** Task 2 (running TestSubmitCreatesProposal tests)
- **Issue:** The existing `auth_client` fixture uses the app's service container whose DB is `:memory:` (TestingConfig). Each `sqlite3.connect()` call opens a new in-memory DB without the schema, so `proposal_model.create_new_pair_proposal()` failed with "no such table: proposals".
- **Fix:** Added `submit_client` fixture that creates a fresh temp-file DB and directly replaces api blueprint's `proposal_model`, `mapping_model`, and `cache_model` module attributes — same pattern as `v1_client` fixture in test_v1_api.py.
- **Files modified:** tests/test_app.py
- **Verification:** Both new tests pass (confirmed schema tables exist, proposal created successfully)
- **Committed in:** 47fd98b (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug in test data, 1 blocking infrastructure issue)
**Impact on plan:** Both auto-fixes necessary for tests to actually run and validate the implementation. No scope creep.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## Next Phase Readiness

- UAT Test 7 gap is now closed: all /submit paths go through proposal workflow
- Admin approval creates mapping with full provenance (approved_by_curator, approved_at_curator, suggestion_score)
- 66 tests all pass; no regressions introduced
- Phase 4 (next phase) can proceed with confidence in the proposal workflow correctness

---
*Phase: 03-stable-public-rest-api*
*Completed: 2026-02-21*
