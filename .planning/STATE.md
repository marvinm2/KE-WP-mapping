---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Scoring & Polish
status: executing
stopped_at: Completed 29-pure-semantic-ranking-shift/29-02-PLAN.md
last_updated: "2026-05-10T11:00:58.035Z"
last_activity: "2026-05-10 — Completed plan 29-03: GO pure-semantic ranking (SEMRANK-02)"
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 6
  completed_plans: 4
  percent: 67
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-10 for v1.5 scoping)

**Core value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.
**Current focus:** v1.5 Scoring & Polish — roadmap complete, ready to plan Phase 29.

## Current Position

Phase: 29 — Pure-Semantic Ranking Shift (in progress)
Plan: 03 (completed)
Status: Ready to execute plan 29-04
Last activity: 2026-05-10 — Completed plan 29-03: GO pure-semantic ranking (SEMRANK-02)

## Performance Metrics

**Velocity (all milestones):**

- Total plans completed: 106 (v1.0: 28, v1.1: 18, v1.2: 9, v1.3: 12, v1.4: 27 + carryforward)
- Total phases completed: 28
- Latest milestone v1.4: 6 phases / 27 plans / 32 tasks / 35 days / +11K LOC

**v1.5 scope:** 5 phases (29–33), 24 requirements, plan counts TBD per phase.

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table (~50 entries spanning v1.0–v1.4). v1.4-specific patterns also in `.planning/RETROSPECTIVE.md` v1.4 section.

Key v1.5-relevant decisions to revisit:

- Hybrid Reactome scoring 60/40 (embedding/gene) — Phase 29 will switch to pure-semantic across WP/GO/Reactome
- IC boost as post-combine GO-specific step — preserved under pure-semantic regime (SEMRANK-02)
- Persistent IDs (`{ncbi, hgnc, symbol}`) in shared SPARQL helper — gene-overlap chip still uses this; only ranking input changes

v1.5 phase ordering decisions:

- Phase 30 (Reactome card parity + threshold tuning) sequenced **after** Phase 29 because thresholds cannot be tuned for a ranking regime that has not landed yet, and "matches WP" only makes sense once WP layout is at the v1.5 baseline.
- Phases 31 (viewer polish), 32 (sibling debt), 33 (baseline cleanup) are independent of the scoring shift and may run in parallel with Phases 29/30 if desired.
- [Phase 29-pure-semantic-ranking-shift]: WP ontology signal lifted from hybrid weight to post-combine boost block (ontology_post_combine_boost.boost_weight=0.15) — mirrors GO IC boost pattern
- [Phase 29-pure-semantic-ranking-shift]: ConfigLoader dataclass defaults left at v1.4 values (document history); runtime values come from YAML; parser tolerant of missing ontology_post_combine_boost key
- [Phase 29-pure-semantic-ranking-shift/29-03]: multi_evidence_bonus fallback default in _combine_go_scores_for changed from 0.05 to 0.0 — safer than relying solely on YAML when config object absent
- [Phase 29-pure-semantic-ranking-shift/29-03]: test fixtures must use load_config() not get_default_config() — dataclass defaults preserve v1.4 values intentionally; load_config() reads YAML v1.5 values
- [Phase 29-pure-semantic-ranking-shift]: Use load_config() not get_default_config() in tests requiring v1.5 YAML weights — get_default_config() returns dataclass defaults (v1.4)
- [Phase 29-pure-semantic-ranking-shift]: method_filter added to /suggest_reactome endpoint for parity with WP/GO; echoed in request_info
- [Phase 29-pure-semantic-ranking-shift]: Ontology signal removed from combine_scored_items weighted sum (ontology_weight=0.0); applied as post-combine boost — decouples WP ranking from ontology match
- [Phase 29-pure-semantic-ranking-shift]: multi_evidence_bonus now config-driven (0.0 in v1.5) not hardcoded 0.05 in PathwaySuggestionService
- [Phase 29-pure-semantic-ranking-shift]: primary_evidence defaults to semantic_similarity in v1.5 (was gene_overlap in v1.4); ontology_tags only when boost fired

### Pending Todos

(carryforward into v1.5 — captured in PROJECT.md Active section, now mapped to phases)

- Phase 27 polish — WR-01..WR-04 + `prefetchKeGenes` race in `ReactomeDiagramEmbed` → **Phase 31**
- GO/WP sibling cleanup — port C-1 XSS fix, H-2 partial-unique pending index, empty-mappings 503 guard → **Phase 32**
- Resolve dead `/confidence_assessment` route → **Phase 33**
- Decide `/dataset/*` future (provision Zenodo/DataCite creds or downgrade to 503) → **Phase 33**
- Pre-existing `test_login_redirect` / `test_guest_login_page_renders` baseline failures → **Phase 33**
- Coverage threshold (42.18% vs 45%) → **Phase 33**

### Blockers/Concerns

- IC weight calibration (default 0.15) needs domain expert review session (carryover from v1.2 — out of v1.5 scope)
- ORCID/LS Login/SURFconext need human E2E testing with real OAuth credentials (carryover from v1.2 — out of v1.5 scope)
- Reactome `flagItems` visual gene highlight not observed — accepted as structural-only per Plan 27-CONTEXT; explicitly deferred as RVIEWHL-01 (v2)
- Pure-semantic ranking will visibly reorder suggestions across WP/GO/Reactome — curators using the tool actively should be informed (changelog + UI hint as part of Phase 29 plans)

### Roadmap Evolution

- v1.4 closed 2026-05-08. Phase 28 added late (2026-05-06) when Phase 27 HUMAN-UAT exposed an HGNC-accession-vs-symbol bug from 2025-08-08 in shared SPARQL helper.
- v1.5 scoped 2026-05-10. Theme: scoring refinement (pure-semantic default) + Reactome ↔ WP parity + v1.4 carry-forward debt sweep.
- v1.5 ROADMAP created 2026-05-10 — 5 phases (29–33), 24/24 requirements mapped, no orphans.

## Session Continuity

**Last session:** 2026-05-10T11:00:47.750Z
**Stopped at:** Completed 29-pure-semantic-ranking-shift/29-02-PLAN.md
**Resume file:** None
**Next action:** Execute plan 29-04 (Reactome pure-semantic ranking, SEMRANK-03)
