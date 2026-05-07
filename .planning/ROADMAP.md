# Roadmap: KE-WP / KE-GO Mapping Tool

## Milestones

- ✅ **v1.0 MVP** — Phases 1–7 (shipped 2026-02-23)
- ✅ **v1.1 Visuals** — Phases 8–12 (shipped 2026-03-04)
- ✅ **v1.2 Curation Depth** — Phases 13–16 (shipped 2026-03-06)
- ✅ **v1.3 GO Assessment Quality** — Phases 17–22 (shipped 2026-03-11)
- 🚧 **v1.4 Reactome Integration** — Phases 23–27 (in progress)

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

### v1.4 Reactome Integration (Phases 23–27)

- [x] **Phase 23: Reactome Data Infrastructure** — Precompute pipeline producing pathway metadata, gene annotations, and BioBERT embeddings (completed 2026-04-03)
- [x] **Phase 24: Database Models and Suggestion Service** — DB schema, model classes, carry-field constants, and ranked suggestion engine with gene overlap signal (completed 2026-04-29)
- [x] **Phase 25: Proposal Workflow and Admin UI** — Submission, duplicate detection, admin approve/reject, and Reactome tab in mapping workflow (completed 2026-05-05)
- [x] **Phase 26: Public API and Exports** — Versioned API endpoint, GMT export, RDF export, and explore page integration (completed 2026-05-06)
- [x] **Phase 27: Reactome Pathway Viewer** — DiagramJS embed in mapping workflow with gene highlighting (completed 2026-05-06)
- [ ] **Phase 28: KE Gene SPARQL Returns Persistent Identifiers** — Rewrite shared ke_genes.py SPARQL helper to return strict {ncbi, hgnc, symbol} triples from a single non-federated AOP-Wiki query; carry persistent IDs through three suggestion services and add genes_full to /ke_genes/<ke_id> while preserving Phase 27 frontend's genes field

## Phase Details

### Phase 23: Reactome Data Infrastructure
**Goal**: Precomputed data files for ~2,700 human Reactome pathways exist in `data/` and are ready for the suggestion service to load
**Depends on**: Nothing (independent of application code)
**Requirements**: RDATA-01, RDATA-02, RDATA-03, RDATA-04, RDATA-05
**Success Criteria** (what must be TRUE):
  1. Running the download script produces `reactome_pathway_metadata.json` with stable IDs matching `^R-HSA-[0-9]+$` (no version suffixes) and only Homo sapiens pathways
  2. Running the annotation script produces `reactome_gene_annotations.json` with HGNC gene symbols sourced from the GMT file; spot-checking a known pathway (e.g. "MAPK signaling") returns recognizable gene symbols
  3. Running the embedding script produces `reactome_pathway_embeddings.npz` loadable by the existing `BiologicalEmbeddingService`; vector shape matches pathway count
  4. Disease branch pathways (descendants of R-HSA-1643685) are absent from metadata; pathways with fewer than 3 or more than 500 annotated genes are absent
**Plans:** 3/3 plans complete
Plans:
- [x] 23-01-PLAN.md — GMT download, gene annotations, disease exclusion, gene count filtering
- [x] 23-02-PLAN.md — API metadata fetch, HTML stripping, dual BioBERT embeddings
- [x] 23-03-PLAN.md — Gap closure: fix integer dbId resolution in disease exclusion, regenerate all data files

### Phase 24: Database Models and Suggestion Service
**Goal**: Curators can receive AI-ranked Reactome pathway suggestions for a selected KE, with suggestion scores driven by both BioBERT similarity and gene overlap
**Depends on**: Phase 23
**Requirements**: RSUG-01, RSUG-02, RSUG-03
**Success Criteria** (what must be TRUE):
  1. Selecting a KE on the mapper page and navigating to the Reactome suggestions panel returns a ranked list of Reactome pathways within normal response time
  2. The suggestion list shows both an embedding similarity score and a gene overlap contribution; pathways with zero matching genes rank lower than those with several
  3. Reactome-specific thresholds (minimum score, max results, gene/embedding weights) can be changed in `scoring_config.yaml` without touching Python source
  4. `ke_reactome_mappings` and `ke_reactome_proposals` tables exist in the database after app startup; `REACTOME_PROPOSAL_CARRY_FIELDS` constant is defined and covers all columns needed at approval time
