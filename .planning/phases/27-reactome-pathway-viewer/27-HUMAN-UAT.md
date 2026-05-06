---
status: partial
phase: 27-reactome-pathway-viewer
source: [27-VERIFICATION.md]
started: 2026-05-06T19:15:00Z
updated: 2026-05-06T19:15:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Inline Reactome diagram renders for a selected pathway
expected: After login, selecting a Reactome suggestion on the mapper tab causes the DiagramJS canvas to render inside #reactome-inline-embed-frame (280px tall), positioned between the duplicate-warning card and the confidence guide.
result: [pending]

### 2. Genes are flagged via flagItems on diagram-loaded
expected: For a KE whose cached genes overlap pathway entities, at least one entity in the diagram appears highlighted; DevTools console shows no errors during the per-gene flagItems loop.
result: [pending]

### 3. CDN failure leaves submission flow functional with no uncaught errors
expected: With DevTools network blocking reactome.org/DiagramJs/*, selecting a suggestion shows the "Pathway viewer unavailable" card with the PathwayBrowser fallback link; the confidence guide and submit button remain interactive; DevTools console shows no uncaught JS exception; a second selection short-circuits via the sticky _failed flag.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
