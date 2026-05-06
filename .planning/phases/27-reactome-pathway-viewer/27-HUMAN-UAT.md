---
status: partial
phase: 27-reactome-pathway-viewer
source: [27-VERIFICATION.md]
started: 2026-05-06T19:15:00Z
updated: 2026-05-06T20:50:00Z
---

## Current Test

[awaiting deploy + remaining human verification of test 3]

## Tests

### 1. Inline Reactome diagram renders for a selected pathway
expected: After login, selecting a Reactome suggestion on the mapper tab causes the DiagramJS canvas to render inside #reactome-inline-embed-frame, positioned between the duplicate-warning card and the confidence guide.
result: passed
notes: Curator confirmed render works on local. Frame height bumped 280px → 500px during UAT (commit ee36491) per curator feedback.

### 2. Genes are flagged via flagItems on diagram-loaded
expected: For a KE whose cached genes overlap pathway entities, at least one entity in the diagram appears highlighted; DevTools console shows no errors during the per-gene flagItems loop.
result: deferred
notes: Curator observed "0 flagged" indicator. Root cause traced to a pre-existing bug in `src/suggestions/ke_genes.py` (since 2025-08-08, commit a325411): the SPARQL selects `edam:data_2298 ?hgnc` which returns numeric HGNC accession IDs (e.g. "12428"), but Reactome `flagItems()` requires gene symbols (e.g. "SNAI1"). This is a shared helper used by Reactome, WikiPathways, and GO suggestion services — gene-overlap scoring across all three has been silently zero. Routed to a separate phase rather than treated as a Phase 27 gap, since the defect predates Phase 27 and Phase 27's call shape is correct.

### 3. CDN failure leaves submission flow functional with no uncaught errors
expected: With DevTools network blocking reactome.org/DiagramJs/*, selecting a suggestion shows the "Pathway viewer unavailable" card with the PathwayBrowser fallback link; the confidence guide and submit button remain interactive; DevTools console shows no uncaught JS exception; a second selection short-circuits via the sticky _failed flag.
result: pending
notes: Requires deploy to molaop-builder.vhp4safety.nl + DevTools network block test in real browser.

## Summary

total: 3
passed: 1
issues: 0
pending: 1
skipped: 0
deferred: 1

## Gaps

- **gap-01** — Gene flagging shows 0 because `/ke_genes/<ke_id>` returns numeric HGNC accession IDs instead of HGNC symbols. Defect predates Phase 27 (in `src/suggestions/ke_genes.py` since commit a325411, 2025-08-08). Routed to a separate phase as a fix to the shared SPARQL helper, not as a Phase 27 gap.
