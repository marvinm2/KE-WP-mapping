# Roadmap: KE-WP / KE-GO Mapping Tool

## Milestones

- ✅ **v1.0 MVP** — Phases 1–7 (shipped 2026-02-23)
- ✅ **v1.1 Visuals** — Phases 8–12 (shipped 2026-03-04)
- ✅ **v1.2 Curation Depth** — Phases 13–16 (shipped 2026-03-06)
- ✅ **v1.3 GO Assessment Quality** — Phases 17–22 (shipped 2026-03-11)
- ✅ **v1.4 Reactome Integration** — Phases 23–28 (shipped 2026-05-08)
- 🔄 **v1.5 Scoring & Polish** — Phases 29–33 (active, scoped 2026-05-10)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–7) — SHIPPED 2026-02-23</summary>

- [x] Phase 1: Deployment Hardening (4/4 plans) — completed 2026-02-19
- [x] Phase 2: Data Model and Audit Trail (4/4 plans) — completed 2026-02-20
- [x] Phase 3: Stable Public REST API (4/4 plans) — completed 2026-02-21
- [x] Phase 4: Curator UX and Explore (5/5 plans) — completed 2026-02-21
- [x] Phase 5: Exports and Dataset Publication (4/4 plans) — completed 2026-02-22
- [x] Phase 6: API Documentation (3/3 plans) — completed 2026-02-22
- [x] Phase 7: KE-GO Proposal Workflow (4/4 plans) — completed 2026-02-23

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Visuals (Phases 8–12) — SHIPPED 2026-03-04</summary>

- [x] Phase 8: Brand Refresh and CSS Cleanup (5/5 plans) — completed 2026-02-24
- [x] Phase 9: WikiPathways Embed Viewer (3/3 plans) — completed 2026-03-03
- [x] Phase 10: AOP Network Graph (4/4 plans) — completed 2026-03-04
- [x] Phase 11: Inline AOP Graph on Mapper Page (3/3 plans) — completed 2026-03-04
- [x] Phase 12: Gene Set Visualization on AOP Graph (3/3 plans) — completed 2026-03-04

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Curation Depth (Phases 13–16) — SHIPPED 2026-03-06</summary>

- [x] Phase 13: Low-Risk Foundations (3/3 plans) — completed 2026-03-04
- [x] Phase 14: Auth Expansion (2/2 plans) — completed 2026-03-06
- [x] Phase 15: GO Hierarchy Integration (2/2 plans) — completed 2026-03-06
- [x] Phase 16: API Metadata Capstone (2/2 plans) — completed 2026-03-06

Full details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 GO Assessment Quality (Phases 17–22) — SHIPPED 2026-03-11</summary>

- [x] Phase 17: KE Description Toggle (2/2 plans) — completed 2026-03-09
- [x] Phase 18: Directionality Detection and Tagging (3/3 plans) — completed 2026-03-10
- [x] Phase 19: Structured Three-Dimension Assessment (3/3 plans) — completed 2026-03-10
- [x] Phase 20: GO Molecular Function Suggestions (2/2 plans) — completed 2026-03-10
- [x] Phase 21: Wire GO Namespace Through Approval Chain (1/1 plan) — completed 2026-03-11
- [x] Phase 22: Fix Bulk Export SELECT for Direction and Namespace (1/1 plan) — completed 2026-03-11

Full details: `.planning/milestones/v1.3-ROADMAP.md`

</details>

<details>
<summary>✅ v1.4 Reactome Integration (Phases 23–28) — SHIPPED 2026-05-08</summary>

- [x] Phase 23: Reactome Data Infrastructure (3/3 plans) — completed 2026-04-03
- [x] Phase 24: Database Models and Suggestion Service (2/2 plans) — completed 2026-04-29
- [x] Phase 25: Proposal Workflow and Admin UI (6/6 plans) — completed 2026-05-05
- [x] Phase 26: Public API and Exports (8/8 plans) — completed 2026-05-06
- [x] Phase 27: Reactome Pathway Viewer (4/4 plans) — completed 2026-05-06
- [x] Phase 28: KE Gene SPARQL Returns Persistent Identifiers (4/4 plans) — completed 2026-05-07

Full details: `.planning/milestones/v1.4-ROADMAP.md`

</details>

### 🔄 v1.5 Scoring & Polish (Phases 29–33) — ACTIVE

