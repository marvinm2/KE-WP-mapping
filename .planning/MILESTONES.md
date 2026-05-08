# Milestones

## v1.4 Reactome Integration (Shipped: 2026-05-08)

**Phases completed:** 6 phases, 27 plans, 32 tasks
**Timeline:** 2026-04-03 → 2026-05-08 (35 days)
**Files changed:** 57 files, +11,010 / -93
**Commits:** 77 conventional (23–28 prefixes) + post-deploy CSS fix
**Requirements:** 18/18 satisfied (RDATA-01..05, RSUG-01..03, RCUR-01..04, REXP-01..04, RVIEW-01, KEGENE-01)

**Delivered:** Curators can now build, approve, export, and inspect KE→Reactome pathway mappings with full provenance — alongside the pre-existing KE-WP and KE-GO workflows. The milestone wires Reactome end-to-end: from precomputed BioBERT embeddings of ~1,954 Homo sapiens pathways, through a hybrid embedding-plus-gene-overlap suggestion engine, into a curator submit-and-approve flow with duplicate detection, then out to a versioned public REST API, GMT/RDF exports for downstream tools, and an inline DiagramJS pathway viewer with CDN-failure fallback. A late-discovered HGNC-accession-vs-symbol bug in the shared SPARQL helper (Phase 28) was rewritten to return persistent `{ncbi, hgnc, symbol}` triples, restoring non-empty gene-overlap signals across the WP, GO, and Reactome suggestion services in one stroke.

**Key accomplishments:**

- **Phase 23 (Data infrastructure):** Precompute pipeline producing 1,954 Homo sapiens pathways across 5 data files — pathway metadata JSON, HGNC gene annotations JSON, dual BioBERT name+description NPZ embeddings (768-dim, L2-normalised), filtered stable-ID list. Disease-branch descendants excluded via two-pass dbId-to-stId resolution; pathways outside 3–500 gene-count band excluded; stable IDs version-stripped.
- **Phase 24 (Suggestion engine):** `ReactomeSuggestionService` hybrid scorer (BioBERT similarity + gene overlap, 60/40 weight, 0.05 multi-evidence bonus) wired into `ServiceContainer` as a lazy property; `ke_reactome_mappings` + `ke_reactome_proposals` SQLite tables with idempotent migration; `ReactomeSuggestionConfig` dataclass and dedicated `reactome_suggestion:` block in `scoring_config.yaml`.
- **Phase 25 (Curator + admin workflow):** Third tab on the mapper page (Suggested + Search sub-tabs, WP-style 3-button confidence, CSRF-protected submit), `/submit_reactome_mapping` + `/check_reactome_entry` + `/search_reactome` + `/suggest_reactome/<ke_id>` API routes, `/admin/reactome-proposals` queue + approve/reject endpoints with single-INSERT carry-fields and rollback path, partial-unique pending index for race-safe duplicate detection. Three review blockers landed and grep-verified (C-1 stored XSS, H-1 non-transactional approve, H-2 duplicate-pending race).
- **Phase 26 (Public API + exports):** Versioned `GET /api/v1/reactome-mappings[/<uuid>]` (paginated, JSON+CSV, filters by KE/pathway/AOP/confidence), `/exports/gmt/ke-reactome[-centric]` (clusterProfiler/fgsea-compatible), `/exports/rdf/ke-reactome` (Turtle with full provenance triples + typed literals), Reactome tab + DataTable in `/explore`, OpenAPI schema documented. RDF empty-mappings 503 guard added inline (Reactome only).
- **Phase 27 (Pathway viewer):** `ReactomeDiagramEmbed` JS utility with lazy CDN script injection, three-layer failure detection, single-instance Diagram reuse, per-gene `flagItems` loop, PathwayBrowser fallback card. RVIEW-01 sign-off post-deploy confirmed inline render + CDN-failure fallback in browser; gene flagItems visual highlight accepted as structural-only per Plan 27-CONTEXT.
- **Phase 28 (Persistent-ID SPARQL helper):** Rewrote `get_genes_from_ke()` to return strict `{ncbi, hgnc, symbol}` triples from a single non-federated AOP-Wiki SPARQL query. Pre-existing latent bug (since 2025-08-08) silently produced empty gene-overlap across WP, GO, and Reactome services; fixed in one shared helper. `/ke_genes/<ke_id>` adds a `genes_full` dict-list while preserving legacy `genes` list for Phase 27's `flagItems`. Cache cutover via in-query version comment — no DB migration.

**Tech debt carried forward:**

