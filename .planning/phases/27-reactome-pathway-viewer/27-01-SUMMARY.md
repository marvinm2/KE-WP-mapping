---
phase: 27-reactome-pathway-viewer
plan: 01
subsystem: ui
tags: [reactome, diagramjs, jinja, html, pytest]

# Dependency graph
requires:
  - phase: 25-proposal-workflow-and-admin-ui
    provides: "#reactome-tab-content section in templates/index.html (Plan 25-04 added the 3rd tab markup)"
provides:
  - "#reactome-inline-embed wrapper (hidden by default) and #reactome-inline-embed-frame (280px-tall mount point) in templates/index.html"
  - "tests/test_index_template.py — Wave-0 Jinja-render smoke tests for the new block"
affects:
  - 27-03-reactome-diagram-utility (consumes #reactome-inline-embed-frame as DiagramJS placeHolder)
  - 27-04-reactome-tab-wireup (toggles #reactome-inline-embed visibility on pathway selection)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mirror WP analog block (#wp-inline-embed) but drop expand-modal button per D-10"
    - "Hidden-by-default DOM scaffold landed before JS that mounts into it (Wave-0 prerequisite for Wave-2 JS work)"

key-files:
  created:
    - tests/test_index_template.py
  modified:
    - templates/index.html

key-decisions:
  - "Block indentation uses 8 spaces (matching #duplicate-warning-reactome and #reactome-confidence-guide siblings) — not 12 spaces as the plan's read_first text mentioned, because the actual surrounding markup is at 8-space depth"
  - "No #reactome-selected-pathway-banner sibling added (Reactome tab has no banner equivalent in current design)"
  - "Two pytest tests created (presence + placement) rather than one combined test — keeps each assertion focused per Wave-0 validation row"

patterns-established:
  - "Phase 27 inline-embed pattern: hidden wrapper > 280px frame > nothing else. No expand button, no banner. DiagramJS native toolbar covers zoom/pan/fit-to-screen (D-10)."

requirements-completed: [RVIEW-01]

# Metrics
duration: 2min
completed: 2026-05-06
---

# Phase 27 Plan 01: Reactome Inline-Embed DOM Scaffold Summary

**Static `#reactome-inline-embed` mount point (280px hidden frame) added to `templates/index.html` between `#duplicate-warning-reactome` and `#reactome-confidence-guide`, with two passing Wave-0 pytest smoke tests asserting block presence and ordering.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-06T17:38:34Z
- **Completed:** 2026-05-06T17:40:46Z
- **Tasks:** 2
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments

- Inserted hidden `#reactome-inline-embed` wrapper (display:none) and `#reactome-inline-embed-frame` (width:100% height:280px position:relative) at lines 359-362 of `templates/index.html`, sandwiched between `#duplicate-warning-reactome` (line 357) and `#reactome-confidence-guide` (line 364)
- Added `tests/test_index_template.py` with two passing tests covering RVIEW-01 (a):
  - `test_reactome_inline_embed_block_present` — both IDs render and 280px height appears in the body
  - `test_reactome_inline_embed_block_placement` — DOM order is `duplicate-warning-reactome < reactome-inline-embed < reactome-confidence-guide`
- Verified D-10 compliance: only one `wp-expand-modal-btn` occurrence remains in `templates/index.html` (the WP one) — Reactome scaffold deliberately omits an expand-modal button

## Task Commits

Each task was committed atomically:

1. **Task 1: Add #reactome-inline-embed scaffold to index.html** — `e68fa95` (feat)
2. **Task 2: Create Wave-0 pytest smoke test for block presence** — `60c489e` (test)

## Files Created/Modified

- `templates/index.html` — Added 5 lines (4 markup + 1 trailing blank) inside `#reactome-tab-content`. Hidden wrapper + 280px frame mount point. No script tag, no inline JS, no event handlers.
- `tests/test_index_template.py` — New file. 33 lines. Two pytest functions using the existing module-level `client` fixture from `tests/conftest.py`.

## Lines Inserted (post-insert numbering)

```
359        <!-- Inline Reactome diagram embed (auto-loads when a pathway is selected) -->
360        <div id="reactome-inline-embed" style="display:none; margin-top: 12px;">
361            <div id="reactome-inline-embed-frame" style="width:100%; height:280px; position:relative;"></div>
362        </div>
```

## Verification Evidence

```
$ grep -c 'id="reactome-inline-embed"' templates/index.html       → 1
$ grep -c 'id="reactome-inline-embed-frame"' templates/index.html → 1
$ grep -c 'wp-expand-modal-btn' templates/index.html              → 1  (WP only — D-10)
$ awk '/id="duplicate-warning-reactome"/{a=NR} /id="reactome-inline-embed"/{b=NR} /id="reactome-confidence-guide"/{c=NR} END{exit !(a<b && b<c)}' templates/index.html
  → exit 0 (positions: 357 < 360 < 364)
$ PYTHONPATH=. pytest tests/test_index_template.py -v
  → 2 passed
```

## Decisions Made

- Used 8-space indentation (matching `#duplicate-warning-reactome` and `#reactome-confidence-guide` siblings), not 12-space as suggested by the plan's `read_first` text. The actual surrounding markup is at 8-space depth — the plan's "12 spaces / 3 levels" comment was based on a different reading point.
- Followed plan exactly otherwise: no banner div, no expand-modal button, no script tag. The block is purely a passive DOM target for Plan 03's JS utility.

## Deviations from Plan

None — plan executed exactly as written. The indentation note above is a minor read_first/reality reconciliation, not a structural deviation; the rendered HTML matches the plan's specified block shape verbatim.

## Issues Encountered

- pytest emits a `FAIL Required test coverage of 45% not reached` warning when running only `tests/test_index_template.py` (because `--cov` is configured globally and a single-file test run doesn't exercise the full codebase). Pytest still exits 0 — this is expected behaviour for partial test runs and is out of scope for this plan (project-wide coverage gap is pre-existing, see PROJECT.md "Known tech debt"). Logged here, no fix attempted.

## Next Phase Readiness

- Plan 03 (Reactome diagram utility) can now mount DiagramJS into `#reactome-inline-embed-frame` via `placeHolder: 'reactome-inline-embed-frame'`. Pitfall 6 reminder: Plan 03 must reveal the `#reactome-inline-embed` wrapper (set `display:block` or remove `display:none`) BEFORE calling `Reactome.Diagram.create()` — DiagramJS reads container width during construction, and a hidden parent yields zero width.
- Plan 04 (tab wire-up) has a stable DOM target with a deterministic frame ID (`reactome-inline-embed-frame`) — no race window between markup insertion and JS access.
- No blockers introduced. RVIEW-01 (a) Wave-0 verification row is satisfied.

## Self-Check: PASSED

Verified files and commits exist:
- `templates/index.html` — modified, committed in `e68fa95`
- `tests/test_index_template.py` — created, committed in `60c489e`
- Both commit hashes appear in `git log --oneline -5`

---
*Phase: 27-reactome-pathway-viewer*
*Plan: 01*
*Completed: 2026-05-06*
