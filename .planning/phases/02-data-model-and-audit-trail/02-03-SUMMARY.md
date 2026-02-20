---
phase: 02-data-model-and-audit-trail
plan: 03
subsystem: ui
tags: [jquery, duplicate-check, confidence, suggestion-score, live-validation]

# Dependency graph
requires:
  - phase: 02-02
    provides: /check enriched response with blocking_type, /check_go_entry enriched response, /flag_proposal_stale endpoint with mapping_type param, check_mapping_exists_with_proposals and check_go_mapping_exists_with_proposals model methods
provides:
  - Live KE-WP duplicate check firing on pathway selection via checkForDuplicatePair() posting to /check
  - Live KE-GO duplicate check firing on GO term selection via checkForDuplicatePair_go() posting to /check_go_entry
  - Inline warning cards for both forms showing approved_mapping and pending_proposal blocking types
  - Flag-as-stale button wired to /flag_proposal_stale with correct mapping_type ('wp' or 'go')
  - Confidence select-button group (#confidence-confirm section) shown after assessment completes
  - Client-side submit guard blocking form submission when confidence_level is empty
  - suggestion_score captured from data-score attribute on suggestion card clicks
affects:
  - 03-public-api
  - future curator UX phases

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Live duplicate check pattern: fire AJAX check on field selection (not form submit), render inline warning card with action buttons"
    - "Delegated event binding for dynamically injected warning card buttons using .off().on() pattern"
    - "Confidence confirmation step: auto-populate btn-group from assessment result, allow curator override"

key-files:
  created: []
  modified:
    - templates/index.html
    - static/js/main.js

key-decisions:
  - "checkForDuplicatePair() fires inside setTimeout after pathway selection events to ensure wp_id hidden field is updated before AJAX call"
  - "suggestion_score cleared to empty string (not zero) for search/browse selections — server receives NULL which is intentional"
  - "data-score attribute added to suggestion-item HTML using scores.final_score as primary source, falling back to confidence_score — enables score capture without a second AJAX call"
  - "Browse panel pathway selection also fires checkForDuplicatePair() and clears suggestion_score since it is a manual selection"
  - "confidence-confirm section is reset (hidden, buttons deselected) in both resetGuide() and resetForm() to avoid stale state"

patterns-established:
  - "Inline warning card pattern: renderDuplicateWarning(result) and renderDuplicateWarning_go(result) produce parallel card HTML for KE-WP and KE-GO forms respectively"
  - "mapping_type='wp' vs mapping_type='go' on flag-stale buttons determines which proposal model is used in /flag_proposal_stale"

requirements-completed:
  - CURAT-02
  - CURAT-03

# Metrics
duration: 9min
completed: 2026-02-20
---

# Phase 2 Plan 03: Confidence Select Step and Live Duplicate Check Summary

**jQuery live duplicate checks on pathway/GO selection with inline warning cards and confidence select-button confirmation step added to curator forms**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-20T13:58:19Z
- **Completed:** 2026-02-20T14:07:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Live KE-WP duplicate check fires on pathway selection (suggestion click, search select, browse panel change) and renders inline warning cards with Submit Revision or Flag as Stale CTAs
- Live KE-GO duplicate check fires when curator clicks a GO suggestion; warning card uses `mapping_type='go'` on the flag-stale button for correct server routing
- Confidence select-button group (`#confidence-confirm` section) appears after assessment completes with the recommended level pre-selected; client-side guard blocks form submission if no selection made
- Suggestion score captured from `data-score` attribute on clicked suggestion items into `#suggestion_score` hidden field; cleared for search/browse selections

## Task Commits

Each task was committed atomically:

1. **Task 1: Add confidence select-button step and suggestion_score hidden field to index.html** - `1744219` (feat)
2. **Task 2: Wire live duplicate check, inline preview card, and confidence enforcement in main.js** - `86bccf8` (feat)

## Files Created/Modified

- `/home/marvin/Documents/Services/Ke-gene-mapping/KE-WP-mapping/templates/index.html` - Added `#duplicate-warning` (KE-WP form), `#suggestion_score` hidden field, `#confidence-confirm` section with `#confidence-select-group` btn-group, `#duplicate-warning-go` (GO form)
- `/home/marvin/Documents/Services/Ke-gene-mapping/KE-WP-mapping/static/js/main.js` - Added `checkForDuplicatePair()`, `renderDuplicateWarning()`, `checkForDuplicatePair_go()`, `renderDuplicateWarning_go()` methods; wired confidence select-button group; added confidence submit guard; added `data-score` to suggestion-item HTML; updated `selectSuggestedPathway()`, `selectSearchResult()`, `handlePathwaySelection()`, `selectGoTerm()`, `populateStep4Results()`, `resetGuide()`, `resetForm()`, and global `evaluateConfidence()`

## Decisions Made

- `checkForDuplicatePair()` is called inside `setTimeout(..., 50-100ms)` after pathway selection to ensure the `#wp_id` hidden field is updated (via `updateSelectedPathways()`) before the AJAX POST fires
- `suggestion_score` is set to empty string (not 0) for browse/search selections — this maps to NULL on the server, which is intentional per the plan spec
- `data-score` added to suggestion-item HTML using `suggestion.scores.final_score` as the primary source with fallback to `suggestion.confidence_score`; this avoids an additional AJAX round-trip to get the score

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added data-score attribute to suggestion-item HTML**
- **Found during:** Task 2 (suggestion score capture)
- **Issue:** Plan specified `$(this).data('score')` but suggestion-item elements had no `data-score` attribute — only `data-gene-score` (the gene overlap percentage, not the combined final score)
- **Fix:** Added `data-score="${(suggestion.scores && suggestion.scores.final_score !== undefined) ? suggestion.scores.final_score : (suggestion.confidence_score || '')}"` to the suggestion-item HTML template at build time
- **Files modified:** `static/js/main.js` (suggestion HTML template string)
- **Verification:** `grep -n "data-score" static/js/main.js` shows attribute in suggestion-item HTML
- **Committed in:** `86bccf8` (Task 2 commit)

**2. [Rule 2 - Missing Critical] Reset confidence-confirm and duplicate-warning in resetGuide()/resetForm()**
- **Found during:** Task 2 (state management review)
- **Issue:** Plan did not specify cleanup of the new UI elements on form reset; leaving them visible/populated would cause stale state when a curator starts a new mapping
- **Fix:** Added `$('#confidence-confirm').hide()`, `$('#confidence-select-group .btn-option').removeClass('selected')`, `$('#confidence-select-error').hide()`, and `$('#duplicate-warning').hide().empty()` to `resetGuide()`; added `$('#suggestion_score').val('')` and `$('#duplicate-warning').hide().empty()` to `resetForm()`
- **Files modified:** `static/js/main.js`
- **Committed in:** `86bccf8` (Task 2 commit)

**3. [Rule 1 - Bug] Fixed existing submit guard to not block when confidence_level is set**
- **Found during:** Task 2 (form submit guard implementation)
- **Issue:** The existing guard `if (!formData.connection_type || !formData.confidence_level)` combined two checks and would show a generic message even when only one was missing
- **Fix:** Split the guard: confidence_level check comes first and shows the specific `#confidence-select-error` inline error with scroll-to; connection_type guard remains separate with its own message
- **Files modified:** `static/js/main.js` (handleFormSubmission)
- **Committed in:** `86bccf8` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 missing critical attribute, 1 missing state reset, 1 bug fix)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep.

## Issues Encountered

- The gunicorn process running on port 5000 is owned by a different user and could not be reloaded during development; template changes verified via Jinja2 direct rendering and the Flask test client (which confirmed all 5 new HTML elements present). JS syntax verified via `node --check`.
- Pre-existing test failures (5 tests in `test_app.py`) are unrelated to this plan's changes — confirmed by stashing changes and re-running tests with identical results.

## Next Phase Readiness

- Curator-facing duplicate detection and confidence confirmation are complete
- Server-side validation from 02-02 and UI enforcement from this plan form a complete guard for CURAT-02 and CURAT-03
- Phase 3 (Public API) can proceed — no blockers from this plan

---
*Phase: 02-data-model-and-audit-trail*
*Completed: 2026-02-20*
