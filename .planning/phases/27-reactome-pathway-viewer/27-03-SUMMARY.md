---
phase: 27-reactome-pathway-viewer
plan: 03
subsystem: frontend-js
tags: [reactome, diagramjs, lazy-load, embed, utility, vanilla-js]

# Dependency graph
requires:
  - phase: 27-reactome-pathway-viewer
    plan: 01
    provides: "#reactome-inline-embed and #reactome-inline-embed-frame DOM scaffolding"
  - phase: 27-reactome-pathway-viewer
    plan: 02
    provides: ".reactome-embed-loading / .reactome-embed-error CSS rules consumed by buildErrorState()"
provides:
  - "window.ReactomeDiagramEmbed utility (loadScriptOnce, init, load, flagGenes, hide, buildErrorState)"
  - "Wave-0 grep test (test_reactome_diagram_embed_call_shape) asserting 8 call-shape landmarks"
affects: [27-04]

# Tech tracking
tech-stack:
  added:
    - "Reactome DiagramJS v2 (CDN, lazy-loaded, un-versioned diagram.nocache.js)"
  patterns:
    - "PathwayEmbed-shaped utility object with module export at window.ReactomeDiagramEmbed"
    - "Memoized Promise lazy-script-loader with three-layer failure detection (script.onerror + 10s setTimeout + try/catch)"
    - "Sticky _failed flag short-circuits subsequent loads after hard CDN failure (D-08)"
    - "Single Diagram instance reused across pathway swaps (DiagramJS exports no destroy())"
    - "Per-gene flagItems loop via forEach (DiagramJS flagItems takes a single string, not array)"
    - "HTML-escaped Reactome stable ID interpolation in failure-state HTML"

key-files:
  created: []
  modified:
    - static/js/main.js
    - tests/test_index_template.py

key-decisions:
  - "Utility object lives in main.js between PathwayEmbed and class KEWPApp — minimal blast radius, mirrors existing WP analog placement"
  - "loadScriptOnce + window.onReactomeDiagramReady global ack — RESEARCH §2.6 finding that script.onload fires before Reactome.Diagram.create is callable"
  - "buildErrorState HTML-escapes the reactomeId via String.replace even though server-validated ^R-HSA-[0-9]+$ IDs cannot contain metacharacters (defensive on principle)"
  - "Native DiagramJS toolbar preserved via toHide:[] (D-10) — no expand modal counterpart to wpMappingModal"
  - "Wave-0 test reads main.js from disk via pathlib (no Jinja render, no JS runtime, just static substring assertions)"

patterns-established:
  - "Lazy-CDN-load + memoized-Promise pattern for third-party JS bundles where SRI is infeasible"
  - "Three-layer failure detection idiom (.onerror + setTimeout + try/catch) for fail-fast UX"
  - "Wave-0 grep-test-against-bundled-JS pattern: pytest verifies static/js/main.js call-shape compliance without exercising the JS runtime"

requirements-completed: [RVIEW-01]

# Metrics
duration: 4min
completed: 2026-05-06
---

# Phase 27 Plan 03: ReactomeDiagramEmbed JS Utility Summary

**Adds the ReactomeDiagramEmbed utility object to static/js/main.js with lazy CDN script injection, three-layer failure detection, single-instance Diagram reuse (D-04), per-gene flagItems loop (D-05 corrected), and PathwayBrowser fallback error UX — plus an 8-landmark Wave-0 grep test in tests/test_index_template.py that locks the call-shape against future regressions.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-06T17:48:20Z
- **Completed:** 2026-05-06T17:51:42Z
- **Tasks:** 2
- **Files modified:** 2
- **Lines added:** 173 in static/js/main.js, 25 in tests/test_index_template.py

## Accomplishments

