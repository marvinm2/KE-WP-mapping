---
phase: 04-curator-ux-and-explore
plan: 02
subsystem: ui
tags: [javascript, css, jquery, select2, details-summary, ke-context, filter-chips]

# Dependency graph
requires:
  - phase: 04-01
    provides: /api/ke_detail/<ke_id> endpoint with ke_title, ke_description, biolevel, ke_page, aop_membership
provides:
  - Unified collapsible KE context panel rendered from /api/ke_detail/ (no SPARQL per selection)
  - URL param ?ke_id= pre-fill: deep-link from coverage gap view to pre-selected KE
  - Filter chip CSS classes (.filter-chips, .filter-chip, .filter-chip-remove, .filter-chips-clear)
  - .ke-context-title CSS for prominent summary title with toggle arrow
affects:
  - 04-03 (uses filter-chip CSS; Map button can now deep-link with ?ke_id=)
  - Any future curator workflows that reference #ke-context-panel or #ke-preview

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Native HTML <details>/<summary> element for collapsible panels (no JS toggle needed)"
    - "URL param consumed in init(), cleaned with history.replaceState, applied after Select2 via setTimeout"
    - "removeKEContextPanel() cleans both #ke-context-panel and legacy #ke-preview in one call"

key-files:
  created: []
  modified:
    - static/js/main.js
    - static/css/main.css

key-decisions:
  - "Single loadKEDetail() replaces showKEPreview + loadKEContext + displayKEContext — one AJAX call to /api/ke_detail/ per KE selection"
  - "Panel is a <details id=ke-context-panel> element so collapsibility is CSS-only via native HTML; existing .ke-context-panel styles apply"
  - "URL param ?ke_id= cleaned from URL immediately after read (history.replaceState) to avoid double-application on refresh"
  - "preselectedKE applied inside populateKEDropdown() after Select2 init, with 100ms setTimeout to ensure Select2 is ready"
  - "filter-chip border-radius uses 9999px literal (not var(--radius-full) which is 50% — 50% does not produce pills on rectangular elements)"

patterns-established:
  - "KE context panel pattern: <details id=ke-context-panel open> with summary.ke-context-title containing bold title + biolevel badge"
  - "URL deep-link pattern: store param in this.preselectedKE during init(), null it after use, apply in dropdown callback"

requirements-completed:
  - KE-01

# Metrics
duration: 15min
completed: 2026-02-21
---

# Phase 4 Plan 02: Unified KE Context Panel Summary

**Collapsible KE context panel using native `<details>` element with title, biolevel badge, description, AOP membership list, and AOP-Wiki link fetched from `/api/ke_detail/`; plus URL param `?ke_id=` deep-link pre-fill**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-21T14:00:00Z
- **Completed:** 2026-02-21T14:15:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Replaced three-function split (`showKEPreview` + `loadKEContext` + `displayKEContext`) with unified `loadKEDetail()` + `renderKEContextPanel()` + `removeKEContextPanel()`
- Panel is a `<details>` element (starts `open`); clicking the `<summary>` collapses/expands natively — no JS toggle needed
- AOP membership loaded from `/api/ke_detail/<ke_id>` (pre-computed local data, no live SPARQL per KE selection)
- URL param `?ke_id=` consumed in `init()`, URL cleaned immediately, value applied after Select2 initializes — enables Map button deep-link from 04-03 coverage gaps view
- Added `.ke-context-title` CSS with triangle toggle arrows and `.filter-chip*` CSS classes for use by 04-03 explore table

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace split KE preview/context with unified collapsible panel** - `205be21` (feat)
2. **Task 2: Add CSS for KE context panel title and filter chips** - `0b84277` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `static/js/main.js` - New loadKEDetail(), renderKEContextPanel(), removeKEContextPanel(); URL pre-fill in init() and populateKEDropdown(); removed showKEPreview/loadKEContext/displayKEContext
- `static/css/main.css` - Added .ke-context-panel > summary.ke-context-title styles and complete .filter-chips/.filter-chip/.filter-chip-remove/.filter-chips-clear ruleset

## Decisions Made

- Used `<details id="ke-context-panel">` as the panel element itself (not a wrapper div) so the `.ke-context-panel` class applies directly to the collapsible element
- `filter-chip` border-radius uses `9999px` literal instead of `var(--radius-full)` because `--radius-full` is `50%` which makes circles on square elements, not pill shapes
- `hideKEPreview()` updated to delegate to `removeKEContextPanel()` (backward compat for any reset paths that still call it)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Server startup required `DATABASE_PATH` env var set as absolute path for local dev bash context (`.env` relative path `ke_wp_mapping.db` resolves correctly when CWD matches project root; used `DATABASE_PATH=/abs/path python app.py` for verification)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- KE context panel complete (KE-01 closed); curator now sees full KE context in mapping workflow without leaving the page
- Filter chip CSS ready for 04-03 explore table active-filter display
- `?ke_id=` URL param deep-link ready for 04-03 Map button implementation
- 04-03 (explore AJAX DataTable) already committed; this plan fills the frontend dependency it needed

---
*Phase: 04-curator-ux-and-explore*
*Completed: 2026-02-21*
