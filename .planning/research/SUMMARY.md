# Project Research Summary

**Project:** KE Mapping Tool — v1.0.0 Maturation
**Domain:** Bioinformatics curation database / biological pathway annotation REST API
**Researched:** 2026-02-19
**Confidence:** HIGH

## Executive Summary

This project is a prototype-to-production transition for a specialist bioinformatics curation tool — a category well-studied through reference implementations at WikiPathways, Reactome, ChEMBL, AOP-Wiki, and MSigDB. The existing Flask/BioBERT/SQLite stack is sound and requires no migration. The gaps are structural: the public REST API is not yet versioned or documented, the Docker deployment has several data-loss and memory-blow-up risks, and the export layer is fragile enough to break downstream R/Python pipelines. All of these are known failure patterns in bioinformatics database tooling with well-documented fixes.

The recommended approach is to ship v1.0 by addressing deployment hardening first (SQLite WAL mode, Gunicorn preload, Docker volume for database), then build the stable versioned REST API as a new Blueprint isolated from the existing internal UI API, then stabilize exports and documentation so the tool can be cited in a paper. The differentiating features — BioBERT suggestion engine, AOP context panel, and dual KE-WP/KE-GO mapping — are already functional and unique in the domain; the work is making them trustworthy and accessible to downstream bioinformaticians, not rebuilding them.

The key risk is data provenance: curation decisions made before the audit trail, stable identifiers, and scoring provenance fields are added are difficult to reconstruct for publication. This must be addressed before any curated data is used in publication figures. The secondary risk is deployment: the current Docker configuration will lose the database on container recreation and blow up memory with 4x BioBERT loads. Both risks have specific, low-effort fixes identified in research.

---

## Key Findings

### Recommended Stack

The existing stack (Flask 3.1.2, SQLite, BioBERT via sentence-transformers, pandas, Gunicorn, Docker Compose) is the right stack for this domain. No migration is warranted. Two additions are needed: `rdflib>=7.0.0` for RDF/Turtle export (not currently in requirements.txt) and either `flask-restx>=1.3.0` or `flasgger>=0.9.7` for OpenAPI documentation. Both `pyarrow` and `openpyxl` must move from optional to required dependencies so all advertised export formats work reliably in production.

**Core technologies:**
- Flask Blueprint app factory (existing) — add a new `v1_api_bp` with `url_prefix="/api/v1"` for the stable public API; keep existing `api_bp` for UI-internal endpoints
- SQLite with WAL mode — enable `PRAGMA journal_mode=WAL` and `busy_timeout=10000` before any multi-worker production traffic
- Gunicorn with `--preload-app` — required to prevent 4x BioBERT memory duplication across workers
- rdflib 7.x — add to requirements.txt for Turtle/RDF export
- Flask-RESTX or flasgger — OpenAPI/Swagger docs are table stakes for any bioinformatics API consumer

### Expected Features

The two distinct user groups (curators / AOP domain experts; bioinformaticians / downstream API consumers) have non-overlapping top priorities. Curators need duplicate detection, rejection reasons, and AOP context in the UI. Bioinformaticians need stable identifiers, versioned bulk downloads, GMT export for clusterProfiler/fgsea, and publicly accessible endpoints without GitHub OAuth.

**Must have for v1.0 (table stakes):**
- Filter and search the explore view by AOP, KE, pathway, GO term, confidence level — every annotation database provides this; currently missing server-side
- GMT export for KE-WP mappings — direct clusterProfiler/fgsea integration; no existing tool provides this for AOP gene sets; low effort
- Confidence level visible in the explore table — already in DB, just not displayed
- Stable mapping IDs exposed in UI and all API responses — required for paper citations and cross-references
- Dataset DOI registered on Zenodo — required for any publication citing this database
- Public read access to explore page and all GET API endpoints without GitHub OAuth login
- At minimum a human-readable API documentation page listing all endpoints
- Coverage gap view showing which KEs have no mapping yet

