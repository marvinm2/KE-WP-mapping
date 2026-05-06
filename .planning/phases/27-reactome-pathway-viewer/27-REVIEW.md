---
phase: 27-reactome-pathway-viewer
reviewed: 2026-05-06T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - static/css/main.css
  - static/js/main.js
  - templates/index.html
  - tests/test_index_template.py
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: issues_found
---

# Phase 27: Code Review Report

**Reviewed:** 2026-05-06
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found
**Diff base:** 6e131a54..HEAD

## Summary

Phase 27 adds the inline Reactome `DiagramJS` embed: a small DOM scaffold in
`templates/index.html`, two new CSS rule blocks in `static/css/main.css`, a
`ReactomeDiagramEmbed` utility in `static/js/main.js` (~+173 lines), wire-up in
`selectReactomePathway()` / `resetReactomeTab()`, and pytest smoke tests.

The implementation follows the documented `RESEARCH` design (un-versioned CDN,
three-layer failure detection, per-gene `flagItems`, `onDiagramLoaded` for race
safety) and mirrors the WikiPathways analog reasonably well. No critical
security or correctness defects were found in the new code.

However, two concrete state-management defects degrade the failure-recovery and
re-selection paths:

- The error-state HTML injection destroys the inner `#reactome-inline-embed-frame`
  element that the cached diagram is mounted against, breaking subsequent
  attempts after a transient failure.
- Each call to `load()` registers a new `onDiagramLoaded` callback against the
  reused diagram instance, accumulating handlers across re-selections.

Additional warnings cover async-failure detection gaps in `loadDiagram()` and a
sticky-failure flag whose effect is masked by the memoized script promise. Five
informational items track style/maintainability concerns.

## Warnings

### WR-01: Error-state HTML overwrites `#reactome-inline-embed-frame`, breaking later mounts

**File:** `static/js/main.js:4730-4734`
**Issue:** When `load()` rejects, `selectReactomePathway` does:
```js
$('#reactome-inline-embed')
    .html(window.ReactomeDiagramEmbed.buildErrorState(reactomeId))
    .show();
```
`.html(...)` replaces the children of `#reactome-inline-embed`, including the
inner `<div id="reactome-inline-embed-frame">` that the DiagramJS instance was
(or will be) mounted against. Recovery scenarios are then broken:

