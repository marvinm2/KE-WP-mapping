---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Scoring & Polish
status: executing
stopped_at: Completed 32-02-PLAN.md (DEBT-01 satisfied)
last_updated: "2026-05-11T10:51:41.626Z"
last_activity: 2026-05-11
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 18
  completed_plans: 14
  percent: 78
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-10 for v1.5 scoping)

**Core value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.
**Current focus:** v1.5 Scoring & Polish — roadmap complete, ready to plan Phase 29.

## Current Position

Phase: 32
Plan: 4 of 7
Status: Ready to execute
Last activity: 2026-05-11

## Performance Metrics

**Velocity (all milestones):**

- Total plans completed: 117 (v1.0: 28, v1.1: 18, v1.2: 9, v1.3: 12, v1.4: 27 + carryforward)
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
- [Phase 29-pure-semantic-ranking-shift]: Used --color-primary-pink CSS variable (existing in :root) for banner magenta accent rather than non-existent --color-magenta; added .info-banner--v15 modifier class to avoid clobbering existing generic .info-banner blue-border style
- [Phase 29-pure-semantic-ranking-shift]: Reactome under-development notice uses blue (#307BBF) left-border accent (distinct from v1.5 magenta banner); initReactomeDevBanner() mirrors initV15Banner() pattern with localStorage key kewp_reactome_dev_notice_dismissed
- [Phase 30-reactome-suggestion-card-parity-and-threshold-tuning]: embedding_min_threshold=0.84 for Reactome suggestions: score transformation (power_exponent=4.0) compresses cosine similarity into 0.45-0.85 range; original 0.30-0.55 expected range was pre-calibration assumption; at 0.84 narrow KEs give 1-2 suggestions and broad KE 129 gives exactly 10 (cap is binding)
- [Phase 30]: embedding_min_threshold=0.83 for Reactome suggestions: initial calibration selected 0.84 but left KE 1395 with 0 suggestions; one step down to 0.83 restored coverage (2 suggestions) while keeping narrow KEs at 2-5 and capping broad KEs at 10
- [Phase 30/30-02]: s.scores = { final_score: ... } adapter injects WP-compatible field onto Reactome suggestion before passing to createFinalScoreBar — keeps shared helper byte-identical; mutating s in place is safe as each suggestion is rendered once and discarded
- [Phase 30/30-02]: show-more-reactome-suggestions class name used instead of show-more-suggestions — avoids coupling to WP handler; Reactome toggle uses addClass/removeClass (suggestion-item-hidden) rather than .hide()/.show() to match class-based initial render state
- [Phase 30/30-02]: getBorderClassForMatch([]) and getMatchTypeBadges([]) called with empty array for Reactome (no match_types under pure-semantic regime) — ensures constant WP "no badges" visual treatment
- [Phase 31-reactome-viewer-polish]: Split _failed into _scriptFailed (sticky session) + _lastLoadFailed (per-attempt) per D-09; resetForNewKe() wired to KE-change handler
- [Phase 31-reactome-viewer-polish/31-02]: bind-once onDiagramLoaded in init() with load-token guard closure — older fires from same-KE pathway swaps no-op via myToken !== _loadToken check (D-05, WR-02)
- [Phase 31-reactome-viewer-polish/31-02]: Promise wrapper around loadDiagram replaces _resolveCurrentLoad atomically per load(); settled flag inside each Promise closure prevents double-settle
- [Phase 31-reactome-viewer-polish/31-02]: selectReactomePathway pre-clears sibling overlay and shows frame before load() attempt — visual state is clean at attempt start regardless of prior outcome (D-01)
- [Phase 31-reactome-viewer-polish/31-02]: hide() restores frame visibility (#reactome-inline-embed-frame.show()) so next load() starts with frame visible; _scriptFailed not touched (D-09)
- [Phase 31-reactome-viewer-polish/31-03]: _cachedKeGenes[keId] is Promise<string[]> not string[] — in-flight distinguishable from empty-result; eliminates VIEWFIX-05 race condition
- [Phase 31-reactome-viewer-polish/31-03]: prefetchKeGenes returns memoised Promise so callers .then directly; existing fire-and-forget call site at line 1467 unchanged; D-16 .fail() resolves to [] (never rejects)
- [Phase 31-reactome-viewer-polish/31-03]: selectReactomePathway fires load() immediately with [] for instant mount (D-15); gene Promise .then writes _pendingFlags and calls flagGenes() only when load-token still matches
- [Phase 31-reactome-viewer-polish/31-03]: openMappingModal defers PathwayEmbed.mountIframe into gene Promise .then — single mount with correct genes; modal chrome opens immediately with "Loading genes…" state (D-14)
- [Phase 32]: Inline escapeHtml helper in admin_proposals.html (not extracted to utils.js); status badge uses statusEsc + statusTitleEsc for both class fragment and title-cased display text
- [Phase 32-go-wp-sibling-debt-sweep]: [Plan 32-02] escapeHtml inlined per-template (not shared utils.js); pre-escape derived locals into *Esc-suffix vars (nsShortEsc, nsBadgeClassEsc, statusEsc, cConnEsc/cSpecEsc/cEvEsc); renderAdminDimensionToggles also escape-wrapped per 'no exceptions' policy
- [Phase 32]: [Phase 32/32-05]: WP RDF 503 guard ported from Reactome verbatim — if mappings: serialise else: write empty placeholder. Without short-circuit, generate_ke_wp_turtle([]) emits non-empty @prefix prelude (rdflib serialise behaviour), bypassing st_size==0 check and returning 200 + prefix-only Turtle blob instead of contracted 503.
- [Phase 32]: [Phase 32/32-05]: RDF route tests must monkeypatch module-global mapping_model (per tests/test_reactome_exports.py pattern) — client fixture temp-DB rebind doesn't reach the blueprint module's mapping_model global which is bound once at create_app() time.

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

**Last session:** 2026-05-11T10:51:31.715Z
**Stopped at:** Completed 32-02-PLAN.md (DEBT-01 satisfied)
**Resume file:** None
**Next action:** Execute Phase 32 (GO/WP sibling debt sweep — DEBT-01..06)
