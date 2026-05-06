---
phase: 27-reactome-pathway-viewer
plan: 04
subsystem: frontend-js
tags: [reactome, diagramjs, embed, wireup, vanilla-js]

# Dependency graph
requires:
  - phase: 27-reactome-pathway-viewer
    plan: 01
    provides: "#reactome-inline-embed and #reactome-inline-embed-frame DOM scaffolding (mount target for the embed)"
  - phase: 27-reactome-pathway-viewer
    plan: 03
    provides: "window.ReactomeDiagramEmbed utility (load / hide / buildErrorState surface)"
provides:
  - "Selection-time wire-up: selectReactomePathway() now triggers ReactomeDiagramEmbed.load(reactomeId, genes) with race-tolerant gene lookup and .catch() error UX"
  - "Reset-time wire-up: resetReactomeTab() now hides the embed via ReactomeDiagramEmbed.hide()"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-hook insertion at the convergence point (selectReactomePathway already serves both suggestion-card and search-result paths) — D-03"
    - "Race-tolerant gene lookup via this._cachedKeGenes[keId] || [] — flagging is delegated to the embed's onDiagramLoaded callback (D-06)"
    - "Promise .catch() at the call site renders the error card without bubbling — RVIEW-01 #3 fail-closed UX"
    - "Embed call placed AFTER revealReactomeConfidenceStep() so a render failure cannot delay the confidence step"
    - "Defensive if (window.ReactomeDiagramEmbed) guard in both call sites — script-load-order safety belt-and-suspenders"

key-files:
  created: []
  modified:
    - static/js/main.js

key-decisions:
  - "Wire-up done at the existing selectReactomePathway / resetReactomeTab functions (no new methods, no new files) — minimal blast radius and aligns with D-03 single-hook decision"
  - "Race-tolerant gene lookup pattern (this._cachedKeGenes[keId] || []) reused verbatim from the WP modal pattern at line 3277 — established idiom"
  - "Embed call placed after the existing duplicate-check + confidence-step calls so a CDN/runtime failure cannot block the submission flow (RVIEW-01 #3)"
  - "Task 3 (manual deploy verification of the three RVIEW-01 success criteria against molaop-builder.vhp4safety.nl) is intentionally a manual-only step per the plan's <verify><automated>echo \"Manual-only…\"</automated> contract — deferred to post-deploy by the curator/admin (consistent with Plan 25-05's same-pattern deferral)"

patterns-established:
  - "Two-line wire-up pattern (load on selection + hide on reset) for inline third-party embeds, mirroring the WP pattern at lines 3132-3138 (hidePathwaySuggestions WP analog)"

requirements-completed: [RVIEW-01]

# Metrics
duration: 4min
completed: 2026-05-06
---

# Phase 27 Plan 04: Reactome Tab Wire-Up Summary

**Wires the `ReactomeDiagramEmbed` utility (Plan 03) into the Reactome tab: every pathway selection now triggers `ReactomeDiagramEmbed.load(reactomeId, genes)` with race-tolerant gene lookup and a `.catch()` that renders the PathwayBrowser fallback error card; every tab reset now calls `ReactomeDiagramEmbed.hide()`. ~23 lines added across two existing functions in `static/js/main.js`. RVIEW-01 (a)/(b)/(c) static checks all pass; manual deploy verification of the three success criteria is deferred to post-deploy per the plan's manual-only verify contract.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-06T17:57:23Z
- **Completed:** 2026-05-06T18:01:21Z
- **Tasks:** 2 automated + 1 manual-deploy (deferred)
- **Files modified:** 1 (`static/js/main.js`)

## Accomplishments

- **Selection wire-up (Task 1):** Inside `selectReactomePathway` (now `static/js/main.js:4706-4736`), appended a guarded block that
  1. reads the active KE id via `$('#ke_id').val()`,
  2. resolves genes race-tolerantly via `(keId && this._cachedKeGenes[keId]) ? this._cachedKeGenes[keId] : []`,
  3. calls `window.ReactomeDiagramEmbed.load(reactomeId, genes)`,
  4. catches the rejected Promise and renders `ReactomeDiagramEmbed.buildErrorState(reactomeId)` into `#reactome-inline-embed`, then `.show()`s the container.