1. Failure mode A — script-load fails, then user selects a different pathway:
   `_scriptPromise` is nulled in `fail()` so the script is re-injected; if it
   eventually resolves, `init()` runs and `Reactome.Diagram.create({placeHolder:
   'reactome-inline-embed-frame', ...})` is called against an element that no
   longer exists in the DOM (it was replaced by the error card's `<div
   class="reactome-embed-error">…</div>`). Behaviour is undefined.
2. Failure mode B — script loaded fine on a previous selection, current
   selection failed inside `loadDiagram()`/`init()`; `_diagram` may already be
   cached against the old frame node. Even if `init()` returns the cached
   diagram, the DOM node it bound to is gone, so future `loadDiagram()`/
   `flagItems()` calls render against a detached canvas.

The WP analog (`loadInlineEmbed` at `main.js:3264-3273`) also calls `.html()` /
`.empty()` but builds the iframe per-call, so it is naturally idempotent.
DiagramJS reuse-instance design (D-04) does not tolerate the placeholder
disappearing between calls.

**Fix:** Inject the error card into the frame, not the parent, so the parent
container's children remain intact:
```js
window.ReactomeDiagramEmbed.load(reactomeId, genes).catch(() => {
    // Restore the frame element if a previous error wiped it, then mount the
    // error card *inside* it. Keeps #reactome-inline-embed-frame intact for
    // future successful selections.
    const $container = $('#reactome-inline-embed').show();
    if ($container.find('#reactome-inline-embed-frame').length === 0) {
        $container.html(
            '<div id="reactome-inline-embed-frame" ' +
            'style="width:100%; height:280px; position:relative;"></div>'
        );
    }
    $('#reactome-inline-embed-frame')
        .html(window.ReactomeDiagramEmbed.buildErrorState(reactomeId));
});
```
…and additionally null `this._diagram` on `init()` failure (currently `_failed`
is set but `_diagram` is left in whatever state) so a re-mount can occur after
the frame is restored.

### WR-02: `onDiagramLoaded` handlers accumulate on the reused diagram instance

**File:** `static/js/main.js:194-204`
**Issue:** `load()` is invoked every time the curator picks a Reactome pathway,
and on every call it registers a new closure:
```js
diagram.onDiagramLoaded(function(/* loadedStId */) {
    self.flagGenes(genes);
});
```
DiagramJS exposes `onDiagramLoaded` as a subscribe-style API; per RESEARCH §2
there is no documented `off` / `unsubscribe`. Because the diagram instance is
reused (`_diagram` cached at line 160), every previously-registered handler
remains attached. Consequences:

1. On the second selection, both the old `(genes_A)` and new `(genes_B)`
   closures fire when `loadDiagram(B)` completes. Even though each handler
   calls `resetFlaggedItems()` first, the *order* the GWT bundle invokes
   subscribers in is undocumented — the visible flag set is whichever closure
   ran last, not necessarily the latest user selection.
2. Memory: the `genes_A` array is retained by the closure for the lifetime of
   the diagram, accumulating across selections (out of v1 scope, but worth
   noting because it is a real leak vector).
3. After Phase 27's RVIEW-01 #3 path (transient failure → recovery), the leak
   compounds with WR-01.

**Fix:** Either (a) register exactly one persistent handler at `init()` time
that reads `this._pendingGenes` set by each `load()` call, or (b) gate flagging
through a generation counter so stale handlers no-op:
```js
init: function() {
    $('#' + this._CONTAINER_ID).show();
    if (this._diagram) return this._diagram;
    var self = this;
    this._diagram = window.Reactome.Diagram.create({...});
    // Single persistent handler — reads latest genes, ignores stale closures.
    this._diagram.onDiagramLoaded(function() { self.flagGenes(self._pendingGenes); });
    return this._diagram;
},
load: function(reactomeId, genes) {
    var self = this;
    return this.loadScriptOnce().then(function() {
        var diagram = self.init();
        self._pendingGenes = genes || [];
        diagram.loadDiagram(reactomeId);
        return diagram;
    });
}
```
Option (a) also removes the `flagGenes(genes)` argument duplication.

### WR-03: Async failures from `loadDiagram()` bypass the documented three-layer detection

**File:** `static/js/main.js:194-204`, jsdoc at lines 83-87
**Issue:** The class jsdoc claims layer (c) covers `try/catch around
Diagram.create() and loadDiagram()`. In practice:
- `Diagram.create()` IS try/caught inside `init()`.
- `diagram.loadDiagram(reactomeId)` is NOT inside any try/catch, and even if
  it were, DiagramJS performs its diagram-JSON fetch asynchronously after this
  call returns. A 404 from `https://reactome.org/ContentService/data/.../diagram`
  or a malformed payload neither rejects the promise returned by `load()` nor
  triggers `onDiagramLoaded`. The user sees an empty 280px box with no error
  card, no spinner, no fallback link.

This contradicts the RVIEW-01 #3 acceptance criterion ("any failure renders the
error card; submission flow is never blocked").

**Fix:** Either (a) wrap `diagram.loadDiagram(...)` in try/catch AND start a
secondary timeout that races `onDiagramLoaded`, rejecting the load promise if
the diagram-loaded signal never fires, or (b) document explicitly in the jsdoc
that async diagram-JSON fetch failures are NOT caught and that a stalled empty
canvas is the visible failure mode. Suggested code:
```js
load: function(reactomeId, genes) {
    var self = this;
    return this.loadScriptOnce().then(function() {
        var diagram = self.init();
        return new Promise(function(resolve, reject) {
            var settled = false;
            var t = setTimeout(function() {
                if (!settled) { settled = true; reject(new Error('Diagram render timeout')); }
            }, self._LOAD_TIMEOUT_MS);
            try {
                diagram.onDiagramLoaded(function() {
                    if (settled) return;
                    settled = true;
                    clearTimeout(t);
                    self.flagGenes(genes);
                    resolve(diagram);
                });
                diagram.loadDiagram(reactomeId);
            } catch (e) {
                if (!settled) { settled = true; clearTimeout(t); reject(e); }
            }
        });
    });
}
```

### WR-04: `_failed` flag has no effect after `loadScriptOnce()` has resolved once

**File:** `static/js/main.js:108-150, 161-172`
**Issue:** `loadScriptOnce()` checks `_failed` only when `_scriptPromise` is
null:
```js
if (this._scriptPromise) return this._scriptPromise;
if (this._failed) return Promise.reject(...);
```
But after the first successful script load `_scriptPromise` is a resolved
promise, so subsequent failures inside `init()` (which set `_failed = true` at
line 170) leak through: the next call to `loadScriptOnce()` short-circuits at
the first line and returns the resolved promise; `init()` runs again; the same
exception is likely re-thrown. The "sticky-failure" semantics documented at
lines 105-106 are therefore incomplete — they apply only to the script-load
phase, not to the `Diagram.create` phase, despite both setting `_failed`.

**Fix:** Either remove the `_failed = true` assignment in `init()`'s catch (the
flag is misleading there), or check `_failed` first:
```js
loadScriptOnce: function() {
    if (this._failed) return Promise.reject(new Error('Reactome embed previously failed'));
    if (this._scriptPromise) return this._scriptPromise;
    ...
}
```
Pick whichever matches intended retry semantics, and update the jsdoc to match.

