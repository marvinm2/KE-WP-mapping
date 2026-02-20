---
phase: 02-data-model-and-audit-trail
plan: 01
subsystem: database
tags: [sqlite, migrations, uuid, provenance, auto-migration]

# Dependency graph
requires: []
provides:
  - "uuid column on mappings (TEXT, unique index, backfilled for existing rows)"
  - "approved_by_curator + approved_at_curator columns on mappings and ke_go_mappings"
  - "uuid, suggestion_score, is_stale columns on proposals and ke_go_proposals"
  - "UUID4 generation in MappingModel.create_mapping() and GoMappingModel.create_mapping()"
  - "Four new migration methods: _migrate_mappings_uuid_and_provenance, _migrate_go_mappings_uuid_and_provenance, _migrate_proposals_phase2_fields, _migrate_go_proposals_phase2_fields"
affects:
  - 02-02  # curator approval enforcement depends on approved_by_curator column
  - 02-03  # audit trail display depends on uuid and provenance columns
  - 02-04  # public API depends on uuid as stable external identifier

# Tech tracking
tech-stack:
  added: ["uuid (stdlib, imported as uuid_lib)"]
  patterns:
    - "PRAGMA table_info → check columns → ALTER TABLE ADD COLUMN if missing → log — established auto-migration pattern, extended in this plan"
    - "UUID4 generated in Python at row creation time, stored as TEXT in SQLite"
    - "UUID backfill via SQLite randomblob() for pre-existing rows without uuid"

key-files:
  created: []
  modified:
    - src/core/models.py

key-decisions:
  - "Backfill existing rows with SQLite randomblob() UUID expression rather than Python-side migration — avoids loading all rows into memory, runs atomically inside init_db() transaction"
  - "Unique index on uuid created with IF NOT EXISTS — idempotent and prevents duplicates for new rows"
  - "proposal tables: uuid is nullable for pre-Phase-2 rows (not backfilled) — only new proposals get a uuid via Python at creation time (not yet wired to create_proposal(), deferred to later plan)"
  - "Coverage failure (38% vs 80% threshold) is pre-existing — all 45 tests pass, no regressions introduced"

patterns-established:
  - "Migration method signature: _migrate_X(self, conn) — receives active connection, raises on error"
  - "Error wrapping: try/except Exception, logger.error, raise — consistent with _migrate_proposals_admin_fields"
  - "Migration call order in init_db(): admin fields → updated_by → uuid/provenance (mapping tables) → phase2 fields (proposal tables)"

requirements-completed: [CURAT-01, CURAT-03, EXPLO-04]

# Metrics
duration: 3min
completed: 2026-02-20
---

# Phase 2 Plan 01: Data Model and Audit Trail — Schema Migrations Summary

**Five new columns across four tables via idempotent ALTER TABLE migrations, plus UUID4 generation at mapping creation time, establishing the data provenance foundation for all Phase 2 curation and audit features.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-20T13:25:51Z
- **Completed:** 2026-02-20T13:28:51Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `uuid`, `approved_by_curator`, `approved_at_curator` to both `mappings` and `ke_go_mappings` tables via two new migration methods; existing rows backfilled with SQLite randomblob() UUIDs; unique indexes created
- Added `uuid`, `suggestion_score`, `is_stale` to both `proposals` and `ke_go_proposals` tables via two new migration methods
- Wired `uuid_lib.uuid4()` into `MappingModel.create_mapping()` and `GoMappingModel.create_mapping()` — every new mapping row now gets a stable UUID4 at insert time
- All four migration methods called from `init_db()` and idempotent (safe to run multiple times against same DB)

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration methods for mapping tables (uuid + provenance columns)** - `715b71c` (feat)
2. **Task 2: Proposal phase2 migrations and UUID generation in create_mapping()** - `cf43f28` (feat)

**Plan metadata:** (docs commit follows this summary)

## Files Created/Modified

- `src/core/models.py` — Added `import uuid as uuid_lib`; added four migration methods; wired all four into `init_db()`; updated both `create_mapping()` methods to generate and insert UUID4

## Decisions Made

- Backfill existing mapping rows with SQLite `randomblob()` UUID expression instead of Python-side migration — runs atomically inside the existing `init_db()` transaction with no memory overhead
- Unique index on `uuid` uses `CREATE UNIQUE INDEX IF NOT EXISTS` — idempotent, protects uniqueness constraint for all future inserts
- Proposal table `uuid` is nullable and not backfilled for pre-Phase-2 rows — backfilling proposals is not required by this plan; `create_proposal()` UUID wiring is deferred to a later Phase 2 plan
- Pre-existing coverage failure (38% vs 80%) is out of scope — all 45 tests pass, zero regressions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `make test` exits with code 2 due to a pre-existing coverage threshold failure (38% total vs 80% required). All 45 tests pass. Coverage gap is across exporters, suggestions, and main blueprint — none touched in this plan. Logged to deferred-items.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All five new columns exist on the four target tables — downstream plans (02-02, 02-03, 02-04) can proceed
- Migration methods are idempotent — starting the app against an existing production database is safe
- UUID backfill for the mapping tables is complete — every existing mapping row has a valid UUID
- Proposal table `uuid` wiring in `create_proposal()` still pending — downstream plans that need proposal UUIDs must add that step

---
*Phase: 02-data-model-and-audit-trail*
*Completed: 2026-02-20*

## Self-Check: PASSED

- src/core/models.py: FOUND
- 02-01-SUMMARY.md: FOUND
- Commit 715b71c (Task 1): FOUND
- Commit cf43f28 (Task 2): FOUND
- _migrate_mappings_uuid_and_provenance: FOUND
- _migrate_go_mappings_uuid_and_provenance: FOUND
- _migrate_proposals_phase2_fields: FOUND
- _migrate_go_proposals_phase2_fields: FOUND