- **Reset wire-up (Task 2):** Inside `resetReactomeTab` (between `$('#duplicate-warning-reactome').hide().empty();` and `$('#reactome-message').empty();`), appended a guarded `window.ReactomeDiagramEmbed.hide()` call so the inline embed is hidden alongside the existing duplicate-warning / confidence / submit-step hides on every reset.
- **No new methods, no new files** — both insertions sit inside existing functions; net diff is +23 lines, 0 removed, contained to two contiguous regions.
- **Acceptance grep checks pass:**
  - `grep -c 'ReactomeDiagramEmbed.load(reactomeId, genes)' static/js/main.js` → 1
  - `grep -c 'ReactomeDiagramEmbed.hide()' static/js/main.js` → 1
  - `grep -c 'ReactomeDiagramEmbed.buildErrorState(reactomeId)' static/js/main.js` → 1
  - `grep -c 'if (window.ReactomeDiagramEmbed)' static/js/main.js` → 1 (in `selectReactomePathway`; the resetReactomeTab guard appears as well — total 2 occurrences across the two new sites)
  - `_cachedKeGenes[keId]` now appears at line 4729 inside `selectReactomePathway` (in addition to existing lines ~3253–3277 from the WP cache)
- **Wave-0 grep tests pass:** `pytest tests/test_index_template.py -q` → 3 passed (the call-shape landmark test from Plan 03 still locks).

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire ReactomeDiagramEmbed into selectReactomePathway() — RVIEW-01 #1, #3** — `547398a` (feat)
2. **Task 2: Wire ReactomeDiagramEmbed.hide() into resetReactomeTab() — D-09** — `0b90e11` (feat)