- [x] **Phase 29: Pure-Semantic Ranking Shift** — Switch WP/GO/Reactome suggestion ranking to BioBERT similarity only; demote gene-overlap to display-only chip (completed 2026-05-10)
- [x] **Phase 30: Reactome Suggestion Card Parity and Threshold Tuning** — Bring Reactome suggestion-card layout to WP standard; re-tune Reactome thresholds for the new pure-semantic regime (completed 2026-05-10)
- [x] **Phase 31: Reactome Viewer Polish** — Fix Phase 27 carry-forward issues in `ReactomeDiagramEmbed` (WR-01..04 + prefetch race) (completed 2026-05-11)
- [ ] **Phase 32: GO/WP Sibling Debt Sweep** — Port Reactome's C-1 XSS fix, H-2 partial-unique pending index, and empty-mappings 503 guard to GO/WP equivalents
- [ ] **Phase 33: Baseline Cleanup** — Resolve dead routes, baseline test failures, and coverage threshold

## Phase Details

### Phase 29: Pure-Semantic Ranking Shift
**Goal**: Curators see suggestions ranked purely by BioBERT semantic similarity across all three pathway resources, with gene-overlap visible but no longer influencing rank order.
**Depends on**: Nothing (first phase of v1.5; builds on shipped v1.4)
**Requirements**: SEMRANK-01, SEMRANK-02, SEMRANK-03, SEMRANK-04, SUGDISP-01
**Success Criteria** (what must be TRUE):
  1. On the WP suggestions tab, the top-ranked suggestion is the one with the highest BioBERT similarity to the selected KE — gene overlap no longer reorders the list
  2. On the GO suggestions tab (BP and MF), the top-ranked suggestion is the one with the highest BioBERT similarity, with the GO IC specificity boost still applied as a separate post-combine step
  3. On the Reactome suggestions tab, the top-ranked suggestion is the one with the highest BioBERT similarity — gene overlap no longer reorders the list
  4. Each suggestion card on WP / GO / Reactome shows a visible gene-overlap chip with the count and overlap fraction, but the chip carries no rank weight (verified by sorting comparison against pure-similarity ranking)
  5. `scoring_config.yaml` reflects the v1.5 pure-semantic defaults; the previous hybrid weights are recorded with a deprecation comment explaining the rationale
**Plans**: 6 plans
  - [x] 29-01-PLAN.md — Update scoring_config.yaml to v1.5 pure-semantic defaults; adapt ConfigLoader; pin combine_scored_items single-signal contract
  - [x] 29-02-PLAN.md — Refactor PathwaySuggestionService (WP) to embedding-only ranking with ontology post-combine boost
  - [x] 29-03-PLAN.md — Refactor GoSuggestionService (BP + MF) to embedding-only ranking; preserve IC boost + directionality
  - [x] 29-04-PLAN.md — Refactor ReactomeSuggestionService to embedding-only ranking; add method_filter deprecation log on three suggestion endpoints
  - [x] 29-05-PLAN.md — Frontend: gene-overlap chip on WP / GO / Reactome cards; remove method-filter UI and scoring breakdown; drop method_filter from outbound fetches
  - [x] 29-06-PLAN.md — v1.5 dismissible migration banner + CHANGELOG.md v1.5 entry

### Phase 30: Reactome Suggestion Card Parity and Threshold Tuning
**Goal**: A curator working on Reactome suggestions experiences the same scoring-breakdown layout and information density as on WP, with thresholds tuned so the post-pure-semantic suggestion list feels curated rather than noisy.
**Depends on**: Phase 29 (cannot tune thresholds for a ranking that is still hybrid; cannot align card layout to "WP standard" if WP card layout is still mid-shift)
**Requirements**: SUGDISP-02, REASCORE-01, REASCORE-02
**Success Criteria** (what must be TRUE):
  1. The Reactome suggestion card visually matches the WP suggestion card — same panel chrome, same arrangement of signal chips, same score badge, same info density (verified by side-by-side screenshot comparison on a single KE)
  2. On a representative sample of at least five KEs covering different bio levels, a curator confirms that the top-N Reactome suggestions feel comparable in quality to the top-N WP suggestions for the same KE
  3. The `reactome_suggestion:` block in `scoring_config.yaml` has updated min-similarity and top-N-cap values, and the resulting suggestion lists are visibly tighter than the pre-tuning baseline (no long tails of low-similarity noise)
**Plans**: 2 plans
  - [x] 30-01-PLAN.md — Empirical distribution dump on 5 calibration KEs; tune `scoring_config.yaml::reactome_suggestion` thresholds (`embedding_min_threshold`, `min_threshold`, `max_results: 10`, demote `gene_min_threshold`); curator spot-check (REASCORE-01, REASCORE-02)
  - [x] 30-02-PLAN.md — Refactor `displayReactomeSuggestions` to WP card chrome (reuse `createFinalScoreBar`, `renderGeneOverlapChip`, collapse-after-3); side-by-side visual parity check (SUGDISP-02)

