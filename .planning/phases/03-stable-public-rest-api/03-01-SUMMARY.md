---
phase: 03-stable-public-rest-api
plan: 01
subsystem: database
tags: [sqlite, migrations, pagination, suggestion_score, go_namespace, BioBERT]

requires:
  - phase: 02-data-model-and-audit-trail
    provides: uuid and provenance columns on mappings/ke_go_mappings, proposal suggestion_score column

provides:
  - "suggestion_score REAL column on mappings table (nullable, set at approval time)"
  - "suggestion_score REAL column on ke_go_mappings table (nullable)"
  - "go_namespace TEXT NOT NULL DEFAULT 'biological_process' column on ke_go_mappings"
  - "MappingModel.get_mappings_paginated() with ke_id/pathway_id/confidence_level/ke_ids filters"
  - "GoMappingModel.get_go_mappings_paginated() with ke_id/go_term_id/confidence_level filters; returns go_namespace per row"
  - "MappingModel.update_mapping() accepts suggestion_score kwarg and persists it via ALLOWED_FIELDS"
  - "admin.py approve_proposal() copies suggestion_score from proposal to mapping row at approval time"

affects:
  - 03-stable-public-rest-api
  - 03-02 (v1 API blueprint will call get_mappings_paginated/get_go_mappings_paginated)

tech-stack:
  added: []
  patterns:
    - "PRAGMA table_info() idempotent migration pattern: check column existence before ALTER TABLE"
    - "Paginated query builder: conditions list + params list + WHERE clause assembly + LIMIT/OFFSET"
    - "ALLOWED_FIELDS whitelist dict in update_mapping() guards all dynamic SET clauses"

key-files:
  created: []
  modified:
    - src/core/models.py
    - src/blueprints/admin.py

key-decisions:
  - "suggestion_score column is REAL, nullable — NULL for all pre-Phase-3 rows; non-null only after curator approval of a scored proposal"
  - "go_namespace DEFAULT 'biological_process' — all current GO mappings are BP; column present for MF/CC extensibility"
  - "suggestion_score written to ALLOWED_FIELDS in update_mapping() — required so the value is not silently dropped by the dynamic SET clause builder"

patterns-established:
  - "Migration idempotency: PRAGMA table_info() check before every ALTER TABLE — safe to re-run on existing DB"
  - "Paginated data layer: (List[Dict], total_count) tuple — consistent return type for v1 API blueprint"

requirements-completed: [API-01, API-02, API-03]

duration: 5min
completed: 2026-02-20
---

# Phase 3 Plan 01: Data Model Preparation for v1 API Summary

**suggestion_score and go_namespace columns migrated onto mapping tables; paginated query methods and approval wiring added for the v1 REST API data layer**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-20T21:55:06Z
- **Completed:** 2026-02-20T22:00:15Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added three idempotent migration methods to Database class: `_migrate_mappings_suggestion_score`, `_migrate_go_mappings_suggestion_score`, `_migrate_go_mappings_go_namespace`
- Added `MappingModel.get_mappings_paginated()` and `GoMappingModel.get_go_mappings_paginated()` as the paginated data layer the v1 API blueprint (Plan 02) will call
- Wired `suggestion_score` from proposal to mapping row at admin approval time in `approve_proposal()`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add suggestion_score migration and paginated query methods to models.py** - `da63db0` (feat)
2. **Task 2: Wire suggestion_score from proposal to mapping at admin approval** - `561759e` (feat)

**Plan metadata:** (docs commit — pending)

## Files Created/Modified
- `src/core/models.py` - Added three migration methods, two paginated query methods, `suggestion_score` param to `update_mapping()`
- `src/blueprints/admin.py` - `approve_proposal()` now reads `proposal.get('suggestion_score')` and passes it to `update_mapping()`

## Decisions Made
- `suggestion_score` is REAL and nullable — correct for pre-Phase-3 rows that never had a score on the mapping row
- `go_namespace` defaults to `'biological_process'` — all existing GO mappings are BP, column enables future MF/CC expansion without schema changes
- Added `'suggestion_score': 'suggestion_score'` to `ALLOWED_FIELDS` in `update_mapping()` — required so the kwarg is not silently dropped by the dynamic SET clause builder

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Coverage threshold failure (37% < 80%) in `make test` is a pre-existing condition unrelated to this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Data layer is complete: `get_mappings_paginated()` and `get_go_mappings_paginated()` are ready for Plan 02 (v1 API blueprint) to call
- `suggestion_score` now flows end-to-end: proposal creation -> admin approval -> mapping row -> (Plan 02 will expose it in provenance.suggestion_score JSON field)
- All 45 existing tests pass

---
*Phase: 03-stable-public-rest-api*
*Completed: 2026-02-20*