**Should have after launch (v1.x differentiators):**
- GMT export for KE-GO mappings — once KE-GO volume is sufficient
- OpenAPI/Swagger spec — after routes are stable
- Curator attribution in API responses and exports (FAIR provenance)
- Score breakdown visible on suggestion cards (explainability)
- Versioned dataset releases with changelog notes

**Defer to v2+:**
- Bulk AOP-level curation review — high complexity, design requires usage data
- ORCID/SURF federation authentication — important for institutional users but significant scope
- WP + GO cross-validation consistency signal — depends on both mapping sets being populated
- Literature mining for evidence-based suggestions
- KEGG Pathways integration

### Architecture Approach

The correct architecture is a dual-Blueprint split: the existing `api_bp` (no URL prefix) remains as the UI-internal API that can evolve freely, and a new `v1_api_bp` with `url_prefix="/api/v1"` provides the stable public REST API. This pattern is what ChEMBL, Reactome, and WikiPathways all use. The v1 API reads only from SQLite (no SPARQL, no BioBERT) — this keeps latency predictable and allows generous rate limits. Content negotiation via Accept header (JSON default, text/csv, text/turtle) makes the same endpoint usable from R `httr2` and Python `requests` without extra parameters. Offset/limit pagination following ChEMBL's `page_meta` envelope is appropriate for this dataset size and is natively supported by `httr2::iterate_with_offset()`.

**Major components:**
1. `v1_api_bp` (new: `src/blueprints/v1_api.py`) — stable public REST API, `/api/v1/*`, GET endpoints public, POST requires auth
2. `MappingModel` / `GoMappingModel` (extend existing) — add `get_mappings_paginated(filters, limit, offset)` methods; these are the only data access layer the v1 API touches
3. Exporters (`src/exporters/`) — freeze column names with explicit stable-name mapping; add `schema_version` to all export files
4. Discovery endpoint (`GET /api/v1/`) — returns API version, schema version, resource URLs, documentation link; self-orienting for R/Python consumers

### Critical Pitfalls

1. **SQLite data loss on container recreation** — the database defaults to a relative path inside the container; it is destroyed on container rebuild. Fix: change `DATABASE_PATH` default to `/app/data/ke_wp_mapping.db` and mount as a Docker volume before any external user submits data. This is the highest-urgency fix because data loss is irreversible.

2. **Gunicorn 4x BioBERT memory explosion** — without `--preload-app`, each of 4 workers loads BioBERT independently (~400MB each = ~1.6GB just for model weights before requests). Fix: add `--preload-app` to the Gunicorn command and extend `--start-period` to 120s in the Docker health check.

3. **API without versioning locks in breaking changes** — the existing `api_bp` has no URL prefix; field names, response shapes, and route names are unversioned. Bioinformatics scripts in paper supplements run years after publication. Fix: new `v1_api_bp` with frozen field names; never rename a field once published.

4. **No audit trail for curation decisions** — no record of which suggestions were presented, what score was shown, or who approved. Fix: add `suggestion_score`, `suggestion_method`, `approved_by`, `approved_at`, and `scoring_config_version` columns before any curated data is used in publication figures. Retroactive reconstruction is not possible.

5. **GitHub OAuth gates public data** — requiring GitHub login to read approved mappings excludes paper reviewers, R/Python scripts, and collaborators without GitHub accounts. Fix: all GET endpoints on `/api/v1/` and the explore page must be publicly accessible without authentication.

---

## Implications for Roadmap

Based on combined research, the work falls into six phases ordered by dependency and urgency. Phases 1-2 are pre-conditions for any other work. Phases 3-4 deliver the core v1.0 contract. Phases 5-6 are publication-readiness polish.

### Phase 1: Deployment Hardening

**Rationale:** Data loss and memory blow-up are irreversible and block everything else. These must be fixed before any external user submits data or any production traffic arrives. No new features should be built on a broken foundation.

**Delivers:** A production-safe deployment: database survives container recreation, Gunicorn starts without exhausting RAM, SQLite handles concurrent writes, embedding files are decoupled from the Docker image.

**Addresses:** FEATURES.md — health check endpoint (document it is available), stable deployment for curator onboarding.

**Avoids:** Pitfalls 2 (Gunicorn × BioBERT memory), 3 (SQLite without WAL), 4 (embeddings baked into image), 8 (database lost on container restart).

