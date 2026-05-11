# Requirements: v1.5 Scoring & Polish

**Defined:** 2026-05-10
**Core Value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.

## v1.5 Requirements

### Scoring Defaults (pure-semantic ranking)

- [x] **SEMRANK-01**: WP suggestion ranking uses BioBERT cosine similarity only — gene overlap is no longer factored into rank order
- [x] **SEMRANK-02**: GO suggestion ranking uses BioBERT cosine similarity only — gene overlap is no longer factored into rank order; IC boost (v1.2) retained as separate post-combine step
- [x] **SEMRANK-03**: Reactome suggestion ranking uses BioBERT cosine similarity only — gene overlap is no longer factored into rank order
- [x] **SEMRANK-04**: `scoring_config.yaml` updated with v1.5 pure-semantic defaults; legacy hybrid weights recorded as deprecated with rationale

### Suggestion Display (gene-overlap demoted to chip)

- [x] **SUGDISP-01**: Gene-overlap shown as auxiliary chip on each suggestion card across WP / GO / Reactome (count + overlap fraction visible; not a ranking input)
- [x] **SUGDISP-02**: Reactome suggestion-card scoring breakdown layout matches WP (signal chips, score badge, info density consistent)

### Reactome Ranking Quality

- [x] **REASCORE-01**: Reactome ranking quality on a representative KE sample is qualitatively comparable to WP (curator spot-check across ≥5 KEs covering different bio levels)
- [x] **REASCORE-02**: Reactome thresholds in `scoring_config.yaml` re-tuned post pure-semantic shift (min similarity, top-N cap) so suggestion lists feel curated, not noisy

### Reactome Viewer Polish (Phase 27 carry-forward)

- [x] **VIEWFIX-01**: `ReactomeDiagramEmbed` catch handler does not destroy the mount on second-failure recovery (WR-01)
- [x] **VIEWFIX-02**: `onDiagramLoaded` handler not accumulated across pathway swaps (WR-02)
- [x] **VIEWFIX-03**: Async `loadDiagram` failures route through the error-card path, not silent (WR-03)
- [x] **VIEWFIX-04**: `_failed` flag scope tied to current load attempt, not sticky across retries (WR-04)
- [x] **VIEWFIX-05**: `prefetchKeGenes` race resolved — `flagItems` always called with the resolved gene list when genes exist for the KE

### GO/WP Sibling Debt Sweep

- [x] **DEBT-01**: `admin_go_proposals.html` modal uses XSS-safe rendering (port C-1 fix from `admin_reactome_proposals.html`)
- [x] **DEBT-02**: `admin_proposals.html` (KE-WP) modal uses XSS-safe rendering (port C-1 fix from `admin_reactome_proposals.html`)
- [ ] **DEBT-03**: `ke_go_proposals` has partial-unique pending index `(ke_id, go_id) WHERE status='pending' AND mapping_id IS NULL` (port H-2 from Reactome) with race-safe duplicate handling
- [x] **DEBT-04**: `ke_wp_proposals` has partial-unique pending index `(ke_id, pathway_id) WHERE status='pending' AND mapping_id IS NULL` (port H-2 from Reactome) with race-safe duplicate handling
- [ ] **DEBT-05**: `download_ke_go_rdf` returns 503 on empty graph (port from Reactome RDF route)
- [x] **DEBT-06**: `download_ke_wp_rdf` returns 503 on empty graph (port from Reactome RDF route)

### Baseline Cleanup

- [ ] **CLEAN-01**: `/confidence_assessment` route either renders correctly with a real template or is removed cleanly (no 500)
- [ ] **CLEAN-02**: `/dataset/{metadata,versions,citation,datacite}` either provisions a working `metadata_manager` (Zenodo/DataCite creds) or is downgraded to 503 / hidden behind a feature flag
- [ ] **CLEAN-03**: `test_login_redirect` passes (root-cause Phase 14 OAuth route drift)
- [ ] **CLEAN-04**: `test_guest_login_page_renders` passes
- [ ] **CLEAN-05**: Test coverage at or above the 45% threshold OR threshold downgraded with a documented rationale

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### KE-Reactome Three-Dimension Assessment