- **Task 1 (feat):** Inserted the `ReactomeDiagramEmbed` object between `window.PathwayEmbed = PathwayEmbed;` (line 65) and `class KEWPApp {` (now at line 240). Net 173 added lines, zero edits to existing code. The utility exports six entry points (`loadScriptOnce`, `init`, `flagGenes`, `load`, `hide`, `buildErrorState`) and three private constants (`_CDN_URL`, `_CONTAINER_ID`, `_FRAME_ID`, `_LOAD_TIMEOUT_MS`). `window.ReactomeDiagramEmbed` is the single export consumed by Plan 04.
- **Task 2 (test):** Appended `test_reactome_diagram_embed_call_shape` to `tests/test_index_template.py` after the existing Plan 01 placement test. The new test reads `static/js/main.js` from disk and asserts 8 call-shape landmarks. All 3 tests in `tests/test_index_template.py` now pass.
- **No regression:** `pytest tests/test_index_template.py -q` — `3 passed`. Existing Plan 01 Task 2 tests untouched.
- **Static check:** All 11 acceptance-criteria grep landmarks present in main.js after the insertion. Insertion order verified: `window.PathwayEmbed = PathwayEmbed;` at line 65 → utility body → `class KEWPApp {` at line 240.

## Verification (acceptance criteria)

All Task 1 grep checks return ≥ 1:

| Landmark                                                         | Count |
| ---------------------------------------------------------------- | ----- |
| `window.ReactomeDiagramEmbed = ReactomeDiagramEmbed`             | 1     |
| `https://reactome.org/DiagramJs/diagram/diagram.nocache.js`      | 1     |
| `window.onReactomeDiagramReady`                                  | 1     |
| `Reactome.Diagram.create(`                                       | 1     |
| `flagItems(`                                                     | 1     |
| `resetFlaggedItems(`                                             | 3     |
| `reactome-embed-error`                                           | 1     |
| `reactome.org/PathwayBrowser/#/`                                 | 1     |
| `_LOAD_TIMEOUT_MS: 10000`                                        | 1     |
| `placeHolder: this._FRAME_ID`                                    | 1     |
| Insertion order (PathwayEmbed export < utility < class KEWPApp)  | OK    |

Task 2:

- `pytest tests/test_index_template.py::test_reactome_diagram_embed_call_shape -q` → **passed**
- `pytest tests/test_index_template.py -q` → **3 passed** (Plan 01's 2 tests + Plan 03's new test)

## Key Behaviours Implemented

- **Lazy CDN load (D-07):** First `loadScriptOnce()` call injects `<script src="https://reactome.org/DiagramJs/diagram/diagram.nocache.js">` into `<head>`, returns a Promise that resolves on the `window.onReactomeDiagramReady` global. Subsequent calls return the same memoized Promise.
- **Three-layer failure detection (D-08):** (a) `script.onerror` for hard CDN unreachable; (b) 10-second `setTimeout` fallback for stalled loads (matches WP iframe timeout at main.js:43); (c) `try/catch` around `Reactome.Diagram.create()` and `loadDiagram()` for runtime exceptions.
- **Sticky failure flag (D-08):** `_failed = true` set on any failure path; subsequent `loadScriptOnce()` calls return `Promise.reject(new Error('Reactome CDN previously failed'))` without re-injecting.
- **Single instance reuse (D-04):** `init()` short-circuits if `_diagram` already constructed. DiagramJS exports no `destroy()`/`dispose()` method — instance lives forever.
- **Pitfall 6 fix:** `init()` calls `$('#reactome-inline-embed').show()` BEFORE `Reactome.Diagram.create()` so the widget reads non-zero width.
- **Per-gene flagItems (D-05 corrected per RESEARCH §2.3):** `flagGenes()` calls `resetFlaggedItems()` first, then iterates `genes.forEach(g => flagItems(g))`. Per-gene `try/catch` swallows individual failures so one bad symbol does not abort the loop.
- **Race-tolerant load:** `load()` calls `diagram.loadDiagram(reactomeId)` immediately, registers `onDiagramLoaded` callback that performs the flagging — caller in Plan 04 can pass possibly-empty gene cache without waiting for fetch.
- **Hide preserves instance:** `hide()` applies `$('#reactome-inline-embed').hide()` and defensively calls `resetFlaggedItems()` inside try/catch.
- **Error UX (D-09):** `buildErrorState(reactomeId)` returns HTML with class `reactome-embed-error` (styled by Plan 02) and a `target="_blank" rel="noopener noreferrer"` anchor to `https://reactome.org/PathwayBrowser/#/<id>`. `reactomeId` is HTML-escaped via `String.replace` defensively.
- **Native toolbar preserved (D-10):** `toHide: []` passed to `Reactome.Diagram.create()` keeps the GWT-bundle's zoom/pan/fit-to-screen/overlay controls. No second mount point for an expand modal.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ReactomeDiagramEmbed utility object to static/js/main.js** — `29dc506` (feat)
2. **Task 2: Append call-shape grep test to tests/test_index_template.py** — `130e52b` (test)

