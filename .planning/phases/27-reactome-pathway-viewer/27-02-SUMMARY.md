---
phase: 27-reactome-pathway-viewer
plan: 02
subsystem: ui
tags: [css, reactome-embed, design-tokens, vhp4safety-palette, parity]

# Dependency graph
requires:
  - phase: 26-public-api-and-exports
    provides: Reactome data surfaces (mapper page, explore tab) — context for where the embed will render
provides:
  - .reactome-embed-loading CSS rule (loading state for ReactomeDiagramEmbed)
  - .reactome-embed-error CSS rule (error card for ReactomeDiagramEmbed)
  - .reactome-embed-error a CSS rule (link color inside error card)
affects: [27-03-reactome-diagram-embed, 27-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "WP→Reactome selector parity (only the prefix changes wp-embed- → reactome-embed-)"
    - "Reuse of design tokens (--color-text-muted, --color-primary-blue) — no new colors"

key-files:
  created: []
  modified:
    - static/css/main.css

key-decisions:
  - "Mirror WP embed CSS verbatim (only selector prefix changes) — guarantees visual parity"
  - "Reuse existing design tokens; no new color literals or layout primitives introduced"
  - "Plan 03's spinner-class gotcha resolved by Plan 03 itself using existing .spinner .spinner--md inside .reactome-embed-loading (no .loading-spinner class needed)"

patterns-established:
  - "reactome-embed-* selector family — paired with the existing wp-embed-* family for inline pathway embeds"

requirements-completed: [RVIEW-01]

# Metrics
duration: 1min
completed: 2026-05-06
---

# Phase 27 Plan 02: Reactome Embed CSS States Summary

**Adds .reactome-embed-loading, .reactome-embed-error, and .reactome-embed-error a to static/css/main.css with WP-parity property values, no new tokens, ready for Plan 03's ReactomeDiagramEmbed loading and error markup.**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-05-06T17:38:48Z
- **Completed:** 2026-05-06T17:39:20Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Three new CSS selectors appended directly after the WP analog block (`static/css/main.css:1605` boundary).
- All property values byte-for-byte identical to the WP variants — only the selector prefix changes (`wp-embed-` → `reactome-embed-`).
- No new design tokens. The new rules reuse `--color-text-muted` (×2) and `--color-primary-blue` (×1) from the existing token system.
- Existing `.wp-embed-loading`, `.wp-embed-error`, and `.wp-embed-error a` rules verified untouched.

## New selectors and property values

| Selector | Properties |
| --- | --- |
| `.reactome-embed-loading` | `display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 12px; color: var(--color-text-muted);` |
| `.reactome-embed-error` | `display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 8px; color: var(--color-text-muted);` |
| `.reactome-embed-error a` | `color: var(--color-primary-blue);` |

The `gap` differs between the two block selectors (`12px` vs `8px`) — that asymmetry is inherited from the WP analog and is preserved exactly.

## Task Commits

Each task was committed atomically:

1. **Task 1: Append .reactome-embed-loading and .reactome-embed-error rules** — `69cae78` (feat)

## Files Created/Modified

- `static/css/main.css` — appended 21 lines (3 new rules) immediately after the existing `.wp-embed-error a { ... }` block and before `.wp-preview-btn`. No other edits.

## Verification (acceptance criteria)

All criteria from the plan passed:

- `grep -c '\.reactome-embed-loading' static/css/main.css` → **1** (expected 1)
- `grep -cE '\.reactome-embed-error[^-]' static/css/main.css` → **2** (expected ≥ 2: block selector + descendant `a` selector)
- `grep -c 'var(--color-text-muted)' static/css/main.css` → **28** (baseline 26 → delta +2; expected exactly +2)
- `grep -c 'var(--color-primary-blue)' static/css/main.css` → **79** (baseline 78 → delta +1; expected exactly +1)
- `awk '/\.reactome-embed/,/^\}/' static/css/main.css | grep -E '#[0-9a-fA-F]{3,8}|rgb\(|hsl\('` → no matches (no new color literals introduced)
- `.wp-embed-loading`, `.wp-embed-error`, `.wp-embed-error a` rules — confirmed unchanged on re-read of the surrounding block

## Decisions Made

None — followed plan as specified. The plan dictated verbatim CSS to insert; the only judgement call was placement (immediately after `.wp-embed-error a { ... }` and before `.wp-preview-btn`), which the plan explicitly specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Notes for Plan 03

The plan flagged an informational gotcha for the downstream consumer:

- The codebase has `.spinner` and `.spinner--md` (lines ~2247–2251) but **no** `.loading-spinner` class.
- Plan 03's injected loading markup must use `<span class="spinner spinner--md"></span>` inside the `.reactome-embed-loading` wrapper — **not** `<div class="loading-spinner">` (which would mirror a latent WP gap rather than fix it).
- This plan did not redefine spinner classes; the spinner-class gotcha is resolved by Plan 03's markup choice.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 03 (`ReactomeDiagramEmbed` JS utility) can now reference the `.reactome-embed-loading` and `.reactome-embed-error` class names from injected HTML and rely on visual parity with the existing WP inline embed.
- No blockers.

## Self-Check: PASSED

- `static/css/main.css` — FOUND (modified, 3 new rules present)
- Commit `69cae78` — FOUND in `git log --all`

---
*Phase: 27-reactome-pathway-viewer*
*Plan: 02*
*Completed: 2026-05-06*