### Phase 31: Reactome Viewer Polish
**Goal**: The Reactome inline pathway viewer recovers cleanly from CDN failures, pathway swaps, and gene-prefetch races without leaving the user with a broken mount, accumulating handlers, or empty gene highlights.
**Depends on**: Nothing (independent JS-only work; can run in parallel with Phases 29–30)
**Requirements**: VIEWFIX-01, VIEWFIX-02, VIEWFIX-03, VIEWFIX-04, VIEWFIX-05
**Success Criteria** (what must be TRUE):
  1. After a first DiagramJS load failure, retrying the load (e.g. by selecting a different pathway) produces either a successful render or the error-card fallback — the mount is never destroyed mid-recovery (WR-01)
  2. Swapping between pathways on the same KE does not produce duplicate `onDiagramLoaded` callbacks (verified via instrumented handler count or end-to-end behaviour) (WR-02)
  3. An async failure inside `loadDiagram` surfaces the same error-card path as a synchronous failure — failures are never silent (WR-03)
  4. After a failed load on KE A, switching to KE B starts a clean attempt — the `_failed` flag is scoped to the previous attempt, not sticky (WR-04)
  5. When a curator opens a KE that has genes, `flagItems` is invoked with the resolved gene list — no race condition leaves the diagram with an empty highlight set (VIEWFIX-05)
**Plans**: 3 plans
  - [x] 31-01-PLAN.md — DOM scaffolding (sibling error overlay) + state-shape refactor (`_failed` → `_scriptFailed` + `_lastLoadFailed`) + KE-change reset hook (VIEWFIX-01, VIEWFIX-04 substrate)
  - [x] 31-02-PLAN.md — Promise-wrapped `loadDiagram` + bind-once `onDiagramLoaded` with token-guard + `_flagGenesInvocations` counter + sibling-overlay failure path (VIEWFIX-01, VIEWFIX-02, VIEWFIX-03, VIEWFIX-04)
  - [x] 31-03-PLAN.md — `prefetchKeGenes` as memoised `Promise<string[]>`; race-tolerant gene-flag application in `selectReactomePathway`; modal awaits gene Promise (VIEWFIX-05)

### Phase 32: GO/WP Sibling Debt Sweep
**Goal**: GO and WP admin/proposal/RDF surfaces have the same security and robustness posture as Reactome — XSS-safe modal rendering, race-safe pending-duplicate detection, and graceful empty-graph responses.
**Depends on**: Nothing (independent of scoring/viewer work; can run in parallel)
**Requirements**: DEBT-01, DEBT-02, DEBT-03, DEBT-04, DEBT-05, DEBT-06
**Success Criteria** (what must be TRUE):
  1. An admin opening a GO or KE-WP proposal modal sees user-supplied content rendered safely — script payloads in proposer-controlled fields are escaped, not executed (parity with Reactome admin modal post-C-1 fix)
  2. Two near-simultaneous proposal submissions for the same KE→GO or KE→WP pair result in exactly one pending row plus a clean duplicate response on the second — no race window where both insert successfully
  3. Hitting `/download_ke_go_rdf` or `/download_ke_wp_rdf` when no approved mappings exist returns a 503 with a clear "no data" body, matching the Reactome RDF route's behaviour — no half-formed Turtle and no 200 with empty graph
**Plans**: 7 plans
  - [x] 32-01-PLAN.md — Port C-1 XSS escapeHtml helper + per-interpolation wrapping to `templates/admin_proposals.html` (DEBT-02)
  - [x] 32-02-PLAN.md — Port C-1 XSS escapeHtml helper + per-interpolation wrapping to `templates/admin_go_proposals.html` (DEBT-01)
  - [x] 32-03-PLAN.md — `proposals` table: pre-migration cleanup + partial-unique index + DUPLICATE_PENDING sentinel + /submit route 409 using check_mapping shape (DEBT-04)
  - [ ] 32-04-PLAN.md — `ke_go_proposals` table: pre-migration cleanup + partial-unique index + DUPLICATE_PENDING sentinel + /submit_go_mapping 409 using check_go_mapping shape (DEBT-03)
  - [x] 32-05-PLAN.md — `download_ke_wp_rdf`: `if mappings: ... else: write_text('')` short-circuit + empty-graph regression test (DEBT-06)
  - [ ] 32-06-PLAN.md — `download_ke_go_rdf`: `if mappings: ... else: write_text('')` short-circuit + empty-graph regression test (DEBT-05)
  - [ ] 32-07-PLAN.md — CHANGELOG.md v1.5 entry covering all three concerns (DEBT-01..06)