**Key tasks:**
- Add `PRAGMA journal_mode=WAL` and `busy_timeout=10000` to `Database.get_connection()`
- Add `--preload-app`, extend `--start-period=120s` in Gunicorn/Docker config
- Move `DATABASE_PATH` default to `/app/data/ke_wp_mapping.db`, add Docker volume mount
- Add `data/*.npy` and `data/*.json` to `.dockerignore`, mount as Docker volume

### Phase 2: Data Model and Audit Trail

**Rationale:** Columns added now are retroactively available to all future mappings. Columns not added before curation begins cannot be reconstructed. This phase must precede any curation that feeds publication figures.

**Delivers:** Complete provenance model: stable UUIDs for mappings, suggestion provenance fields, audit trail for admin actions, normalized `go_id` format.

**Addresses:** FEATURES.md — stable mapping IDs in UI and API, curator attribution, confidence visible on each mapping.

**Avoids:** Pitfalls 6 (unstable identifiers), 7 (ML score instability, non-reproducible curation), 13 (no audit trail undermines scientific reproducibility).

**Key tasks:**
- Add `mapping_uuid` (UUID4) column to both mapping tables
- Add `suggestion_score`, `suggestion_method`, `scoring_config_version`, `approved_by`, `approved_at` columns
- Normalize `go_id` to colon format (`GO:0006955`) on insert; add application-level check
- Add `schema_version` field to all existing export files (JSON, CSV, Parquet)
- Freeze export column names via explicit stable-name mapping dict in exporters
- Add `pyarrow` and `openpyxl` to `requirements.txt` unconditionally

### Phase 3: Stable Public REST API (v1 Blueprint)

**Rationale:** The REST API is the primary consumer interface for downstream bioinformatics workflows. It must be stable before any paper is submitted because the paper supplement will reference API URLs. Build JSON-only first, then add content negotiation.

**Delivers:** Versioned, publicly accessible REST API at `/api/v1/` with paginated and filterable collection endpoints for both KE-WP and KE-GO mappings, discovery endpoint, public GET access without OAuth.

**Addresses:** FEATURES.md — documented REST API, stable mapping IDs in API responses, filter and search (server-side), confidence visible in API, unique stable identifiers.

**Avoids:** Pitfalls 1 (unversioned API), 6 (unstable identifiers in API), 9 (rate limits with no Retry-After), 12 (GitHub OAuth excludes collaborators).

**Uses:** STACK.md — new `v1_api_bp` Flask Blueprint; marshmallow schemas for v1 response contracts; offset/limit pagination following ChEMBL's `page_meta` envelope.

**Key tasks:**
- Create `src/blueprints/v1_api.py` with `url_prefix="/api/v1"`, register in `app.py`
- Add `get_mappings_paginated(filters, limit, offset)` and `get_go_mappings_paginated()` to models
- Implement `GET /api/v1/` (discovery), `/mappings`, `/mappings/<id>`, `/go-mappings`, `/go-mappings/<id>`
- All GET endpoints: no `@login_required`; apply generous rate limits with `Retry-After` headers
- Add `schema_version: "1.0"` to every response envelope
- Add content negotiation (Accept: text/csv, text/turtle) to collection endpoints

### Phase 4: Curator UX and Curation Quality

**Rationale:** Curator efficiency directly determines database quality. Duplicate proposals, ambiguous feedback, and invisible rejection reasons cause curators to abandon the tool or submit redundant work. These UX fixes also unblock the coverage gap view and filter improvements on the explore page.

**Delivers:** Duplicate detection before submission, rejection reasons surfaced to curators, explore page with server-side filtering by AOP/KE/pathway/confidence, coverage gap view showing uncovered KEs.

**Addresses:** FEATURES.md — filter explore view by AOP/KE/pathway/confidence (P1), coverage gap view (P2), indication of which KEs have no mapping yet.

**Avoids:** Pitfall 5 (curator UX failures: ambiguous feedback, no duplicate guard).