## Files Created/Modified

- `static/js/main.js` — 173 lines added between line 65 (`window.PathwayEmbed = PathwayEmbed;`) and the `class KEWPApp {` declaration. Single contiguous insertion. No other regions touched.
- `tests/test_index_template.py` — 25 lines appended after `test_reactome_inline_embed_block_placement`. Existing Plan 01 tests byte-identical.

## Decisions Made

None outside the plan — followed all CONTEXT.md decisions (D-04, D-05, D-06, D-07, D-08, D-09, D-10) verbatim. The plan dictated almost-verbatim JS source; the only translation was decoding the `<action>` block's XML-entity-escaped quotes (`&lt;`, `&gt;`, `&amp;`, `&quot;`) back to literal characters in the JS source (per the plan's HTML-entity note).

## Deviations from Plan

None — plan executed exactly as written.

The plan estimated 120-150 added lines; actual is 173 lines. The delta comes from the JSDoc comment block above the utility (mandatory per the plan's "comments are mandatory because the call sequence is non-obvious"), the multi-line constructor call, and per-method JSDoc. No behavioural deviation; the extra lines are documentation.

## Issues Encountered

None. Both tasks completed in the order specified in the plan, both pytest runs went green on first execution, all 11 grep landmarks present after the single insertion.

## Notes for Plan 04

The wire-up plan can rely on:

- **`window.ReactomeDiagramEmbed.load(reactomeId, genes)`** — single-call entrypoint that (a) lazy-loads the CDN bundle on first use, (b) shows the parent container, (c) constructs the diagram if not yet constructed, (d) calls `loadDiagram(reactomeId)`, and (e) flags the genes inside `onDiagramLoaded`. Returns a Promise; on rejection, render `ReactomeDiagramEmbed.buildErrorState(reactomeId)` into the parent.
- **`window.ReactomeDiagramEmbed.hide()`** — call from `resetReactomeTab()`; preserves the diagram instance for next selection.
- **`window.ReactomeDiagramEmbed.buildErrorState(reactomeId)`** — call inside `.catch()` of the `load()` Promise; returns ready-to-inject HTML using the CSS Plan 02 added.
- **Sticky failure flag:** if a curator hits a CDN failure once in a session, all subsequent `load()` calls fast-reject. Plan 04 should ensure the error card is rendered on every fast-reject (not only the first failure).
- **Genes argument shape:** `genes` is a plain `Array<string>` of HGNC symbols (e.g. `["TP53", "BRCA1"]`). Plan 04 fetches these from `/ke_genes/<ke_id>` (already exposed by Phase 23/24 work).

## User Setup Required

None for this plan. Behavioural verification (selection → diagram load → flag, CDN-failure → error card) is delegated to Plan 04 Task 3 (manual deploy verification on `https://molaop-builder.vhp4safety.nl`).

## Next Phase Readiness

- Plan 04 (`selectReactomePathway` and `resetReactomeTab` wire-up) can now reference `window.ReactomeDiagramEmbed.load(...)` and `.hide()`. The full RVIEW-01 acceptance flow becomes reachable once Plan 04 lands.
- No blockers. The Wave-2 dependency `27-03 → 27-04` is satisfied.

## Self-Check: PASSED

- `static/js/main.js` — FOUND (modified, 173 lines added, all 11 grep landmarks present)
- `tests/test_index_template.py` — FOUND (modified, +25 lines, test_reactome_diagram_embed_call_shape passes)
- Commit `29dc506` (Task 1 feat) — FOUND in `git log --all`
- Commit `130e52b` (Task 2 test) — FOUND in `git log --all`

---
*Phase: 27-reactome-pathway-viewer*
*Plan: 03*
*Completed: 2026-05-06*