**Plans:** 2/2 plans complete
Plans:
- [x] 24-01-PLAN.md — DB tables, model classes, carry-field constant, ReactomeSuggestionConfig dataclass, scoring_config.yaml section
- [x] 24-02-PLAN.md — ReactomeSuggestionService class with embedding+gene scoring, ServiceContainer wiring

### Phase 25: Proposal Workflow and Admin UI
**Goal**: Curators can submit KE→Reactome mapping proposals and admins can approve or reject them through a dedicated admin dashboard, with the full provenance chain intact
**Depends on**: Phase 24
**Requirements**: RCUR-01, RCUR-02, RCUR-03, RCUR-04
**Success Criteria** (what must be TRUE):
  1. A curator can select a KE and a Reactome pathway from the Reactome tab on the mapper page, choose a confidence level, and submit a proposal; the proposal appears in the admin queue immediately
  2. Attempting to submit the same KE→Reactome pair a second time shows a duplicate-detection warning and blocks the submission
  3. An admin can view pending Reactome proposals in the admin dashboard, approve one with a comment, and the approved mapping appears in the database with all carry fields (pathway name, species, suggestion score, confidence) non-NULL
  4. An admin can reject a Reactome proposal with a reason; the proposal is marked rejected and does not appear as an approved mapping
**Plans:** 6/6 plans complete
Plans:
- [x] 25-01-PLAN.md — Backend models, schemas, and search method (ReactomeProposalModel.update_proposal_status + get_all_proposals; ReactomeMappingModel.update_reactome_mapping + check_reactome_mapping_exists_with_proposals; ReactomeMappingSchema + ReactomeCheckEntrySchema; search_reactome_terms)
- [x] 25-02-PLAN.md — API endpoints (/submit_reactome_mapping, /check_reactome_entry, /search_reactome, /suggest_reactome) + api blueprint wiring
- [x] 25-03-PLAN.md — Admin endpoints + admin_reactome_proposals.html template + cross-link updates + admin blueprint wiring
- [x] 25-04-PLAN.md — Mapper-page Reactome tab markup (third button, #reactome-tab-content with sub-tabs, confidence buttons, submit form)
- [x] 25-05-PLAN.md — Frontend JS (handleTabSwitch 3-way, loadReactomeSuggestions, search type-ahead, duplicate detection, confidence + submit handlers) — visual verification scope-limited to steps 1–4 (approved-1-4); steps 5–10 deferred to 25-06 e2e + production smoke
- [x] 25-06-PLAN.md — End-to-end tests covering RCUR-01..04 (test_reactome_e2e.py + augmentations to existing reactome test files)

### Phase 26: Public API and Exports
**Goal**: Approved KE→Reactome mappings are accessible via a versioned public API endpoint and downloadable as GMT and RDF files
**Depends on**: Phase 24, Phase 25
**Requirements**: REXP-01, REXP-02, REXP-03, REXP-04
**Success Criteria** (what must be TRUE):
  1. `GET /api/v1/reactome-mappings` returns paginated JSON with approved mappings; `Accept: text/csv` returns tabular CSV; filtering by KE ID or Reactome pathway ID narrows results correctly
  2. Downloading the Reactome GMT file produces a valid GMT format (pathway name tab stable ID tab gene symbols) loadable by clusterProfiler/fgsea without error
  3. Downloading the Reactome RDF file produces valid Turtle syntax with full provenance triples (proposer, timestamp, confidence, suggestion score)
  4. Approved Reactome mappings appear in the explore page DataTable and can be filtered alongside WP and GO mappings
**Plans**: TBD

### Phase 27: Reactome Pathway Viewer
**Goal**: Curators can view the Reactome pathway diagram directly within the mapping workflow tab without leaving the application
**Depends on**: Phase 25
**Requirements**: RVIEW-01
**Success Criteria** (what must be TRUE):
  1. Selecting a Reactome pathway suggestion on the mapper tab loads the Reactome DiagramJS diagram for that pathway inline within the page
  2. Genes from the KE's associated mappings are highlighted in the diagram via `flagItems()` when the diagram finishes loading
  3. If the DiagramJS CDN is unavailable, the tab remains functional for submission without throwing a JavaScript error
**Plans**: TBD

### Phase 28: KE Gene SPARQL Returns Persistent Identifiers
**Goal**: The shared `get_genes_from_ke()` helper in `src/suggestions/ke_genes.py` returns a strict-shape list of dicts `{ncbi, hgnc, symbol}` (NCBI Gene ID + HGNC accession + HGNC symbol) sourced from a single non-federated SPARQL query against AOP-Wiki RDF; downstream consumers in Reactome, WikiPathways, and GO suggestion services consume the dict shape and restore non-empty gene-overlap signals; the public `/ke_genes/<ke_id>` endpoint adds a `genes_full` field while preserving the legacy `genes` (list of symbol strings) for Phase 27's `flagItems()`.
**Depends on**: Phase 27
**Requirements**: KEGENE-01
**Context**:
  - Defect predates Phase 27. The pre-Phase-28 SPARQL `?object edam:data_2298 ?hgnc` returns numeric HGNC accession IDs (`"11892"` for TNF), but the variable was named `?hgnc` and labeled "symbol" downstream. First introduced in commit `a325411` (2025-08-08).
  - All three suggestion services have silently produced empty gene-overlap signal since then. Phase 27's `flagItems()` is the most visible symptom.
  - Persistent IDs (NCBI Gene + HGNC accession) were chosen over a symbols-only fix because HGNC routinely renames genes (e.g. `C11orf95 -> ZFTA`); persistent IDs don't drift.
  - Empirically confirmed via live AOP-Wiki SPARQL probes (2026-05-07): all three identifiers are natively present on every gene node (96.4% complete coverage; 100% on the two test KEs). No federated query, no local cross-ref table needed.
**Success Criteria** (what must be TRUE):
  1. `get_genes_from_ke()` returns `List[Dict[str, str]]` with strict `{ncbi, hgnc, symbol}` shape; bindings missing any field are dropped silently (D-04).
  2. `GET /ke_genes/<ke_id>` returns JSON with both `genes` (legacy list of HGNC symbol strings) and `genes_full` (list of `{ncbi, hgnc, symbol}` dicts).
  3. WikiPathways `_find_pathways_by_genes` returns non-empty pathway results for KEs whose genes overlap WP pathway annotations.
  4. Reactome `_compute_gene_overlap_scores` produces non-zero `gene_overlap` for KE/pathway pairs that share genes.
  5. GO `_compute_gene_overlap_scores_for` produces non-zero gene-driven GO suggestion scores.
  6. Phase 27's `flagItems()` continues to receive HGNC symbol strings via the `genes` field (no Phase 27 frontend regression); embedded diagram now flags non-zero entities.
  7. SPARQL response cache automatically invalidates via the version-comment trick (`# ke-genes-query-v2 ...` inside the f-string changes `md5(query)`); no DB migration required.
**Plans:** 4 plans
Plans:
- [ ] 28A-PLAN.md — Rewrite get_genes_from_ke() helper with strict-triple SPARQL and version-comment cache bust; new tests/test_ke_genes.py with five parser unit tests
- [ ] 28B-PLAN.md — Update three suggestion-service consumers (pathway.py, reactome.py, go.py) to consume List[Dict] and extract symbol field at call sites
- [ ] 28C-PLAN.md — Add genes_full field to GET /ke_genes/<ke_id> response while preserving legacy genes (list of symbol strings)
- [ ] 28D-PLAN.md — Update .planning/ROADMAP.md Phase 28 entry and add KEGENE-01 to .planning/REQUIREMENTS.md

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
| 28. KE Gene SPARQL Returns Persistent Identifiers | v1.4 | 0/4 | Not Started | — |