- **REACTASMNT-01**: KE-Reactome confidence input uses Connection / Specificity / Evidence three-dimension assessment (mirroring KE-GO, v1.3) — *deferred: user chose to keep WP-style 3-button confidence for v1.5; revisit if curators ask for richer confidence capture on Reactome*

### KE-WP Three-Dimension Assessment

- **WPASMNT-01**: KE-WP confidence input migrated to three-dimension assessment for consistency with KE-GO — *deferred: not requested in v1.5; same rationale as REACTASMNT-01*

### Visual Gene Highlighting on Reactome Diagram

- **RVIEWHL-01**: `flagItems` produces visible gene highlight on Reactome DiagramJS canvas — *deferred from v1.4; needs HGNC↔diagram-entity mapping investigation, possibly NCBI-ID-based flagging*

### External Integrations

- **DATA-01**: KEGG Pathways integration — deferred from v1.0
- **AUTH-08**: User account linking across OAuth providers — deferred from v1.2
- **GOHI-08**: GO hierarchy visualization / term tree browser — deferred from v1.2

### Domain Calibration

- **ICCAL-01**: IC weight calibration session with domain expert (open since v1.2) — coordination dependency, not pure dev work
- **OAUTHE2E-01**: Human E2E testing of ORCID / LS Login / SURFconext with real credentials (open since v1.2) — coordination dependency

## Out of Scope

Explicitly excluded for v1.5. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Three-dimension assessment for KE-Reactome / KE-WP | User explicitly scoped v1.5 to keep WP-style 3-button confidence; not adding cross-resource assessment in this milestone |
| Restoring gene-overlap as a ranking signal under any weight | User chose pure-semantic; revisit only if curator feedback shows ranking degradation |
| New pathway-resource integrations (KEGG, HPO, etc.) | v1.5 is refinement, not expansion |
| Visual gene highlight on Reactome diagram (RVIEWHL-01) | Accepted as structural-only per Plan 27-CONTEXT; revisit in a future milestone with proper investigation |
| Live AOP-Wiki sync | Pre-loaded KE list remains the design |
| Mobile native app | Web-first |
| Migration to PostgreSQL | SQLite WAL still meets curator-team scale |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEMRANK-01 | Phase 29 | Complete |
| SEMRANK-02 | Phase 29 | Complete |
| SEMRANK-03 | Phase 29 | Complete |
| SEMRANK-04 | Phase 29 | Complete |
| SUGDISP-01 | Phase 29 | Complete |
| SUGDISP-02 | Phase 30 | Complete |
| REASCORE-01 | Phase 30 | Complete |
| REASCORE-02 | Phase 30 | Complete |
| VIEWFIX-01 | Phase 31 | Complete |
| VIEWFIX-02 | Phase 31 | Complete |
| VIEWFIX-03 | Phase 31 | Complete |
| VIEWFIX-04 | Phase 31 | Complete |
| VIEWFIX-05 | Phase 31 | Complete |
| DEBT-01 | Phase 32 | Complete |
| DEBT-02 | Phase 32 | Complete |
| DEBT-03 | Phase 32 | Pending |
| DEBT-04 | Phase 32 | Complete |
| DEBT-05 | Phase 32 | Pending |
| DEBT-06 | Phase 32 | Complete |
| CLEAN-01 | Phase 33 | Pending |
| CLEAN-02 | Phase 33 | Pending |
| CLEAN-03 | Phase 33 | Pending |
| CLEAN-04 | Phase 33 | Pending |
| CLEAN-05 | Phase 33 | Pending |

**Coverage:**
- v1.5 requirements: 24 total
- Mapped to phases: 24 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-10*
*Last updated: 2026-05-10 after v1.5 ROADMAP creation (phase mappings filled)*
