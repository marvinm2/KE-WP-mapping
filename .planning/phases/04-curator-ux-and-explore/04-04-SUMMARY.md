---
phase: 04-curator-ux-and-explore
plan: "04"
subsystem: ui
tags: [flask, jinja2, sqlite, select2, csv, stats, public-api]

# Dependency graph
requires:
  - phase: 03-stable-public-rest-api
    provides: /api/v1/mappings with pagination, filtering, and Accept:text/csv support
provides:
  - Public /stats page with metric cards, confidence table, AOP filter, and export buttons
  - ?format=csv query param support on /api/v1/mappings and /api/v1/go-mappings
  - get_mapping_stats() helper for aggregate COUNT queries against both mapping tables
affects:
  - 04-curator-ux-and-explore (provides public data access entry point)
  - future phases using /api/v1/mappings CSV export

# Tech tracking
tech-stack:
  added: [Select2 4.1.0-rc.0 (CDN), jQuery 3.6.0 (CDN)]
  patterns: [standalone HTML template with navigation include, get_connection() try/finally conn.close() DB pattern, ?format query param alongside Accept header for format negotiation]

key-files:
  created:
    - templates/stats.html
  modified:
    - src/blueprints/main.py
    - src/blueprints/v1_api.py
    - templates/components/navigation.html

key-decisions:
  - "get_mapping_stats() uses try/finally conn.close() pattern matching existing MappingModel methods — not a context manager (Database.get_connection() returns plain sqlite3.Connection)"
  - "?format=csv param checked before Accept header in _respond_collection — allows download-button anchor hrefs to trigger CSV without setting Accept headers"
  - "Content-Disposition: attachment header added to CSV responses in _respond_collection — needed for browser download trigger from anchor href"
  - "AOP coverage indicator hidden by default; shown via JS only when AOP is selected — avoids misleading 0/0 display on page load"
  - "Stats route omits @login_required and @monitor_performance — public access is the explicit requirement"

patterns-established:
  - "Public routes: no @login_required, no @monitor_performance for simplicity"
  - "Format negotiation: check ?format= param first, fall back to Accept header — enables both programmatic (header) and browser (param) access"

requirements-completed: [EXPLO-05, EXPLO-06]

# Metrics
duration: 4min
completed: 2026-02-21
---

# Phase 4 Plan 04: Dataset Metrics Dashboard Summary

**Public /stats page with metric cards, confidence table, AOP/confidence filter, and export buttons; plus ?format=csv query param on /api/v1/mappings for download-button CSV export**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-21T13:39:16Z
- **Completed:** 2026-02-21T13:43:15Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created public `/stats` route (no `@login_required`) with `get_mapping_stats()` helper that queries both `mappings` and `ke_go_mappings` tables for COUNT and GROUP BY confidence_level
- Built `templates/stats.html` with three metric cards (wp_total, go_total, total), confidence breakdown table, AOP Select2 filter, confidence toggle buttons, dynamic export link hrefs, and AOP coverage indicator
- Updated `_respond_collection` in v1_api.py to honor `?format=csv` query param in addition to existing `Accept: text/csv` header, with `Content-Disposition: attachment` for download-button flow
- Added "Stats" nav link to `navigation.html`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add /stats route and get_mapping_stats() helper** - `19f4464` (feat)
2. **Task 2: Create stats.html template and add ?format=csv to v1_api.py** - `40900d6` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `templates/stats.html` - New standalone public stats page with metric cards, confidence table, AOP filter (Select2), confidence toggle buttons, and export buttons with dynamic href updates and AOP coverage indicator
- `src/blueprints/main.py` - Added `get_mapping_stats()` helper (try/finally DB pattern) and `GET /stats` route
- `src/blueprints/v1_api.py` - Updated `_respond_collection()` to check `?format=csv` param before Accept header; added `Content-Disposition: attachment` to CSV responses
- `templates/components/navigation.html` - Added Stats nav link

## Decisions Made
- `get_mapping_stats()` uses `conn = self.db.get_connection()` with `try/finally conn.close()` — matches the existing pattern throughout MappingModel; `Database.get_connection()` is not a context manager
- `?format=csv` checked first in `_respond_collection`, Accept header as fallback — download-button anchor hrefs can't set Accept headers, so the param approach is required
- `Content-Disposition: attachment` header added to all CSV responses — enables browser file-save dialog from anchor `href` clicks
- AOP coverage indicator hidden by default, shown via JavaScript only when an AOP is selected — avoids showing a confusing "0 of 0" state on initial page load

## Deviations from Plan

None - plan executed exactly as written.

The only adaptation was using the correct DB connection pattern (`conn = model.db.get_connection()` with explicit `try/finally conn.close()`) rather than the `with` context manager shown in the plan's code example, since `Database.get_connection()` returns a plain `sqlite3.Connection`, not a context manager. The plan itself explicitly noted this check was required.

## Issues Encountered
None.

## Next Phase Readiness
- EXPLO-05 and EXPLO-06 requirements are complete
- `/stats` is publicly accessible and shows all required metrics
- CSV export via `?format=csv` works for both programmatic (Accept header) and browser download (param) access
- AOP coverage indicator is functional, driven by existing `/get_aop_kes/<aop_id>` and `/api/v1/mappings?aop_id=` endpoints

---
*Phase: 04-curator-ux-and-explore*
*Completed: 2026-02-21*
