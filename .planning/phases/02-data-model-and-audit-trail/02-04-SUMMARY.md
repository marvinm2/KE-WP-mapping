---
phase: 02-data-model-and-audit-trail
plan: 04
subsystem: ui
tags: [flask, jinja2, sqlite, datatables, provenance, uuid]

# Dependency graph
requires:
  - phase: 02-01
    provides: UUID and provenance columns (uuid, approved_by_curator, approved_at_curator) in mappings table

provides:
  - Curator and Approved columns in explore browse table replacing Timestamp
  - Fallback display logic for pre-Phase-2 mappings (approved_by_curator or created_by)
  - get_mapping_by_uuid() model method for stable UUID lookup on MappingModel
  - get_go_mapping_by_uuid() model method on GoMappingModel
  - /mappings/<uuid> stable detail page returning 200 for valid UUIDs and 404 for unknown
  - templates/mapping_detail.html with all provenance fields including UUID
  - Suggestion score and proposal UUID visible in admin proposal detail modal

affects:
  - Phase 3 (public API) — /mappings/<uuid> is the stable permalink for external consumers
  - EXPLO-04 — every mapping now has a stable addressable URL
  - CURAT-01 — curator name and approval date visible in browse table

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Jinja2 fallback chain: approved_by_curator or created_by or '—' for pre-Phase-2 records
    - Date truncation via .split('T')[0].split(' ')[0] handles both ISO (T-separator) and SQLite (space-separator) timestamps
    - abort(404) pattern for unknown UUIDs in Flask route

key-files:
  created:
    - templates/mapping_detail.html
  modified:
    - templates/explore.html
    - src/core/models.py
    - src/blueprints/main.py
    - templates/admin_proposals.html

key-decisions:
  - "UUID is shown in mapping_detail.html (permanent detail page) but NOT in the curator explore table — admin/API only per locked decision"
  - "DataTables order updated from col 6 (old Timestamp) to col 7 (new Approved) after adding Curator column"
  - "mapping_model already wired via set_models() in main.py — no additional wiring needed for new route"
  - "mapping_detail.html uses standalone HTML with navigation component include — no Jinja2 base template inheritance in this project"

patterns-established:
  - "UUID lookup routes: get_mapping_by_uuid(uuid) returns dict or None; abort(404) handles the None case"
  - "Admin-only fields (UUID, suggestion_score) rendered via JavaScript in modal innerHTML, not in Jinja2 table rows"

requirements-completed:
  - CURAT-01
  - EXPLO-04

# Metrics
duration: 14min
completed: 2026-02-20
---

# Phase 2 Plan 04: Provenance UI and Stable Mapping Detail Page Summary

**Curator/Approved columns surfaced in explore table with pre-Phase-2 fallbacks, and every mapping addressable at /mappings/<uuid> returning 404 for unknown UUIDs**

## Performance

- **Duration:** 14 min
- **Started:** 2026-02-20T13:41:05Z
- **Completed:** 2026-02-20T13:55:00Z
- **Tasks:** 2
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- Replaced Timestamp column in explore browse table with Curator and Approved columns, using fallback chain for legacy mappings
- Added `get_mapping_by_uuid()` to MappingModel and `get_go_mapping_by_uuid()` to GoMappingModel
- Added `/mappings/<uuid>` Flask route that returns 200 with full provenance page or 404 for unknown UUIDs
- Created `templates/mapping_detail.html` showing all fields including UUID (admin/API detail page)
- Added Suggestion Score and Proposal UUID to admin proposal detail modal

## Task Commits

Each task was committed atomically:

1. **Task 1: Provenance columns in explore table and UUID model methods** - `e6d436e` (feat)
2. **Task 2: /mappings/<uuid> route and admin provenance display** - `4840129` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `templates/explore.html` — Curator + Approved columns replacing Timestamp; DataTables order updated to col 7; no UUID column
- `src/core/models.py` — Added get_mapping_by_uuid() to MappingModel; get_go_mapping_by_uuid() to GoMappingModel
- `src/blueprints/main.py` — Added /mappings/<string:mapping_uuid> route; added abort import
- `templates/mapping_detail.html` — New: standalone HTML showing all provenance fields including UUID; back link to /explore
- `templates/admin_proposals.html` — Suggestion Score and Proposal UUID in admin proposal detail modal (JavaScript)

## Decisions Made

- UUID is shown in `mapping_detail.html` (permanent detail page) but NOT in the curator explore table — admin/API only per locked decision from Plan 01
- DataTables sort column updated from index 6 (old Timestamp) to index 7 (new Approved) after adding Curator column
- `mapping_model` was already wired via `set_models()` in `main.py` — the new route reuses it without any additional wiring
- `mapping_detail.html` uses standalone HTML with `{% include 'components/navigation.html' %}` — no base template inheritance in this project (all templates are standalone)

## URL Pattern for Stable Mapping Detail Pages

Pattern: `/mappings/<uuid>` where UUID is the stable v4 UUID stored in the `uuid` column of the `mappings` table.

- Valid UUID: HTTP 200, renders `mapping_detail.html`
- Unknown UUID: HTTP 404 via Flask's `abort(404)`, rendered by the existing error handler

## Fallback Logic for Pre-Phase-2 Mappings

In the explore table, mappings approved before Phase 2 (where `approved_by_curator IS NULL`) display:

- Curator column: `approved_by_curator or created_by or '—'`
- Approved column: `(approved_at_curator or created_at or '').split('T')[0].split(' ')[0]`

The split logic handles both ISO 8601 timestamps (T-separator) and SQLite's default format (space-separator) by taking the first 10 characters (date portion only).

## How mapping_model Was Wired

No changes were needed. `mapping_model` is set as a module-level global in `src/blueprints/main.py` via `set_models()` called at app startup from `app.py`. The new `mapping_detail` route uses this same `mapping_model` instance.

## Base Template

`mapping_detail.html` uses no Jinja2 template inheritance (no `{% extends %}`). All templates in this project are standalone HTML files that use `{% include 'components/navigation.html' %}` for the navigation bar.

## Deviations from Plan

None — plan executed exactly as written. The `get_go_mapping_by_uuid()` method was added per plan spec.

## Issues Encountered

Pre-existing rate-limiter test flakiness (5 tests intermittently fail with HTTP 429 when running the test suite multiple times in quick succession). These failures are unrelated to this plan's changes — all model and route functionality tests pass. Logged to deferred-items.

## Next Phase Readiness

- CURAT-01 complete: curator name and approval date visible in browse table for all mappings
- EXPLO-04 complete: every mapping addressable via /mappings/<uuid>
- Stable UUID URLs ready for consumption by Phase 3 public API
- Admin proposal workflow has UUID and suggestion_score visibility

## Self-Check: PASSED

All files exist and all task commits verified:
- `templates/mapping_detail.html` — FOUND
- `templates/explore.html` — FOUND
- `src/core/models.py` — FOUND
- `src/blueprints/main.py` — FOUND
- `templates/admin_proposals.html` — FOUND
- `e6d436e` — FOUND (Task 1 commit)
- `4840129` — FOUND (Task 2 commit)

---
*Phase: 02-data-model-and-audit-trail*
*Completed: 2026-02-20*