### Phase 33: Baseline Cleanup
**Goal**: The smoke-test surface is clean — no dead 500 routes, the test suite has no pre-existing failures, and coverage either meets the 45% threshold or has the threshold consciously revised with a documented reason.
**Depends on**: Nothing (orthogonal to feature/debt work)
**Requirements**: CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04, CLEAN-05
**Success Criteria** (what must be TRUE):
  1. Hitting `/confidence_assessment` returns either a real, rendered template page or a clean removal (404 / redirect) — never a 500 from a missing template
  2. Hitting `/dataset/{metadata,versions,citation,datacite}` returns either a working response (when Zenodo/DataCite credentials are provisioned) or a clean 503 / hidden-by-feature-flag — never the current `metadata_manager`-unconfigured 500
  3. `pytest` runs with `test_login_redirect` and `test_guest_login_page_renders` passing (root-cause of Phase 14 OAuth route drift addressed)
  4. The CI coverage gate is green: either coverage is at or above 45%, or the threshold has been revised with a documented rationale committed alongside the config change
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Deployment Hardening | v1.0 | 4/4 | Complete | 2026-02-19 |
| 2. Data Model and Audit Trail | v1.0 | 4/4 | Complete | 2026-02-20 |
| 3. Stable Public REST API | v1.0 | 4/4 | Complete | 2026-02-21 |
| 4. Curator UX and Explore | v1.0 | 5/5 | Complete | 2026-02-21 |
| 5. Exports and Dataset Publication | v1.0 | 4/4 | Complete | 2026-02-22 |
| 6. API Documentation | v1.0 | 3/3 | Complete | 2026-02-22 |
| 7. KE-GO Proposal Workflow | v1.0 | 4/4 | Complete | 2026-02-23 |
| 8. Brand Refresh and CSS Cleanup | v1.1 | 5/5 | Complete | 2026-02-24 |
| 9. WikiPathways Embed Viewer | v1.1 | 3/3 | Complete | 2026-03-03 |
| 10. AOP Network Graph | v1.1 | 4/4 | Complete | 2026-03-04 |
| 11. Inline AOP Graph on Mapper Page | v1.1 | 3/3 | Complete | 2026-03-04 |
| 12. Gene Set Visualization on AOP Graph | v1.1 | 3/3 | Complete | 2026-03-04 |
| 13. Low-Risk Foundations | v1.2 | 3/3 | Complete | 2026-03-04 |
| 14. Auth Expansion | v1.2 | 2/2 | Complete | 2026-03-06 |
| 15. GO Hierarchy Integration | v1.2 | 2/2 | Complete | 2026-03-06 |
| 16. API Metadata Capstone | v1.2 | 2/2 | Complete | 2026-03-06 |
| 17. KE Description Toggle | v1.3 | 2/2 | Complete | 2026-03-09 |
| 18. Directionality Detection and Tagging | v1.3 | 3/3 | Complete | 2026-03-10 |
| 19. Structured Three-Dimension Assessment | v1.3 | 3/3 | Complete | 2026-03-10 |
| 20. GO Molecular Function Suggestions | v1.3 | 2/2 | Complete | 2026-03-10 |
| 21. Wire GO Namespace Through Approval Chain | v1.3 | 1/1 | Complete | 2026-03-11 |
| 22. Fix Bulk Export SELECT | v1.3 | 1/1 | Complete | 2026-03-11 |
| 23. Reactome Data Infrastructure | v1.4 | 3/3 | Complete    | 2026-04-03 |
| 24. Database Models and Suggestion Service | v1.4 | 2/2 | Complete   | 2026-04-29 |
| 25. Proposal Workflow and Admin UI | v1.4 | 6/6 | Complete   | 2026-05-05 |
| 26. Public API and Exports | v1.4 | 8/8 | Complete    | 2026-05-06 |
| 27. Reactome Pathway Viewer | v1.4 | 4/4 | Complete   | 2026-05-06 |
| 28. KE Gene SPARQL Returns Persistent Identifiers | v1.4 | 4/4 | Complete    | 2026-05-07 |
| 29. Pure-Semantic Ranking Shift | v1.5 | 6/6 | Complete    | 2026-05-10 |
| 30. Reactome Suggestion Card Parity and Threshold Tuning | v1.5 | 2/2 | Complete    | 2026-05-10 |
| 31. Reactome Viewer Polish | v1.5 | 3/3 | Complete    | 2026-05-11 |
| 32. GO/WP Sibling Debt Sweep | v1.5 | 4/7 | In Progress|  |
| 33. Baseline Cleanup | v1.5 | 0/TBD | Not started | — |
