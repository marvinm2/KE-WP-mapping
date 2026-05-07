# Requirements: KE-WP/KE-GO/KE-Reactome Mapping Tool

**Defined:** 2026-03-11
**Core Value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.

## v1.4 Requirements

Requirements for v1.4 Reactome Integration. Each maps to roadmap phases.

### Data Infrastructure

- [x] **RDATA-01**: Precompute script downloads Reactome pathway metadata (names, stable IDs, descriptions) from bulk files
- [x] **RDATA-02**: Precompute script extracts HGNC gene annotations per pathway from Reactome GMT file
- [x] **RDATA-03**: Precompute script generates BioBERT embeddings for Reactome pathway names/descriptions as NPZ
- [x] **RDATA-04**: Precompute script filters pathways by gene count (3-500) and excludes Disease branch
- [x] **RDATA-05**: Stable IDs normalized (version suffix stripped) before storage

### Suggestion Engine

- [x] **RSUG-01**: BioBERT embedding-based KE→Reactome suggestions ranked by similarity score
- [x] **RSUG-02**: Gene overlap signal contributes to Reactome suggestion scoring
- [x] **RSUG-03**: Reactome-specific scoring thresholds configurable independently in scoring_config.yaml

### Curation Workflow

- [x] **RCUR-01**: Curator can submit KE→Reactome mapping proposal with confidence
- [x] **RCUR-02**: Admin can approve/reject Reactome proposals with full provenance
- [x] **RCUR-03**: Duplicate detection prevents re-submitting same KE→Reactome pair
- [x] **RCUR-04**: Reactome tab in mapping workflow alongside WP and GO tabs

### Exports & API

- [x] **REXP-01**: Separate Reactome GMT export file (clusterProfiler/fgsea compatible)
- [x] **REXP-02**: Reactome RDF/Turtle export with full provenance
- [x] **REXP-03**: `GET /api/v1/reactome-mappings` public endpoint with pagination and filters
- [x] **REXP-04**: Reactome mappings in explore page DataTable

### Viewer

- [ ] **RVIEW-01**: Reactome DiagramJS pathway viewer embed in mapping workflow

### Helper Library

- [ ] **KEGENE-01**: `get_genes_from_ke()` returns a strict-shape `List[Dict[str, str]]` with fields `{ncbi, hgnc, symbol}` (NCBI Gene ID + HGNC accession + HGNC symbol), sourced from a single non-federated AOP-Wiki SPARQL query; the public `GET /ke_genes/<ke_id>` adds a `genes_full` dict-list field while preserving `genes` as `[symbol]` for Phase 27 backward-compat; downstream gene-overlap signals across Reactome, WP, and GO suggestion services become non-empty for KEs with overlapping genes

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Human Phenotype Ontology

- **HPO-01**: KE→HPO term suggestion engine
- **HPO-02**: HPO precompute pipeline
- **HPO-03**: HPO proposal workflow and exports

### Assessment Analytics

- **ASMT-05**: Expose individual dimension scores in API responses alongside final confidence
- **ASMT-06**: Inter-curator agreement metrics for assessment dimensions

### Embedding Model Evaluation

- **EVAL-01**: Benchmark BioBERT alternatives for sentence-level similarity (#60)
- **EVAL-02**: Ground truth KE-pathway mapping dataset for model comparison

## Out of Scope

| Feature | Reason |
|---------|--------|
| Reactome hierarchy/superpathway browsing | Flat pathway list sufficient for curation; hierarchy adds UI complexity |
| Live Reactome API queries at runtime | Violates precompute-everything pattern; bulk download is faster and more reliable |
| Reactome three-dimension assessment | GO-specific feature; Reactome mappings use standard confidence like WP |
| Reactome directionality detection | Pathway names don't have directional prefixes like GO terms |
| UniProt-based gene annotations | HGNC symbols used throughout; GMT file provides HGNC directly |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| RDATA-01 | Phase 23 | Complete |
| RDATA-02 | Phase 23 | Complete |
| RDATA-03 | Phase 23 | Complete |
| RDATA-04 | Phase 23 | Complete |
| RDATA-05 | Phase 23 | Complete |
| RSUG-01 | Phase 24 | Complete |
| RSUG-02 | Phase 24 | Complete |
| RSUG-03 | Phase 24 | Complete |
| RCUR-01 | Phase 25 | Complete |
| RCUR-02 | Phase 25 | Complete |
| RCUR-03 | Phase 25 | Complete |
| RCUR-04 | Phase 25 | Complete |
| REXP-01 | Phase 26 | Complete |
| REXP-02 | Phase 26 | Complete |
| REXP-03 | Phase 26 | Complete |
| REXP-04 | Phase 26 | Complete |
| RVIEW-01 | Phase 27 | Pending |
| KEGENE-01 | Phase 28 | Pending |

**Coverage:**
- v1.4 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-05-07 after Phase 28 redefinition (KEGENE-01 added; all 18 requirements mapped)*