**Key tasks:**
- Add duplicate check in `create_proposal()`: reject if approved mapping or pending proposal already exists for same (ke_id, wp_id) or (ke_id, go_id)
- Return proposal ID and "pending review" status in submission response (not just "Entry added")
- Make admin rejection reason field required (minimum 20 chars); display to curator in proposal history
- Add server-side filtering to explore endpoint: `?ke_id=`, `?wp_id=`, `?go_id=`, `?confidence_level=`, `?aop_id=`
- Add coverage gap view: count/list of KEs from `ke_metadata.json` with no approved mapping

### Phase 5: GMT Export and Dataset Publication

**Rationale:** GMT export is the single highest-value low-effort feature for downstream bioinformaticians — it enables direct use of this database in clusterProfiler/fgsea without any data wrangling. Dataset DOI registration is required for any journal submission. These two deliverables together make the database citeable and immediately useful.

**Delivers:** GMT file for KE-WP mappings (consumable by clusterProfiler, fgsea, GSEA directly), Zenodo DOI registration, versioned dataset release mechanism with changelog notes.

**Addresses:** FEATURES.md — GMT export KE-WP (P1 differentiator), stable dataset download with version stamps, dataset DOI/citation.

**Avoids:** Pitfall 10 (export format fragility breaks downstream pipelines — GMT format must have stable gene set names and stable term identifiers).

**Key tasks:**
- Implement GMT export endpoint: KE name as term, WikiPathways gene list from SPARQL as gene set
- Register dataset on Zenodo; update `/dataset/datacite` and `/dataset/citation` endpoints with live DOI
- Add `Last-Modified` header and version stamp to all export responses
- Link bulk downloads prominently from the API discovery endpoint

### Phase 6: API Documentation and Public Launch

**Rationale:** Documentation must come last — it locks in endpoint contracts and field names. Writing docs before routes are stable creates maintenance debt. Once docs are published, the stable API contract is publicly committed.

**Delivers:** OpenAPI/Swagger spec for all `/api/v1/` endpoints, human-readable API documentation page with R and Python consumer examples, public-facing documentation of rate limits and bulk download guidance.

**Addresses:** FEATURES.md — documented REST API (P1), OpenAPI/Swagger spec (P2).

**Avoids:** Pitfall 9 (research API consumers hit unexplained rate limits — docs must include rate limit values, Retry-After explanation, and `time.sleep()` examples).

**Uses:** STACK.md — `flask-restx>=1.3.0` or `flasgger>=0.9.7` for OpenAPI spec generation.

**Key tasks:**
- Add `flask-restx` or `flasgger` to requirements.txt and annotate v1 Blueprint endpoints
- Update existing `/documentation` page with API endpoint listing, response schema, consumer code examples
- Document rate limits, bulk download URLs, and GMT file usage for clusterProfiler/fgsea

---

### Phase Ordering Rationale

- Deployment hardening (Phase 1) comes first because all other work runs on this foundation; data loss is irreversible and blocks curator onboarding.
- Data model (Phase 2) comes before the API (Phase 3) because the API exposes whatever columns exist at build time; adding provenance columns after the API is published requires a breaking schema change.
- The REST API (Phase 3) comes before UX polish (Phase 4) because external bioinformatician access is gated on the API existing; curator UX improvements are valuable but do not block the external consumer use case.
- GMT export (Phase 5) comes after the API (Phase 3) because the stable approved mapping set the GMT is generated from is the same set exposed by the API; the two must be consistent.
- Documentation (Phase 6) comes last because it locks in contracts; only document what will not change.

### Research Flags

Phases needing deeper research during planning:
- **Phase 3 (REST API):** The content negotiation implementation and exact marshmallow schema design benefit from a short research spike reviewing the existing `api.py` endpoint implementations to ensure the new `v1_api_bp` does not accidentally duplicate SPARQL-backed endpoints in the public API surface.
- **Phase 5 (GMT Export):** The WikiPathways SPARQL gene list fetching for GMT generation needs a concrete spike to confirm gene list availability for all approved KE-WP mappings — the SPARQL endpoint is the external dependency most likely to rate-limit or change.

