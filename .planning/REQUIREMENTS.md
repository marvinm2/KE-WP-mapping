# Requirements: KE-WP / KE-GO Mapping Tool

**Defined:** 2026-02-19
**Core Value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.

## v1 Requirements

Requirements for v1.0 release. Each maps to a roadmap phase.

### Deployment & Performance

- [ ] **DEPLOY-01**: SQLite WAL mode and connection pooling enabled for concurrent curator access
- [ ] **DEPLOY-02**: Embedding files migrated from pickle/dict format to NPZ matrix format
- [ ] **DEPLOY-03**: Automated database backup mechanism in place before external users can modify data
- [ ] **DEPLOY-04**: Embedding vectors normalized at precompute time; dot product replaces cosine similarity at query time (closes #65)

### Data Quality & Curation

- [ ] **CURAT-01**: Each approved mapping records the approving curator and timestamp (provenance/audit trail)
- [ ] **CURAT-02**: Duplicate mapping detection prevents submitting the same KE→pathway or KE→GO pair twice
- [ ] **CURAT-03**: Confidence level (High/Medium/Low) stored with each approved mapping and visible in browse table

### Public REST API

- [ ] **API-01**: Versioned `/api/v1/` blueprint, entirely separate from existing internal suggestion endpoints
- [ ] **API-02**: `GET /api/v1/mappings` — paginated KE-WP mapping list, filterable by KE ID, AOP ID, and pathway ID
- [ ] **API-03**: `GET /api/v1/go-mappings` — paginated KE-GO mapping list, filterable by KE ID and GO term ID
- [ ] **API-04**: Content negotiation on collection endpoints — `Accept: text/csv` returns tabular data for R/Python scripts

### Explore & Browse

- [ ] **EXPLO-01**: Explore page filterable by AOP — shows all approved KE mappings belonging to a selected AOP
- [ ] **EXPLO-02**: Explore page filterable by confidence level (High/Medium/Low)
- [ ] **EXPLO-03**: Coverage gap view — shows which KEs in a selected AOP have no approved mappings yet
- [ ] **EXPLO-04**: All API and explore-page responses include stable, permanent mapping IDs
- [ ] **EXPLO-05**: Dataset metrics dashboard showing mapping counts and coverage statistics (closes #116)
- [ ] **EXPLO-06**: Custom download interface — user filters dataset then exports the matching subset (closes #116)

### KE Selection UX

- [ ] **KE-01**: KE context panel visible during mapping workflow — shows KE description, AOP context, and biological level (closes #114)

### Exports & Dataset Publication

- [ ] **EXPRT-01**: GMT format export for KE-WP mappings, directly loadable by clusterProfiler/fgsea without preprocessing
- [ ] **EXPRT-02**: GMT format export for KE-GO mappings
- [ ] **EXPRT-03**: RDF/Turtle export of the full curated mapping database
- [ ] **EXPRT-04**: Dataset published on Zenodo with a DOI for use as a publication citation

### API Documentation

- [ ] **DOCS-01**: OpenAPI/Swagger spec auto-generated and served as interactive UI for `/api/v1/`
- [ ] **DOCS-02**: R (`httr2`) and Python (`requests`) code examples for consuming the public API
- [ ] **DOCS-03**: Rate limit policy documented for API consumers

## v2 Requirements

Deferred to after v1.0. Tracked but not in current roadmap.

### Authentication Expansion

- **AUTH-01**: ORCID OAuth as alternative to GitHub login (closes #101)
- **AUTH-02**: SURF Federation (SAML 2.0) support for Dutch research institutions (closes #101)

### ML / AI Improvements

- **ML-01**: GO hierarchy integration for term ranking (specificity weighting, redundancy filtering) (closes #80)
- **ML-02**: Evaluate sentence-embedding–optimized biomedical models as BioBERT replacement (closes #60)
- **ML-03**: Multi-tier ranking (title-only BioBERT for initial filter, description BioBERT for re-ranking) (closes #59)
- **ML-04**: User feedback learning system for suggestion improvement (closes #30)
- **ML-05**: PubMed literature mining for evidence-based suggestions (closes #27)

### Data Integration

- **DATA-01**: KEGG Pathways integration for expanded pathway coverage (closes #25)
- **DATA-02**: Data version/provenance tracking for KE and pathway sources (closes #71)

### Advanced Visualization

- **VIZ-01**: Interactive AOP network visualization for KE selection (closes #74)
- **VIZ-02**: Improved WikiPathways-native pathway viewer (closes #72)
- **VIZ-03**: Pathway comparison and gene overlap analysis tools (closes #29)

### Performance & Infrastructure

- **PERF-01**: Redis-based intelligent caching with predictive cache warming (closes #28)
- **PERF-02**: Pathway search by ontology tags and gene sets on explore page (closes #53)

## Out of Scope

| Feature | Reason |
|---------|--------|
| GraphQL API | REST is community standard for bioinformatics databases; GraphQL adds complexity without clear benefit |
| WebSocket streaming | Suggestions are fast enough synchronously; async not justified |
| Real-time collaborative editing | SQLite + small curator team — not a bottleneck |
| Auto-approval of high-confidence suggestions | Human validation is the core value proposition |
| Mobile native app | Web-first; curator workflows don't require mobile |
| KE→Gene direct mappings as output | Genes used internally as matching signal only |
| KEGG integration (v1) | WikiPathways + GO sufficient for v1; KEGG deferred to v2 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEPLOY-01 | Phase 1 | Pending |
| DEPLOY-02 | Phase 1 | Pending |
| DEPLOY-03 | Phase 1 | Pending |
| DEPLOY-04 | Phase 1 | Pending |
| CURAT-01 | Phase 2 | Pending |
| CURAT-02 | Phase 2 | Pending |
| CURAT-03 | Phase 2 | Pending |
| EXPLO-04 | Phase 2 | Pending |
| API-01 | Phase 3 | Pending |
| API-02 | Phase 3 | Pending |
| API-03 | Phase 3 | Pending |
| API-04 | Phase 3 | Pending |
| EXPLO-01 | Phase 4 | Pending |
| EXPLO-02 | Phase 4 | Pending |
| EXPLO-03 | Phase 4 | Pending |
| EXPLO-05 | Phase 4 | Pending |
| EXPLO-06 | Phase 4 | Pending |
| KE-01 | Phase 4 | Pending |
| EXPRT-01 | Phase 5 | Pending |
| EXPRT-02 | Phase 5 | Pending |
| EXPRT-03 | Phase 5 | Pending |
| EXPRT-04 | Phase 5 | Pending |
| DOCS-01 | Phase 6 | Pending |
| DOCS-02 | Phase 6 | Pending |
| DOCS-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-02-19*
*Last updated: 2026-02-19 after roadmap creation — all 25 requirements mapped*