- **Phase 27 latent issues** (4 review warnings + 1 race): catch handler destroys mount on second-failure recovery (WR-01), `onDiagramLoaded` handler accumulation across pathway swaps (WR-02), async `loadDiagram` failures bypass error-card path (WR-03), sticky `_failed` flag scope mismatch (WR-04), `prefetchKeGenes` in-flight race leaving `flagItems` with empty gene list. None block first-time E2E flow.
- **Phase 25 sibling debt** (out of scope by phase boundary): GO/WP admin modal XSS sinks share the C-1 pattern; `ke_go_proposals` and `ke_wp_proposals` lack the H-2 partial-unique pending index; `REACTOME_PROPOSAL_CARRY_FIELDS` constant defined but never imported (carry-list hard-coded inline in `create_approved_mapping`).
- **Phase 26 sibling debt:** `download_ke_go_rdf` and `download_ke_wp_rdf` lack the empty-graph 503 guard added to the Reactome variant; plan 26-0X frontmatter uses REXP-XX IDs that drift from canonical REQUIREMENTS.md (functional coverage complete, only doc noise).
- **Project-wide baseline:** Pre-existing `test_login_redirect` and `test_guest_login_page_renders` failures (likely Phase 14 OAuth route drift); `/dataset/{metadata,versions,citation,datacite}` 500 because `metadata_manager` is unconfigured (Zenodo/DataCite creds absent); dead `/confidence_assessment` route renders missing template; coverage at 42.18% vs 45% threshold.
- **RVIEW-01 #2 visual highlight:** structural-only acceptance carried — call shape verified, but visual gene highlight on the diagram canvas not observed. Acceptable per the original phase plan; worth revisiting if a future phase wants the highlight to actually render (would require investigating HGNC↔diagram-entity mapping or switching to NCBI-ID-based flagging).

**Archive:** `.planning/milestones/v1.4-ROADMAP.md`, `.planning/milestones/v1.4-REQUIREMENTS.md`, `.planning/milestones/v1.4-MILESTONE-AUDIT.md`

---

## v1.3 GO Assessment Quality (Shipped: 2026-03-11)

**Phases completed:** 6 phases, 12 plans
**Timeline:** 2026-03-08 → 2026-03-11 (4 days)
**Files changed:** 27 files, +2,597 / -574
**Commits:** 27

**Delivered:** GO mapping quality improvements — configurable KE description toggle with dual embeddings, directionality detection with scoring boost and export integration, structured three-dimension assessment replacing single confidence dropdown, GO Molecular Function suggestions alongside Biological Process, and gap closure for namespace propagation and bulk export fields.

**Key accomplishments:**

- KE description toggle: dual embedding sets (title-only + with-description), global config toggle, per-KE overrides with admin coverage audit page
- Directionality detection: prefix-based GO term direction detection, KE title direction regex, scoring boost for aligned direction, badges on suggestion cards, direction tags in GMT/RDF/API exports
- Three-dimension assessment: Connection/Specificity/Evidence rating with configurable weights, weighted average confidence computation, live preview, dimension scores stored and exposed in API
- GO Molecular Function: MF precompute pipeline, combined BP/MF display with namespace badges, aspect filter, independent MF scoring thresholds
- Gap closure: go_namespace propagation through submit → proposal → approval → mapping chain (Phase 21); get_all_mappings() SELECT updated with go_direction, go_namespace, suggestion_score (Phase 22)

**Tech debt carried forward:**

- Dual KE embedding NPZ files not yet generated (precompute script must be run; fallback in place)
- MF precomputed data files not yet generated (run scripts with --namespace mf; BP-only degradation in place)
- IC weight calibration (default 0.15) needs domain expert review session (carried from v1.2)
- ORCID/LS Login/SURFconext need human E2E testing with real OAuth credentials (carried from v1.2)
- Nyquist validation missing for phases 17-21 (informational only)

**Archive:** `.planning/milestones/v1.3-ROADMAP.md`, `.planning/milestones/v1.3-REQUIREMENTS.md`

---

## v1.2 Curation Depth (Shipped: 2026-03-06)

**Phases completed:** 4 phases, 9 plans, 18 tasks
**Timeline:** 2026-03-04 → 2026-03-06 (2 days)
**Files changed:** 24 files, +1,318 / -153
**Commits:** 17

**Delivered:** Curation depth features — collapsed section summaries, full proposer provenance, KE-centric GMT exports, multi-provider OAuth (ORCID/LS Login/SURFconext), GO hierarchy integration with IC-based specificity ranking and redundancy filtering, and enriched public API with KE context and GO metadata fields.

**Key accomplishments:**

