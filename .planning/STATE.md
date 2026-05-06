---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Reactome Integration
status: executing
stopped_at: Phase 27 context gathered
last_updated: "2026-05-06T17:37:20.477Z"
last_activity: 2026-05-06 -- Phase 27 execution started
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 23
  completed_plans: 19
  percent: 83
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-11)

**Core value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.
**Current focus:** Phase 27 — reactome-pathway-viewer

## Current Position

Phase: 27 (reactome-pathway-viewer) — EXECUTING
Plan: 1 of 4
Status: Executing Phase 27
Last activity: 2026-05-06 -- Phase 27 execution started

```
[Phase 23] [ ] [Phase 24] [ ] [Phase 25] [ ] [Phase 26] [ ] [Phase 27]
  0%                                                              100%
```

## Performance Metrics

**Velocity (all milestones):**

- Total plans completed: 75 (v1.0: 28, v1.1: 18, v1.2: 9, v1.3: 12)
- Total phases completed: 22
- v1.4 phases planned: 5 | completed: 0

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table.

**v1.4 specific:**

- Gene annotation source: Reactome GMT file (HGNC symbols), not UniProt annotation file — avoids silent zero-overlap failure
- Embedding field alias pattern: `reactome_id` → `pathwayID` before embedding service call, alias back after — avoids touching shared service
- DB schema must be finalized before any model code — prevents SELECT column list gaps (lesson from v1.3 go_namespace bug)
- `REACTOME_PROPOSAL_CARRY_FIELDS` constant required — same pattern as GO; prevents silent NULL propagation through approval chain
- DiagramJS CDN embed (not PathwayBrowser iframe) for pathway viewer — CDN widget is the supported third-party integration path
- Hybrid suggestion weights: gene=0.40, embedding=0.60 as starting point; config-driven via `scoring_config.yaml` `reactome_suggestion:` section
- [Phase 23-reactome-data-infrastructure]: GMT gene start col auto-detected at runtime (col 2 not 3) — current Reactome GMT has no 'Reactome Pathway' description column
- [Phase 23-reactome-data-infrastructure]: ContentService IP fallback added: reactome.org/ContentService HTTPS ConnectTimeouts; raw socket via resolved IP works — _get_content_service() handles both paths
- [Phase 23-reactome-data-infrastructure]: ContentService /data/query/ids hard-limits POST responses to 20 items — BATCH_SIZE changed from 100 to 20
- [Phase 23-reactome-data-infrastructure]: IP fallback extended to POST requests via _post_content_service() helper
- [Phase 23]: Integer dbId entries in Reactome containedEvents resolved via R-HSA-{dbId} fallback — top-level disease categories not present as dict entries in same response
- [Phase 24]: Reactome scoring: embedding=0.60, gene=0.40, name_weight=0.70 — Reactome descriptions short, name carries more semantic signal
- [Phase 24]: REACTOME_PROPOSAL_CARRY_FIELDS = (pathway_name, species, suggestion_score, confidence_level) — same pattern as GO carry-fields constant
- [Phase 24]: Reactome proposals table uses provider_username (not github_username) — aligned with multi-provider OAuth identity pattern
- [Phase 24-database-models-and-suggestion-service]: Reactome service uses copy-and-trim from GoSuggestionService rather than inheritance — single-namespace simplification avoids carrying unused _NamespaceData bookkeeping
- [Phase 24-database-models-and-suggestion-service]: Reactome scoring uses 'reactome_pathway_gene_count' field name (mirrors GO's 'go_gene_count') for self-documenting per-database identification
- [Phase 24-database-models-and-suggestion-service]: get_reactome_suggestions enforces config-driven max_results ceiling via min(limit, max_results) so route layer can't bypass scoring config
- [Phase 25]: Plan 25-01: Reactome data layer landed (4 model methods + 2 schemas + 1 search method); updated_by dropped from update_reactome_mapping (no such column on ke_reactome_mappings); schemas placed in src/core/schemas.py not src/utils/validation.py
- [Phase 25]: Plan 25-04: Reactome mapper-page markup added (3rd tab button + #reactome-tab-content with WP-style 3-button confidence — NOT GO 3-dimension wizard); 14 reactome- prefixed IDs ready for Plan 25-05 JS wiring
- [Phase 25]: Plan 25-02: Reactome HTTP endpoints landed; tests use a FakeReactomeSuggestionService to avoid BioBERT load; Tasks 1+2 collapsed to one commit (adjacent additions in same file region); set_admin_models intentionally deferred to Plan 25-03 to keep wave-2 plans non-overlapping
- [Phase 25]: Reactome admin approval is straight-pass-through confidence (D-02): no dimension scoring, no _compute_confidence_from_dimensions call
- [Phase 25]: Admin Reactome template drops GO 3-dimension assessment UI entirely (UI-SPEC Deviation #4); 148 lines smaller than GO clone source
- [Phase 25]: Plan 25-05 Reactome tab JS wiring complete (handleTabSwitch 3-way + 10 new methods + 4 delegated handlers + 2 state slots in static/js/main.js); 62 Reactome-suite tests green; submit-payload contract canonicalised in 25-05 SUMMARY for Plan 25-06 to consume
- [Phase 25]: Plan 25-05 visual verification scope-limited to steps 1–4 of 10 (user response "approved-1-4"); steps 5–10 require GitHub OAuth (not configured locally) — deferred to Plan 25-06 e2e tests (Flask test client bypasses OAuth) + production smoke after deploy to molaop-builder.vhp4safety.nl. Documented deferral, not a checkpoint failure.
- [Phase 25]: Plan 25-05 deviation pattern: Tasks 1+2+3 collapsed to one source-code commit (595133e) — interleaved methods in same JS module, splitting required no architectural benefit (mirrors Plan 25-02's 1+2 collapse rationale)
- [Phase 25-proposal-workflow-and-admin-ui]: Plan 25-06 e2e tests landed; 4 RCUR-anchored tests + 8 gap-fill tests; all 4 e2e tests passed first run confirming Plans 25-01..25-05 wiring is correct end-to-end
- [Phase 25-proposal-workflow-and-admin-ui]: Plan 25-06 closed Plan 25-05's deferred steps 5-10 via Flask test client (bypasses OAuth); production smoke remains the only outstanding verification on molaop-builder.vhp4safety.nl

### Pending Todos

- Run precompute scripts after Phase 23 to generate data files (blocked until scripts exist)
- Calibrate Reactome suggestion weights after Phase 24 by testing known KE→pathway pairs

### Blockers/Concerns

- IC weight calibration (default 0.15) needs domain expert review session (carried from v1.2)
- ORCID/LS Login/SURFconext need human E2E testing with real OAuth credentials (carried from v1.2)
- Dual KE embedding NPZ files not yet generated (precompute script must be run)
- MF precomputed data files not yet generated (run scripts with --namespace mf)
- DiagramJS production stability MEDIUM confidence — evaluate with proof-of-concept in Phase 27 before full commit

### Roadmap Evolution

- Phase 28 added (2026-05-06): KE Gene SPARQL Returns Symbols. Surfaces during Phase 27 HUMAN-UAT — flagItems showed "0" because `/ke_genes/` returns numeric HGNC accession IDs but Reactome's flagItems requires symbols. Defect predates Phase 27 (in `src/suggestions/ke_genes.py` since commit a325411, 2025-08-08); affects gene-overlap scoring across Reactome, WP, and GO suggestion services.

## Session Continuity

**Last session:** 2026-05-06T12:46:25.854Z
**Stopped at:** Phase 27 context gathered
**Resume file:** .planning/phases/27-reactome-pathway-viewer/27-CONTEXT.md
**Next action:** `/gsd-plan-phase 26` — plan the 4 deliverables: /api/v1/reactome-mappings (with AOP filter), per-mapping + KE-centric Reactome GMT, RDF/Turtle export, and the AJAX-driven Reactome tab on explore.html (consumes /api/v1/reactome-mappings directly). Key new model method needed: ReactomeMappingModel.get_reactome_mappings_paginated.