## Info

### IN-01: `.reactome-embed-loading` / `.reactome-embed-error` are byte-identical to the `.wp-embed-*` rules

**File:** `static/css/main.css:1608-1628`
**Issue:** The two new selector blocks duplicate `.wp-embed-loading` /
`.wp-embed-error` / `.wp-embed-error a` declarations exactly. Future style
changes risk drift.
**Fix:** Combine selectors:
```css
.wp-embed-loading,
.reactome-embed-loading { display: flex; flex-direction: column; ... }
.wp-embed-error,
.reactome-embed-error { ... }
.wp-embed-error a,
.reactome-embed-error a { color: var(--color-primary-blue); }
```

### IN-02: `buildErrorState` re-implements an HTML escaper instead of reusing `KEWPApp.escapeHtml`

**File:** `static/js/main.js:223-235`
**Issue:** `KEWPApp` already has an `escapeHtml` method used throughout
(`main.js:1282, 1507, 1511, …`). `ReactomeDiagramEmbed` is intentionally
standalone (parity with `PathwayEmbed`), but the inline escaper is a duplicate
implementation. Minor maintenance hazard.
**Fix:** Either accept the duplication (document the rationale: "kept
self-contained for parity with `PathwayEmbed`") or extract a tiny module-level
`htmlEscape` helper used by both `KEWPApp.escapeHtml` and
`ReactomeDiagramEmbed.buildErrorState`.

### IN-03: Magic-number width fallback `|| 950` and hard-coded `height: 280`

**File:** `static/js/main.js:162, 166`
**Issue:** Two magic numbers:
```js
var width = $('#' + this._FRAME_ID).width() || 950;
this._diagram = window.Reactome.Diagram.create({..., height: 280, ...});
```
The `280` matches the inline `height:280px` style in `templates/index.html:361`
and the test landmark; the `950` is undocumented (no comment, no constant).
**Fix:** Hoist to named constants near `_LOAD_TIMEOUT_MS`:
```js
_DEFAULT_WIDTH_PX: 950,
_DEFAULT_HEIGHT_PX: 280,
```
and reference them from both `init()` and (ideally) the template scaffold via a
shared CSS variable.

### IN-04: `selectReactomePathway` no longer client-side validates `reactomeId` before passing to the embed

**File:** `static/js/main.js:4706-4736`
**Issue:** `reactomeId` arrives from suggestion-card / search-result `data-`
attributes and is plumbed straight into `ReactomeDiagramEmbed.load(reactomeId,
genes)` and (on failure) into `buildErrorState(reactomeId)`. Server-side
validation (`^R-HSA-[0-9]+$`) only runs at submit time. While `buildErrorState`
HTML-escapes its input and the URL is appended after a `#` (no path-injection
risk), an out-of-shape ID still reaches `loadDiagram()` and the GWT bundle's
behaviour for malformed input is undocumented.
**Fix:** Add a defensive client-side check before calling `.load()`:
```js
const REACTOME_ID_RE = /^R-HSA-[0-9]+$/;
if (window.ReactomeDiagramEmbed && REACTOME_ID_RE.test(reactomeId)) { ... }
```
…and skip the embed silently otherwise. Low priority — no security impact, just
robustness.

### IN-05: Test landmark check would silently miss whitespace/punctuation drift

**File:** `tests/test_index_template.py:44-58`
**Issue:** The grep-based call-shape test asserts substrings like
`"Reactome.Diagram.create("` and `"flagItems("` exist anywhere in `main.js`.
This passes even if the calls are commented out, behind a feature flag, or in
unrelated code added later. It is a smoke test, not a behavioural test, which
is fine for Wave 0 but should be backed by an actual JS unit test before
relying on it for regression catch.
**Fix:** Either accept the limitation (add a docstring note that this is a
landmark grep, not a behaviour test) or add a JS unit test (jsdom + jest /
QUnit) that exercises `ReactomeDiagramEmbed.load()` against a stubbed
`window.Reactome.Diagram`. The latter would also catch WR-02 and WR-03
naturally.

---

_Reviewed: 2026-05-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