- Collapsed section summaries: KE/pathway/confidence context visible at a glance in workflow steps
- Full proposer provenance chain on WP and GO mappings with explore page display and API exposure
- KE-centric GMT export format with gene union across all approved mappings per KE (fgsea/clusterProfiler compatible)
- Multi-provider OAuth: ORCID, LS Login, SURFconext via authlib OIDC alongside GitHub; provider-prefixed identity system
- GO hierarchy integration: OBO parser producing 24,547 BP terms with IC scores; specificity boost and ancestor redundancy filtering in suggestion pipeline
- Enriched public API: connection_type, ke_aop_context, ke_bio_level, go_definition, go_ic, go_depth, proposed_by across JSON and CSV; full OpenAPI spec update

**Tech debt carried forward:**

- ORCID/LS Login/SURFconext need human E2E testing with real OAuth credentials
- IC weight calibration (default 0.15) needs domain expert review session
- Nyquist validation missing for all 4 phases (informational only)

**Archive:** `.planning/milestones/v1.2-ROADMAP.md`, `.planning/milestones/v1.2-REQUIREMENTS.md`

---

## v1.1 Visuals (Shipped: 2026-03-04)

**Phases completed:** 5 phases, 18 plans
**Timeline:** 2026-02-24 → 2026-03-04 (9 days)
**Files changed:** 25 files, +3,359 / -507
**Commits:** 29

**Delivered:** Visual overhaul and interactive graph features — VHP4Safety branding, WikiPathways embed viewer with gene highlighting, interactive AOP network graph with precomputed KER data, inline mapper graph with mapping-status borders, and gene set visualization with count badges and drill-down gene lists.

**Key accomplishments:**

- VHP4Safety-branded CSS token system: 45+ custom properties, 660+ inline styles migrated to CSS classes, semantic status colors separated from brand palette
- WikiPathways Toolforge iframe embed: explore table modal + inline mapping workflow embed with per-KE gene highlighting via URL parameters
- Interactive AOP network graph (Cytoscape.js): 468 AOPs, 3,205 KERs precomputed via SPARQL, dagre layout, type-colored nodes (MIE/KE/AO), KE selection redirects to mapper
- Inline AOP graph on mapper page: mapping-status color borders (green=mapped, gray=unmapped), tab-specific refresh, "Use this KE" one-click selection
- Gene set visualization: count badges via cytoscape-node-html-label plugin, scrollable gene lists with GeneCards links, WP/GO grouped drill-down in side panels

**Tech debt carried forward:**

- 78 hardcoded hex values in main.css utility classes (cosmetic, low priority)
- renderGeneGroups() duplicated in aop-graph.js and aop-graph-inline.js (should move to AOPGraphCore)
- Script load ordering in index.html fragile (100ms setTimeout guard for inline adapter init)
- CDN failure for cytoscape-node-html-label silently suppresses gene badges (console.warn only)

**Archive:** `.planning/milestones/v1.1-ROADMAP.md`, `.planning/milestones/v1.1-REQUIREMENTS.md`

---

## v1.0 MVP (Shipped: 2026-02-23)

**Phases completed:** 7 phases, 28 plans, 52 tasks
**Timeline:** 2026-02-19 → 2026-02-23 (5 days)
**Files changed:** 142 files, 36,227 insertions
**Test suite:** 70 passing tests

**Delivered:** Prototype-to-production hardening — deployment safety, full data provenance, versioned public REST API, curator UX improvements, GMT/RDF/Zenodo exports, interactive API docs, and KE-GO proposal workflow with admin approval.

**Key accomplishments:**

- Production-hardened deployment: SQLite WAL mode, Docker volume persistence, Gunicorn preload_app BioBERT memory sharing, pickle-free NPZ embeddings
- Complete data provenance: UUID stable IDs, curator attribution, approval timestamps, confidence levels, and suggestion scores across all KE-WP and KE-GO mappings
- Versioned public REST API at `/api/v1/` with JSON/CSV content negotiation, CORS, AOP/KE/pathway filters, pagination, and 100 req/hr rate limiting
- Curator UX: collapsible KE context panel, AJAX explore DataTable with AOP + confidence filters, coverage gaps view, public dataset metrics dashboard
- Downloadable exports (GMT for clusterProfiler/fgsea, RDF/Turtle) and Zenodo DOI registration for paper citation
- KE-GO proposal-first workflow: all GO submissions enter pending queue with admin approve/reject, provenance written at approval (closes CURAT-01)

**Tech debt carried forward:**

- Zenodo live DOI requires one-time publish with real ZENODO_API_TOKEN
- Docker cold-start BioBERT preload timing verified locally but not in prod container
- Test coverage at ~40% vs 80% threshold (pre-existing condition, untested suggestion modules)

**Archive:** `.planning/milestones/v1.0-ROADMAP.md`, `.planning/milestones/v1.0-REQUIREMENTS.md`

---
