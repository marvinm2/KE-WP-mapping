# Roadmap: KE-WP / KE-GO Mapping Tool — v1.0.0

## Overview

This roadmap takes a functional prototype to a production-quality, citable bioinformatics database. The existing BioBERT suggestion engine and curation workflow are fully operational; the gaps are deployment safety, data provenance, external API access, and publication-readiness. Phases are ordered strictly by dependency: a broken deployment cannot host trustworthy data, missing provenance columns cannot be retroactively added after curation begins, and documentation cannot be written until routes are frozen.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Deployment Hardening** - Make production-safe before any external user submits data
- [ ] **Phase 2: Data Model and Audit Trail** - Add provenance, stable IDs, and quality fields before the API freezes the schema
- [ ] **Phase 3: Stable Public REST API** - Versioned, publicly accessible read API for downstream bioinformaticians
- [ ] **Phase 4: Curator UX and Explore** - Duplicate detection, filtering, coverage gaps, and dataset metrics
- [ ] **Phase 5: Exports and Dataset Publication** - GMT exports and Zenodo DOI for paper citation
- [ ] **Phase 6: API Documentation** - Lock in contracts with OpenAPI spec and consumer code examples

## Phase Details

### Phase 1: Deployment Hardening
**Goal**: The application runs safely in production — database survives container recreation, memory stays within bounds, concurrent curator writes do not corrupt data, and embedding files load reliably
**Depends on**: Nothing (first phase)
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):
  1. The SQLite database file persists across Docker container recreation and is never stored inside the container image
  2. Four Gunicorn workers start and serve requests using a single loaded copy of the BioBERT model (memory stays under 4GB total)
  3. Multiple curators can submit proposals simultaneously without "database is locked" errors
  4. Embedding files load correctly without `allow_pickle=True`; dot-product similarity replaces cosine computation at query time
**Plans**: TBD

### Phase 2: Data Model and Audit Trail
**Goal**: Every mapping carries complete provenance — who approved it, when, at what confidence, with what suggestion score — and every mapping has a stable identifier that will not change after publication
**Depends on**: Phase 1
**Requirements**: CURAT-01, CURAT-02, CURAT-03, EXPLO-04
**Success Criteria** (what must be TRUE):
  1. Each approved mapping in the database records the approving curator's GitHub username and the approval timestamp
  2. Submitting a proposal for a KE-pathway or KE-GO pair that already has an approved mapping or pending proposal is blocked with a clear error message
  3. Confidence level (High/Medium/Low) is stored with each approved mapping and visible in the browse table
  4. Every mapping returned by any API endpoint or export has a stable UUID that does not change between requests or deployments
**Plans**: TBD

### Phase 3: Stable Public REST API
**Goal**: External bioinformaticians and R/Python scripts can read the curated mapping database over HTTP without a GitHub account, using a versioned API that will not break when internal endpoints change
**Depends on**: Phase 2
**Requirements**: API-01, API-02, API-03, API-04
**Success Criteria** (what must be TRUE):
  1. A Python script using `requests.get("https://.../api/v1/mappings")` returns paginated KE-WP mappings without authentication
  2. An R script using `httr2` can filter KE-WP mappings by KE ID, AOP ID, or pathway ID and receive only the matching rows
  3. The same `/api/v1/go-mappings` endpoint returns KE-GO mappings filterable by KE ID and GO term ID
  4. Passing `Accept: text/csv` to any collection endpoint returns a tabular CSV response loadable directly by `read.csv()` or `pandas.read_csv()`
**Plans**: TBD

### Phase 4: Curator UX and Explore
**Goal**: Curators can efficiently navigate the mapping database, see which KEs still need coverage, and filter approved mappings by AOP, confidence, and other dimensions; dataset metrics are visible at a glance
**Depends on**: Phase 2
**Requirements**: EXPLO-01, EXPLO-02, EXPLO-03, EXPLO-05, EXPLO-06, KE-01
**Success Criteria** (what must be TRUE):
  1. A curator selecting a KE in the mapping workflow sees that KE's description, AOP context, and biological level without leaving the page
  2. The explore page can be filtered by AOP to show only KE mappings belonging to that AOP
  3. The explore page can be filtered by confidence level to show only High, Medium, or Low confidence mappings
  4. A coverage gap view shows which KEs in a selected AOP have no approved mapping, so curators can prioritize uncovered KEs
  5. A dataset metrics dashboard shows total mapping counts and coverage statistics; users can filter the dataset and export only the matching subset
**Plans**: TBD

### Phase 5: Exports and Dataset Publication
**Goal**: The curated database is downloadable in formats that bioinformatics tools consume directly, and it is registered with a permanent DOI that researchers can cite in publications
**Depends on**: Phase 3
**Requirements**: EXPRT-01, EXPRT-02, EXPRT-03, EXPRT-04
**Success Criteria** (what must be TRUE):
  1. A GMT file for KE-WP mappings is downloadable and loads directly into clusterProfiler or fgsea without any preprocessing or format conversion
  2. A GMT file for KE-GO mappings is downloadable in the same way
  3. An RDF/Turtle export of the full curated mapping database is downloadable and parseable by rdflib
  4. The dataset has a registered Zenodo DOI that resolves to a versioned dataset landing page suitable for use as a paper citation
**Plans**: TBD

### Phase 6: API Documentation
**Goal**: The public API is fully documented with an interactive spec, consumer code examples in R and Python, and a published rate limit policy — locking in the stable contract before external researchers depend on it
**Depends on**: Phase 3
**Requirements**: DOCS-01, DOCS-02, DOCS-03
**Success Criteria** (what must be TRUE):
  1. An interactive OpenAPI/Swagger UI is served at a stable URL where users can browse all `/api/v1/` endpoints and execute test requests in the browser
  2. The documentation page includes working R (`httr2`) and Python (`requests`) code examples that a researcher can copy-paste to retrieve mappings
  3. The rate limit policy is documented — including the numeric limit, the `Retry-After` behavior, and a `time.sleep()` example — so API consumers know how to write polite scripts
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Deployment Hardening | 0/TBD | Not started | - |
| 2. Data Model and Audit Trail | 0/TBD | Not started | - |
| 3. Stable Public REST API | 0/TBD | Not started | - |
| 4. Curator UX and Explore | 0/TBD | Not started | - |
| 5. Exports and Dataset Publication | 0/TBD | Not started | - |
| 6. API Documentation | 0/TBD | Not started | - |
