---
phase: 27-reactome-pathway-viewer
verified: 2026-05-06T19:00:00Z
status: human_needed
score: 3/3 must-haves verified (static); 3 success criteria require deploy verification
human_verification:
  - test: "Inline Reactome diagram renders for a selected pathway"
    expected: "After login, selecting a Reactome suggestion on the mapper tab causes the DiagramJS canvas to render inside #reactome-inline-embed-frame (280px tall), positioned between the duplicate-warning card and the confidence guide."
    why_human: "DiagramJS is loaded from reactome.org CDN at runtime via window.onReactomeDiagramReady; pytest cannot exercise the browser/GWT bundle. Visual rendering is the only definitive proof of RVIEW-01 #1."
  - test: "Genes are flagged via flagItems on diagram-loaded"
    expected: "For a KE whose cached genes overlap pathway entities, at least one entity in the diagram appears highlighted; DevTools console shows no errors during the per-gene flagItems loop."
    why_human: "flagItems is an opaque GWT call against the rendered canvas; static checks confirm the call shape exists but only a runtime curator session can confirm the visual highlight (RVIEW-01 #2)."
  - test: "CDN failure leaves submission flow functional with no uncaught errors"
    expected: "With DevTools network blocking reactome.org/DiagramJs/*, selecting a suggestion shows the 'Pathway viewer unavailable' card with the PathwayBrowser fallback link; the confidence guide and submit button remain interactive; DevTools console shows no uncaught JS exception; a second selection short-circuits via the sticky _failed flag."
    why_human: "RVIEW-01 #3 requires asserting the absence of an uncaught exception under network-blocked conditions; this can only be observed in a real browser session."
review_warnings:
  - id: WR-01
    severity: warning
    file: "static/js/main.js:4730-4734"
    issue: "Catch handler uses .html() on #reactome-inline-embed which destroys the inner #reactome-inline-embed-frame mount point — breaks recovery scenarios where the cached diagram instance is later asked to render against a removed DOM node."
    impact: "Latent: visible only on transient-failure → recovery flow on the same session. Does NOT block the three RVIEW-01 success criteria as written."
  - id: WR-02
    severity: warning
    file: "static/js/main.js:194-204"
    issue: "Each load() call registers a new onDiagramLoaded closure on the reused diagram instance; DiagramJS exposes no off()/unsubscribe, so handlers accumulate across pathway swaps and old gene closures keep firing."
    impact: "Latent: gene-flag visible state may show stale flags on rapid re-selection; memory leak across long sessions."
  - id: WR-03
    severity: warning
    file: "static/js/main.js:194-204"
    issue: "Async failures inside diagram.loadDiagram() (e.g. 404 on diagram-JSON fetch) do NOT reject the load Promise nor fire onDiagramLoaded — user sees an empty 280px box rather than the error card."
    impact: "Edge case for RVIEW-01 #3: the failure-card surfaces only for the script-load and create() paths, not for ContentService failures. Documented in jsdoc but contradicts the 'any failure renders error card' wording."
  - id: WR-04
    severity: warning
    file: "static/js/main.js:108-150,161-172"
    issue: "_failed flag is checked AFTER _scriptPromise; once script loads successfully, subsequent failures inside init() set _failed=true but cannot short-circuit because _scriptPromise is already resolved."
    impact: "Sticky-failure semantics are incomplete for the post-script-load lifecycle. Does not block goal achievement."
---

# Phase 27: Reactome Pathway Viewer Verification Report

**Phase Goal:** Curators can view the Reactome pathway diagram directly within the mapping workflow tab without leaving the application.

**Verified:** 2026-05-06T19:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Success Criteria from ROADMAP)

| #  | Truth                                                                                                                                                | Status                | Evidence |
| -- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- | -------- |
| 1  | Selecting a Reactome pathway suggestion on the mapper tab loads the Reactome DiagramJS diagram for that pathway inline within the page               | ? UNCERTAIN (deploy)  | Static call-shape verified: `selectReactomePathway()` (main.js:4706) calls `ReactomeDiagramEmbed.load(reactomeId, genes)` (main.js:4730); both suggestion-card click handler (main.js:472-478) and search-result handler (main.js:507-515) converge on `selectReactomePathway` (D-03). Mount point `#reactome-inline-embed-frame` exists (templates/index.html:361). DiagramJS construction `Reactome.Diagram.create({placeHolder: this._FRAME_ID, …})` present (main.js:163). Runtime CDN load + GWT render cannot be exercised by pytest. |
| 2  | Genes from the KE's associated mappings are highlighted in the diagram via `flagItems()` when the diagram finishes loading                           | ? UNCERTAIN (deploy)  | Static call-shape verified: `load()` registers `onDiagramLoaded` callback that calls `flagGenes(genes)` (main.js:199-201) which iterates `genes.forEach(g => flagItems(g))` after `resetFlaggedItems()` (main.js:181-188). Genes sourced race-tolerantly from `_cachedKeGenes[keId]` (main.js:4729; cache populated by `prefetchKeGenes` writing to `_cachedKeGenes` at main.js:271, 3253-3260). Visual highlight requires runtime browser session. |
| 3  | If the DiagramJS CDN is unavailable, the tab remains functional for submission without throwing a JavaScript error                                   | ? UNCERTAIN (deploy)  | Static call-shape verified: three-layer failure detection — `script.onerror` (main.js:137), 10s `setTimeout` fallback (main.js:141-147), `try/catch` around `Diagram.create()` (main.js:161-172). `.catch()` at call site (main.js:4730-4734) renders `buildErrorState(reactomeId)` which produces the PathwayBrowser fallback link. `revealReactomeConfidenceStep()` runs BEFORE the embed call (main.js:4719) so a render failure cannot block the submit step. Defensive `if (window.ReactomeDiagramEmbed)` guard wraps both call sites. WR-03 notes that async ContentService failures bypass detection — partial coverage. |