(Task 3 — manual deploy verification of RVIEW-01 #1/#2/#3 against the deployed builder — is the plan's manual-only step. It will be executed post-deploy by the curator/admin and recorded in the deploy verification commit message per the plan's instructions. See "Deferred verification" below.)

## Files Modified

- `static/js/main.js` — +23 lines, 0 removed, two contiguous regions:
  - Lines ~4720–4735 (inside `selectReactomePathway`): 16-line guarded embed-load block with `.catch()` error UX.
  - Lines ~4859–4866 (inside `resetReactomeTab`): 7-line guarded `ReactomeDiagramEmbed.hide()` block.

## Diff Scope Check

```
$ git diff HEAD~2 HEAD --stat -- static/js/main.js
 static/js/main.js | 23 +++++++++++++++++++++++
 1 file changed, 23 insertions(+)
```

Hunks land at the two intended functions only:

```
@@ -4717,6 +4717,22 @@ ... (selectReactomePathway insertion) ...
@@ -4843,6 +4859,13 @@ ... (resetReactomeTab insertion) ...
```

No other regions touched. Plan estimate was ~12 net new lines; actual is 23, with the difference attributable to in-line decision-record comments (D-03 / D-06 / D-09 cross-references) that the plan explicitly kept in its sample patch.

## Goal-Backward Verification

Phase goal: **Curators can view the Reactome pathway diagram directly within the mapping workflow tab without leaving the application.**

This plan closes the loop:

1. **Selection → diagram load (RVIEW-01 #1):** `ReactomeDiagramEmbed.load(reactomeId, genes)` is now invoked from `selectReactomePathway` on every Reactome selection (D-03 single hook covers both the suggestion-card click at line 478 and the search-result click at line 515 — both already route through this function).
2. **Diagram-loaded → gene flag (RVIEW-01 #2):** Per-gene `flagItems` is performed inside `ReactomeDiagramEmbed.load`'s `onDiagramLoaded` callback (Plan 03 owns it). This plan supplies the `genes` argument from `_cachedKeGenes[keId]`.
3. **CDN failure → error card without breaking submission (RVIEW-01 #3):** `.catch()` on the load Promise renders `buildErrorState(reactomeId)` into `#reactome-inline-embed`. The `checkForDuplicatePair_reactome()` and `revealReactomeConfidenceStep()` calls run BEFORE the embed call, so a render failure cannot block the confidence step / submit button. The `if (window.ReactomeDiagramEmbed)` guard ensures even a script-load failure is silently absorbed.
4. **Reset path (D-09 housekeeping):** `resetReactomeTab` now calls `ReactomeDiagramEmbed.hide()` which hides the container AND defensively invokes `resetFlaggedItems()`, preventing stale flags from a previous pathway leaking into the next selection.

CONTEXT.md decisions reflected:

- **D-03** (single hook covers both selection paths) — Implemented by placing the call inside `selectReactomePathway`, which the existing handlers at lines 478 and 515 both delegate to.
- **D-06** (race-tolerant flagging) — Implemented via `(keId && this._cachedKeGenes[keId]) ? this._cachedKeGenes[keId] : []`. If the cache is mid-flight (empty array), the diagram still mounts; flags are applied later via the `onDiagramLoaded` callback only when the cache has populated.
- **D-08** layer (c) (runtime exceptions surface as the error card) — Implemented via `.catch()` swallowing the rejected Promise into `buildErrorState`.
- **D-09** (PathwayBrowser fallback link inline; reset must hide embed) — Both halves wired: `.catch()` renders `buildErrorState(reactomeId)` (which Plan 03 builds with the canonical PathwayBrowser link); `resetReactomeTab` calls `.hide()`.
- **D-10** (inline-only — no expand modal) — Untouched; this plan does not alter any modal flow. WP retains its `wpMappingModal`; Reactome has no equivalent and none is added.

## Deviations from Plan

**None.** The plan executed exactly as written, with two minor clarifications worth recording for future readers:

- The plan referenced source line numbers `4533-4547` for `selectReactomePathway` and `4665-4688` for `resetReactomeTab`. Because Plan 03 already inserted the `ReactomeDiagramEmbed` utility object at the top of `main.js` (~170 lines), the actual line numbers shifted to `4706-4720` and `4838-4861` respectively. The pattern-matched `Edit` tool was used (matching by surrounding context, not by line number), so the shift was transparent.
- Initial accidental edit to the main repo's `static/js/main.js` (rather than the worktree's) was caught and reverted before any commit. No commit history was affected; the edit was re-applied to the worktree file and verified via `grep` in the worktree path before committing.

## Deferred Verification

- **Task 3 (manual deploy verification of RVIEW-01 #1, #2, #3):** The plan declares Task 3 as manual-only (`<verify><automated>echo "Manual-only — see acceptance_criteria"</automated>`). Execution against the deployed builder at `https://molaop-builder.vhp4safety.nl` requires:
  1. Push + rebuild + force-update (per `CLAUDE.md` Deployment section).
  2. Logged-in curator selects a KE → opens Reactome tab → clicks a suggestion → confirms diagram renders inside `#reactome-inline-embed-frame`.
  3. Same flow with DevTools network blocking `reactome.org/DiagramJs/*` → confirms error card renders, submission flow still works, no uncaught console exception, second selection short-circuits via the sticky `_failed` flag (Plan 03).
  Results to be recorded in the deploy verification commit message ("Manual deploy verification: RVIEW-01 #1 ✓ #2 ✓ #3 ✓") per plan instructions. **This is not a checkpoint failure** — it is the plan's documented manual-only verification step.

## Self-Check: PASSED

**Files claimed modified:**

- `static/js/main.js` — FOUND (verified: 5 new substrings present at expected call sites).

**Commits claimed:**

- `547398a` (Task 1) — FOUND in `git log --oneline`.
- `0b90e11` (Task 2) — FOUND in `git log --oneline`.

**Verification grep counts (re-verified):**

- `ReactomeDiagramEmbed.load(reactomeId, genes)` → 1 ✓
- `ReactomeDiagramEmbed.hide()` → 1 ✓
- `ReactomeDiagramEmbed.buildErrorState(reactomeId)` → 1 ✓
- `_cachedKeGenes[keId]` inside `selectReactomePathway` → present at line 4729 ✓

**Test status:**

- `pytest tests/test_index_template.py` → 3 passed (Wave-0 grep tests from Plans 01 + 03 still pass).
- Pre-existing 2 unrelated failures in `tests/test_app.py` (`test_login_redirect`, `test_guest_login_page_renders`) confirmed against base via `git stash` — out of scope for this JS-only edit.