Phases with standard patterns (skip research):
- **Phase 1 (Deployment hardening):** All fixes are concretely specified in PITFALLS.md with exact code snippets. No research needed — just execute.
- **Phase 2 (Data model):** Schema additions are additive (new columns with defaults). SQLite ALTER TABLE for column additions is well-understood. No research needed.
- **Phase 6 (Documentation):** Flask-RESTX and flasgger are well-documented and widely used. Standard patterns apply.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing stack analysis based on direct codebase inspection. No guesswork — specific file/line references throughout. The "do not migrate" recommendation is grounded in cost-benefit, not preference. |
| Features | HIGH | Cross-referenced against WikiPathways, Reactome, ChEMBL, AOP-Wiki, MSigDB, BioKC, and 15+ published papers and API documentation sets. Feature prioritization reflects actual downstream consumer workflows (clusterProfiler, fgsea, httr2, pandas). |
| Architecture | HIGH | ChEMBL, WikiPathways, Reactome, and AOP-Wiki REST API patterns are well-documented in official documentation and PLOS Computational Biology community guidelines. The dual-Blueprint split pattern is a direct, concrete recommendation with code examples. |
| Pitfalls | HIGH | 13 pitfalls identified with specific file/line references in the current codebase confirming each warning sign. Pitfalls are not theoretical — they are already present in the code and have concrete fixes. |

**Overall confidence:** HIGH

### Gaps to Address

- **Zenodo DOI registration process:** The research identifies that a DOI is needed and that `/dataset/datacite` exists, but the actual Zenodo registration requires interaction with an external service and institutional decisions about versioning cadence. This needs a person to complete, not a code change.
- **Curator attribution schema check:** FEATURES.md flags that `mappings` and `ke_go_mappings` tables must store `curator_github` at approval time. This needs verification against the current `src/blueprints/admin.py` approval flow — the schema addition may already be present or may need to be added in Phase 2.
- **AOP filter via SPARQL join:** The explore filter by `aop_id` requires joining approved mappings to AOP-Wiki SPARQL data. The SPARQL-based join adds latency and external dependency to a filtering operation. During Phase 4 planning, decide whether AOP membership should be pre-computed into the database (preferred) or fetched via SPARQL per request.
- **Pickle-based embedding security:** PITFALLS.md #11 identifies `allow_pickle=True` as a security and portability risk. Switching to `.npz` format requires rewriting all precomputation scripts. This is a correctness and security fix that must be planned into the Phase 1 scope even though it involves multiple script files.

---

## Sources

### Primary (HIGH confidence)

- ChEMBL Data Web Services documentation — pagination model, filtering conventions, API structure
- WikiPathways 2024 paper (NAR) + JSON API + rWikiPathways Bioconductor — bulk download patterns, GMT format, R client integration
- Reactome Content Service + OpenAPI — content negotiation, versioning, response envelope
- AOP-Wiki API (VHP4Safety) — AOP/KE/KER REST API structure
- "Eleven quick tips to build a usable REST API for life sciences" — Tarkowska et al., PLOS Computational Biology 2018 — community standard reference
- httr2 pagination helpers documentation — `iterate_with_offset()`, `iterate_with_next_url()`
- Existing codebase (`src/`, `Dockerfile`, `docker-compose.yml`, `CONCERNS.md`, `scoring_config.yaml`) — direct inspection with file/line references

### Secondary (MEDIUM confidence)

- "Ten quick tips for biocuration" (PMC) — curation UX and workflow patterns
- BioKC collaborative curation platform (PMC) — curator workflow patterns
- "A curated gene and biological system annotation of AOPs" (Nature Scientific Data) — AOP database provenance requirements
- GOATOOLS Python library (Nature Scientific Reports) — GO term analysis workflow expectations
- Zenodo FAIR data deposition guide — DOI registration and versioning

### Tertiary (LOW confidence)

- "AOP-networkFinder" (Bioinformatics Advances 2025) — emerging AOP network tooling; used for feature landscape only
- Various Flask blueprint versioning blog posts — implementation patterns, confirmed against official Flask docs

---

*Research completed: 2026-02-19*
*Ready for roadmap: yes*