**Static Score:** 3/3 must-haves verified at the call-shape / wiring level.
**Behavioral Score:** 3/3 require manual deploy verification (Plan 04 Task 3, declared manual-only by the plan).

### Required Artifacts

| Artifact                                | Expected                                                                                  | Exists | Substantive | Wired | Status      |
| --------------------------------------- | ----------------------------------------------------------------------------------------- | ------ | ----------- | ----- | ----------- |
| `templates/index.html`                  | `#reactome-inline-embed` (hidden) wrapper + `#reactome-inline-embed-frame` (280px mount)  | ✓      | ✓           | ✓     | ✓ VERIFIED  |
| `static/css/main.css`                   | `.reactome-embed-loading`, `.reactome-embed-error`, `.reactome-embed-error a`             | ✓      | ✓           | ✓     | ✓ VERIFIED  |
| `static/js/main.js` (ReactomeDiagramEmbed) | window utility with loadScriptOnce/init/load/flagGenes/hide/buildErrorState              | ✓      | ✓           | ✓     | ✓ VERIFIED  |
| `static/js/main.js` (selectReactomePathway wire) | `.load(reactomeId, genes).catch(...)` inside selectReactomePathway                  | ✓      | ✓           | ✓     | ✓ VERIFIED  |
| `static/js/main.js` (resetReactomeTab wire) | `ReactomeDiagramEmbed.hide()` inside resetReactomeTab                                    | ✓      | ✓           | ✓     | ✓ VERIFIED  |
| `tests/test_index_template.py`          | 3 tests covering presence, placement, call-shape landmarks                                | ✓      | ✓           | ✓     | ✓ VERIFIED  |

Evidence:
- `grep -c 'id="reactome-inline-embed"' templates/index.html` → 1 (line 360); frame line 361 with `height:280px`.
- `grep -nE '\.reactome-embed-(loading|error)' static/css/main.css` → lines 1608, 1617, 1626.
- `window.ReactomeDiagramEmbed = ReactomeDiagramEmbed` at main.js:238; utility object at main.js:90-236 with all six methods present.
- `pytest tests/test_index_template.py -q` → 3 passed (coverage warning is a pre-existing project-wide artifact, not a failure).

### Key Link Verification

