---
phase: 04-curator-ux-and-explore
plan: 03
subsystem: ui
tags: [datatables, ajax, select2, filter-chips, coverage-gaps, explore-page]

requires:
  - phase: 03-stable-public-rest-api
    provides: "/api/v1/mappings endpoint with aop_id, confidence_level, per_page, page query params"

provides:
  - "AJAX DataTable on /explore KE-WP tab driven by /api/v1/mappings (serverSide: true)"
  - "AOP Select2 filter with search-as-you-type, populated from /get_aop_options"
  - "Confidence toggle buttons (All/High/Medium/Low) with immediate re-query"
  - "Filter chips above DataTable with per-chip remove and Clear all button (AND logic)"
  - "Coverage Gaps third tab: AOP-scoped unmapped KE list with Map button to /?ke_id="
  - "Simplified explore() route (no dataset= server render; go_dataset= retained for KE-GO tab)"

affects: [phase-05, curator-ux, explore-page, ke-go-tab]

tech-stack:
  added: [select2@4.1.0-rc.0]
  patterns:
    - "AJAX DataTable with serverSide: true fetching /api/v1/mappings using URLSearchParams"
    - "Global filter state object (wpState) drives AJAX params on each reload"
    - "Event delegation for propose-change button on dynamically rendered DataTable rows"
    - "Two-step gap detection: /get_aop_kes returns all KEs, /api/v1/mappings?aop_id returns mapped subset"

key-files:
  created: []
  modified:
    - templates/explore.html
    - src/blueprints/main.py

key-decisions:
  - "Select2 CDN added directly to explore.html head (not main.css or base template) - page-scoped dependency"
  - "Filter chip styles duplicated inline (not only in main.css) because 04-03 and 04-02 execute in same wave - wave-1 safe"
  - "Coverage Gaps uses /get_aop_kes (existing api.py route) for AOP KE list - avoids new endpoint"
  - "explore() route drops dataset= server render entirely - KE-WP count no longer shown in tab label (AJAX-only)"
  - "Propose Change modal uses event delegation (#datasetTable .propose-change) because rows are AJAX-rendered"
  - "/get_aop_kes response uses KElabel/KEtitle field names (not ke_id/ke_title) - JS field extraction matches actual shape"

patterns-established:
  - "AJAX DataTable pattern: serverSide: true + URLSearchParams-built fetch to /api/v1endpoints"
  - "Filter state object pattern: wpState.{field} drives AJAX params, renderFilterChips() reacts to state"

requirements-completed: [EXPLO-01, EXPLO-02, EXPLO-03]

duration: 12min
completed: 2026-02-21
---

# Phase 04 Plan 03: Explore Page AJAX DataTable with Filters and Coverage Gaps Summary

**Explore page KE-WP tab converted from server-rendered rows to Select2 + toggle-button filtered AJAX DataTable via /api/v1/mappings, with new Coverage Gaps tab showing unmapped KEs per AOP with Map button**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-21T13:39:05Z
- **Completed:** 2026-02-21T13:51:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- KE-WP Mappings tab is now fully AJAX-driven (serverSide: true DataTable, no Jinja2 rows in HTML source)
- AOP filter: Select2 search-as-you-type dropdown populated from /get_aop_options, immediately re-queries on select
- Confidence filter: toggle buttons All/High/Medium/Low that immediately re-query; both filters combine AND logic
- Active filter chips appear above the table with individual remove (x) and "Clear all" controls
- New Coverage Gaps third tab: select AOP, shows unmapped KEs (via /get_aop_kes + /api/v1/mappings diff), each with Map button linking to /?ke_id=
- KE-GO tab unchanged (still server-rendered, lazy DataTable init preserved)

## Task Commits

Both tasks were committed together (same file, wave-1 delivery):

1. **Task 1: Refactor explore.html KE-WP tab to AJAX DataTable with filter controls** - `774ad8a` (feat)
2. **Task 2: Implement Coverage Gaps tab data fetch and Map button** - `774ad8a` (feat)

**Plan metadata:** committed separately after SUMMARY creation

## Files Created/Modified

- `/home/marvin/Documents/Services/Ke-gene-mapping/KE-WP-mapping/templates/explore.html` - Complete rewrite: Select2 CDN, filter controls row, AJAX DataTable (empty tbody), Coverage Gaps tab HTML, new script block with all JS logic
- `/home/marvin/Documents/Services/Ke-gene-mapping/KE-WP-mapping/src/blueprints/main.py` - Simplified explore() route: removed dataset= (no longer server-rendering KE-WP rows), kept go_dataset=

## Decisions Made

- `explore()` route no longer calls `mapping_model.get_all_mappings()` — KE-WP data fetched client-side via /api/v1/mappings; this removes ~N row server-side load on every /explore page hit
- KE-WP tab label changed from "KE-WP Mappings (N)" to "KE-WP Mappings" — total count not available without server-render; shown dynamically in DataTable info row instead
- Inline CSS for `.conf-filter-btn` and `.filter-chip*` added to explore.html head — main.css additions from 04-02 execute in the same wave, so inline duplication prevents unstyled flash if 04-02 hasn't run yet
- Coverage Gaps uses two API calls: /get_aop_kes for all KEs in AOP, then /api/v1/mappings?aop_id for mapped subset — client-side set difference is clean and avoids a new dedicated endpoint

## Deviations from Plan

None - plan executed exactly as written. Field names in /get_aop_kes response (KElabel, KEtitle, biolevel) and /get_aop_options (aopId, aopTitle) were verified against actual api.py implementation and matched the plan's defensive multi-key lookup pattern.

## Issues Encountered

A linter/auto-formatter was reverting file writes between Read and Write operations. Resolved by staging and committing immediately after the Write tool call succeeded, before the linter could revert.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- EXPLO-01, EXPLO-02, EXPLO-03 requirements fulfilled
- Explore page live-filtering is complete; next plans in phase 04 can build on this foundation
- /api/v1/mappings AOP filter integration tested end-to-end through DataTable AJAX

## Self-Check: PASSED

- FOUND: templates/explore.html (modified with AJAX DataTable, filter controls, Coverage Gaps tab)
- FOUND: src/blueprints/main.py (explore() route simplified, dataset= removed)
- FOUND: .planning/phases/04-curator-ux-and-explore/04-03-SUMMARY.md (this file)
- FOUND: commit 774ad8a (feat(04-03): refactor explore page...)
- VERIFIED: 15 occurrences of key identifiers (serverSide, aop-filter-select, gaps-explore-content, loadCoverageGaps) in explore.html
- VERIFIED: 66 tests pass, no regressions

---
*Phase: 04-curator-ux-and-explore*
*Completed: 2026-02-21*