| From                                            | To                                                              | Via                                                                          | Status   | Details |
| ----------------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------- | -------- | ------- |
| `templates/index.html` (#reactome-tab-content)  | `static/js/main.js` (ReactomeDiagramEmbed.init)                 | DOM ID `reactome-inline-embed-frame` (placeHolder)                           | ✓ WIRED  | Frame ID matches `_FRAME_ID` constant in JS utility. |
| `static/js/main.js` (ReactomeDiagramEmbed.loadScriptOnce) | `https://reactome.org/DiagramJs/diagram/diagram.nocache.js` (CDN) | Dynamically-injected `<script>` + `window.onReactomeDiagramReady` global ack | ✓ WIRED (static) | Script tag injection at main.js:134-138; resolution on global at main.js:132. Runtime CDN reachability requires deploy test. |
| `static/js/main.js` (ReactomeDiagramEmbed.load) | Reactome.Diagram instance                                       | `loadDiagram(stId)` + `onDiagramLoaded(cb)` → `resetFlaggedItems()` + per-gene `flagItems(g)` | ✓ WIRED  | Sequence verified at main.js:194-204 and flagGenes at 181-188. WR-02 flags handler accumulation. |
| `static/js/main.js` (buildErrorState)           | `https://reactome.org/PathwayBrowser/#/<id>`                    | Fallback anchor in error card                                                | ✓ WIRED  | Anchor at main.js:232 with `target="_blank" rel="noopener noreferrer"` and HTML-escaped ID. |
| `static/js/main.js` (selectReactomePathway)     | `static/js/main.js` (window.ReactomeDiagramEmbed.load)          | `_cachedKeGenes[keId]` → `.load(...).catch(buildErrorState)`                 | ✓ WIRED  | main.js:4727-4735. Cache populated by prefetchKeGenes at 3253-3260. |
| `static/js/main.js` (resetReactomeTab)          | `static/js/main.js` (window.ReactomeDiagramEmbed.hide)          | Tab reset path → `hide()` container                                          | ✓ WIRED  | main.js:4866-4868. |

### Requirements Coverage

| Requirement | Source Plan(s)                  | Description                                                | Status               | Evidence |
| ----------- | ------------------------------- | ---------------------------------------------------------- | -------------------- | -------- |
| RVIEW-01    | 27-01, 27-02, 27-03, 27-04      | Reactome DiagramJS pathway viewer embed in mapping workflow | ? PARTIAL (deploy)   | All four sub-plans declare RVIEW-01 in frontmatter; static call-shape, DOM scaffold, CSS, and wire-up all in place. Behavioral acceptance (3 success criteria) requires deploy verification per Plan 04 Task 3 (manual-only). |

REQUIREMENTS.md line 94 marks RVIEW-01 as "Pending" → Phase 27 — phase aligns. No orphaned requirements: the RVIEW-01 ID is the only requirement for this phase and is claimed by every plan.

### Anti-Patterns Found

No critical anti-patterns introduced by phase 27 changes. The 4 warnings from 27-REVIEW.md (WR-01..WR-04) are quality-of-implementation concerns, not blockers:

| File                  | Lines       | Severity   | Pattern                                                                       | Impact |
| --------------------- | ----------- | ---------- | ----------------------------------------------------------------------------- | ------ |
| `static/js/main.js`   | 4730-4734   | ⚠️ Warning | Catch handler `.html()` destroys mount point (WR-01)                          | Recovery flow degraded; goal still met for first-failure rendering. |
| `static/js/main.js`   | 194-204     | ⚠️ Warning | onDiagramLoaded handlers accumulate on reused instance (WR-02)                | Stale flag display on rapid re-selection; latent memory leak. |
| `static/js/main.js`   | 194-204     | ⚠️ Warning | No try/catch + secondary timeout around loadDiagram() async (WR-03)           | Empty canvas on ContentService 404 — RVIEW-01 #3 not fully covered for that failure mode. |
| `static/js/main.js`   | 108-150, 161-172 | ⚠️ Warning | _failed flag scope mismatch — never short-circuits after script resolves (WR-04) | Sticky-failure semantics incomplete; no immediate user impact. |

No TODO/FIXME/PLACEHOLDER strings in the new code regions. No empty handlers, no console.log-only stubs, no return-null shortcuts.

### Pre-existing Test Failures (Out of Scope)

`tests/test_app.py::TestRoutes::test_login_redirect` and `tests/test_app.py::TestGuestAuth::test_guest_login_page_renders` failed against base commit `6e131a5` and are unrelated to phase 27 (no auth/route changes in this phase). Not regressions.

### Human Verification Required

#### 1. Inline diagram renders for a selected Reactome pathway (RVIEW-01 #1)

**Test:** Deploy to `https://molaop-builder.vhp4safety.nl`. Log in as curator → select a KE → open the Reactome tab → click any Reactome suggestion card.
**Expected:** DiagramJS canvas renders inside `#reactome-inline-embed-frame` (visible 280px-tall canvas), positioned between the duplicate-warning card and the confidence guide. DevTools shows the CDN bundle loaded once.
**Why human:** DiagramJS is a third-party GWT bundle loaded at runtime; pytest cannot exercise it.

#### 2. Genes from the KE are highlighted via flagItems (RVIEW-01 #2)

**Test:** With the diagram from #1 loaded for a KE whose cached genes overlap pathway entities, observe the canvas.
**Expected:** At least one entity in the diagram appears flagged/highlighted; no errors in DevTools console during the per-gene loop. (CONTEXT.md: zero highlights is acceptable if upstream HGNC↔internal-entity mismatch occurs — the call being made is the success criterion.)
**Why human:** Visual property of rendered canvas; flagItems is opaque to static analysis.

#### 3. CDN failure does not break submission (RVIEW-01 #3)

**Test:** Open DevTools → Network → block requests matching `reactome.org/DiagramJs/*`. Reload the page. Select a Reactome suggestion.
**Expected:**
- The "Pathway viewer unavailable" error card with the "Open in Reactome PathwayBrowser" link appears in `#reactome-inline-embed`.
- The confidence guide and submit button remain interactive.
- DevTools console shows no uncaught JS exception.
- A second selection short-circuits via the sticky `_failed` flag (error card renders without re-attempt).
**Why human:** Asserting the absence of an uncaught exception under network-blocked conditions can only be observed in a real browser session.

### Gaps Summary

No structural gaps — every must-have is in place at the static / wiring level. Phase 27 is in the same posture as Plan 04 declared: automated checks all pass; the three RVIEW-01 acceptance criteria are explicitly deferred to the manual deploy verification step per Plan 04 Task 3 (`<verify><automated>echo "Manual-only..."`).

The 4 code-review warnings (WR-01..WR-04) are quality concerns — particularly WR-01 (catch handler destroys mount point) and WR-02 (handler accumulation) — that should be addressed before this phase is considered "done" for long-running curator sessions, but they do not block goal achievement on first-time use, which is what the three success criteria measure. The user should decide whether to fix WR-01..WR-04 before deploy or address them as a follow-up.

---

_Verified: 2026-05-06_
_Verifier: Claude (gsd-verifier)_
