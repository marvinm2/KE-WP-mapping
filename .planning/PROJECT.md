# KE-WP / KE-GO Mapping Tool

## What This Is

A production-ready web-based curation tool that lets toxicologists and AOP researchers select Key Events (KEs) from Adverse Outcome Pathways (AOPs) and semi-automatically build a curated database of KE→WikiPathways and KE→GO term mappings. BioBERT embeddings and multi-signal scoring suggest mappings; GO suggestions cover both Biological Process and Molecular Function terms, ranked by information content from the GO hierarchy with redundant ancestor terms filtered. Directionality detection auto-tags GO terms as positive/negative regulation with scoring boosts for directional alignment. Curators assess GO mappings on three quality dimensions (Connection, Specificity, Evidence) that compute a weighted confidence score. Curators approve via a proposal workflow with admin review; every approved mapping carries full provenance (proposer, curator, timestamp, confidence, BioBERT score, direction, namespace, dimension scores). The curated database is accessible via a versioned public REST API (with KE context, GO metadata, direction, namespace, and proposer fields) and downloadable in GMT/RDF formats including KE-centric GMT for fgsea/clusterProfiler. Authentication supports GitHub, ORCID, LS Login, and SURFconext via provider-prefixed identities. An interactive AOP network graph (Cytoscape.js) lets curators visually explore AOPs, select KEs by clicking graph nodes, and see gene-count badges showing mapped gene sets per KE.

## Core Value

Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.

## Requirements

### Validated

<!-- Shipped and confirmed in v1.0 -->

- ✓ Pre-loaded KE list (1561 Key Events from AOP-Wiki) — existing
- ✓ AI-powered KE→WikiPathways suggestion engine (BioBERT embeddings + gene + text + ontology signals) — existing
- ✓ AI-powered KE→GO Biological Process suggestion engine (gene annotation + embedding signals) — existing
- ✓ Human curation workflow: submit proposal → admin approve/reject — existing
- ✓ SQLite persistence for approved KE-WP and KE-GO mappings — existing
- ✓ GitHub OAuth authentication + guest access codes — existing
- ✓ Admin dashboard for proposal review — existing
- ✓ Basic explore page (browse approved mappings) — existing
- ✓ File exports: CSV, JSON, Parquet — existing
- ✓ SPARQL caching, rate limiting, CSRF protection — existing
- ✓ DEPLOY-01: SQLite WAL mode and connection pooling for concurrent curator access — v1.0
- ✓ DEPLOY-02: Pickle-free NPZ embeddings with pre-normalized vectors; dot product similarity — v1.0
- ✓ DEPLOY-03: Automated database backup mechanism (sqlite3 Online Backup API, 7-day retention) — v1.0
- ✓ DEPLOY-04: Embedding vectors normalized at precompute; dot product replaces cosine at query time — v1.0
- ✓ CURAT-01: Approved mappings record curator + timestamp provenance (KE-WP and KE-GO) — v1.0
- ✓ CURAT-02: Duplicate mapping detection prevents re-submitting same KE→pathway or KE→GO pair — v1.0
- ✓ CURAT-03: Confidence level (High/Medium/Low) stored with each approved mapping — v1.0
- ✓ API-01: Versioned `/api/v1/` blueprint, separate from internal endpoints — v1.0
- ✓ API-02: `GET /api/v1/mappings` — paginated, filterable by KE, AOP, pathway — v1.0
- ✓ API-03: `GET /api/v1/go-mappings` — paginated, filterable by KE and GO term — v1.0
- ✓ API-04: `Accept: text/csv` returns tabular CSV on collection endpoints — v1.0
- ✓ EXPLO-01: Explore page filterable by AOP — v1.0
- ✓ EXPLO-02: Explore page filterable by confidence level — v1.0
- ✓ EXPLO-03: Coverage gap view — unmapped KEs per AOP — v1.0
- ✓ EXPLO-04: Stable UUID mapping IDs in all API responses and exports — v1.0
- ✓ EXPLO-05: Dataset metrics dashboard (mapping counts, coverage statistics) — v1.0
- ✓ EXPLO-06: Filtered dataset export (filter then download matching subset) — v1.0
- ✓ KE-01: KE context panel in mapping workflow (description, AOP context, biolevel) — v1.0
- ✓ EXPRT-01: GMT export for KE-WP mappings (clusterProfiler/fgsea compatible) — v1.0
- ✓ EXPRT-02: GMT export for KE-GO mappings — v1.0
- ✓ EXPRT-03: RDF/Turtle export with full provenance — v1.0
- ✓ EXPRT-04: Zenodo DOI registration and versioned dataset publication — v1.0
- ✓ DOCS-01: Interactive OpenAPI/Swagger UI at `/api/docs` — v1.0
- ✓ DOCS-02: R (httr2) and Python (requests) copy-paste code examples — v1.0
- ✓ DOCS-03: Rate limit policy documented (100 req/hr, Retry-After, time.sleep() example) — v1.0
- ✓ BRAND-01: Consistent VHP4Safety palette via CSS tokens across all pages — v1.1
- ✓ BRAND-02: JS inline styles migrated to CSS class assignments — v1.1
- ✓ BRAND-03: Semantic status colors use dedicated `--color-status-*` tokens — v1.1
- ✓ BRAND-04: Z-index token system for overlay components — v1.1
- ✓ BRAND-05: Fix broken `styles.css` 404 on ke-details/pw-details pages — v1.1
- ✓ BRAND-06: VHP4Safety branded navigation and headers — v1.1
- ✓ WPVIEW-01: WikiPathways link in explore DataTable — v1.1
- ✓ WPVIEW-02: Toolforge iframe embed modal from explore table — v1.1
- ✓ WPVIEW-03: Inline WikiPathways embed in mapping workflow — v1.1
- ✓ WPVIEW-04: Gene highlighting in WikiPathways embed — v1.1
- ✓ AOPGR-01: Interactive AOP network graph for selected AOP — v1.1
- ✓ AOPGR-02: Pan, zoom, interact with AOP graph — v1.1
- ✓ AOPGR-03: KE node tap shows info before selection — v1.1
- ✓ AOPGR-04: KE graph selection populates mapping dropdown — v1.1
- ✓ AOPGR-05: KE nodes color-coded by type (MIE/KE/AO) — v1.1
- ✓ AOPGR-06: Directed KER edges showing biological flow — v1.1
- ✓ AOPGR-07: KER adjacency precomputed via SPARQL script — v1.1
- ✓ AOPGR-08: Navigation link to AOP Network page — v1.1
- ✓ INLGR-01: Inline AOP graph panel on mapper page — v1.1
- ✓ INLGR-02: Mapping-status color borders on KE nodes — v1.1
- ✓ INLGR-03: Tab-specific mapping-status borders — v1.1
- ✓ INLGR-04: KE node info panel with type badge, title, bio level — v1.1
- ✓ INLGR-05: API endpoint for mapped KE IDs — v1.1
- ✓ INLGR-06: "Use this KE" auto-selects KE in dropdown — v1.1
- ✓ INLGR-07: Shared graph core between standalone and inline — v1.1
- ✓ GVIZ-01: Per-KE gene counts API endpoint — v1.1
- ✓ GVIZ-02: Per-KE gene list API endpoint — v1.1
- ✓ GVIZ-03: Gene-count badge overlays via cytoscape-node-html-label — v1.1
- ✓ GVIZ-04: Standalone gene list with GeneCards links in side panel — v1.1
- ✓ GVIZ-05: Inline mapper gene list with GeneCards links — v1.1
- ✓ GVIZ-06: Legend item explaining gene count badge — v1.1
- ✓ GVIZ-07: Consistent gene badges on both graph pages — v1.1
- ✓ Collapsed sections summarize selected KE/pathway/confidence info — v1.2
- ✓ Proposer identity recorded on WP and GO mappings with explore page display — v1.2
- ✓ KE-centric GMT export format with gene union across mappings per KE — v1.2
- ✓ Multi-provider OAuth: ORCID, LS Login, SURFconext with provider-prefixed identity — v1.2
- ✓ GO hierarchy integration: OBO parsing, IC weighting, redundancy filtering, specificity boost — v1.2
- ✓ Extended API metadata: KE context, GO IC/depth/definition, proposer, connection type — v1.2
- ✓ OpenAPI spec updated with all v1.2 response fields — v1.2
- ✓ KE description toggle: dual embeddings (title-only + with-desc), global config, per-KE overrides — v1.3
- ✓ GO directionality detection: prefix-based direction tagging, scoring boost, badge display, export integration — v1.3
- ✓ Structured three-dimension assessment: Connection/Specificity/Evidence with configurable weighted average — v1.3
- ✓ GO Molecular Function suggestions: MF precompute pipeline, combined BP/MF tab with aspect filter — v1.3
- ✓ GO namespace propagation through full approval chain — v1.3
- ✓ Bulk export SELECT with go_direction, go_namespace, suggestion_score — v1.3
- ✓ RDATA-01: Reactome metadata precompute (1,954 Homo sapiens pathways, disease branch excluded) — v1.4
- ✓ RDATA-02: HGNC gene annotations per pathway from Reactome GMT — v1.4
- ✓ RDATA-03: BioBERT name+description NPZ embeddings (768-dim, L2-normalised) — v1.4
- ✓ RDATA-04: Pathway gene-count filtering (3–500) and Disease branch exclusion — v1.4
- ✓ RDATA-05: Stable IDs version-stripped — v1.4
- ✓ RSUG-01: BioBERT embedding-based KE→Reactome suggestions ranked by similarity — v1.4
- ✓ RSUG-02: Gene-overlap signal contributes to Reactome suggestion scoring — v1.4
- ✓ RSUG-03: Reactome scoring thresholds independently configurable in `scoring_config.yaml` — v1.4
- ✓ RCUR-01: Curator submits KE→Reactome proposal with confidence — v1.4
- ✓ RCUR-02: Admin approves/rejects Reactome proposals with full provenance (single-INSERT carry-fields) — v1.4
- ✓ RCUR-03: Duplicate detection prevents re-submitting same KE→Reactome pair (with race-safe partial-unique pending index) — v1.4
- ✓ RCUR-04: Reactome tab in mapping workflow alongside WP and GO — v1.4
- ✓ REXP-01: Separate Reactome GMT export (clusterProfiler/fgsea-compatible) — v1.4
- ✓ REXP-02: Reactome RDF/Turtle export with full provenance — v1.4
- ✓ REXP-03: `GET /api/v1/reactome-mappings` paginated public endpoint with filters and CSV — v1.4
- ✓ REXP-04: Reactome mappings in explore-page DataTable — v1.4
- ✓ RVIEW-01: Reactome DiagramJS pathway viewer embedded in mapping workflow with CDN-failure fallback — v1.4 (visual gene flagItems highlight accepted as structural-only per Plan 27-CONTEXT)
- ✓ KEGENE-01: `get_genes_from_ke()` returns strict `{ncbi, hgnc, symbol}` triples; `/ke_genes/<ke_id>` adds `genes_full` while preserving legacy `genes`; gene-overlap signals restored across WP/GO/Reactome — v1.4

### Active

<!-- v1.4 shipped 2026-05-08. Defining v1.5 scope is the next step (run /gsd:new-milestone). Carry-forward candidates below. -->

- [ ] (carryover) Phase 27 polish — fix WR-01..WR-04 latent edge cases in `ReactomeDiagramEmbed` (mount-destroy on catch, handler accumulation, async loadDiagram failures, sticky `_failed` flag scope)
- [ ] (carryover) GO/WP sibling cleanup — apply C-1 XSS fix pattern to `admin_go_proposals.html` + `admin_proposals.html`; add H-2 partial-unique pending index to `ke_go_proposals` + `ke_wp_proposals`; add empty-mappings 503 guard to `download_ke_go_rdf` + `download_ke_wp_rdf`
- [ ] (carryover) Resolve dead `/confidence_assessment` route (create template or remove route)
- [ ] (carryover) Decide `/dataset/*` future — provision Zenodo/DataCite creds or downgrade 500 → 503/disabled
- [ ] (carryover) Pre-existing `test_login_redirect` / `test_guest_login_page_renders` baseline failures (Phase 14 OAuth route drift)

### Out of Scope

- KE→Gene direct mappings — genes used internally as matching signal only
- Real-time AOP-Wiki sync — KE metadata is pre-loaded; live querying is a future concern
- User-contributed pathway databases beyond WikiPathways/GO — focus on established ontologies
- Mobile native app — web-first
- GO hierarchy visualization / term tree browser — deferred (GOHI-08)
- User account linking across OAuth providers — deferred (AUTH-08)
- KEGG Pathways integration — deferred to v2 (DATA-01)
- GraphQL API — REST is community standard for bioinformatics; GraphQL adds complexity
- Redis-backed rate limiting — in-memory sufficient for v1 curator team scale

## Context

**Shipped:** v1.4 Reactome Integration (2026-05-08) — 28 phases total (6 in v1.4), 94 plans, +11K LOC across v1.4
**Tech stack:** Python/Flask blueprints, SQLite, BioBERT (dmis-lab/biobert-base-cased-v1.2), pre-computed NPZ embeddings (~244MB across WP/GO/Reactome), authlib (OIDC), Cytoscape.js 3.33.1, cytoscape-dagre, cytoscape-node-html-label, Reactome DiagramJS (CDN), Gunicorn, Docker
**Database:** `ke_wp_mapping.db` (SQLite, WAL mode) — Docker volume mount `/app/data/ke_wp_mapping.db`; tables for KE-WP, KE-GO, KE-Reactome mappings + proposals + admin tables
**Auth:** GitHub OAuth + ORCID/LS Login/SURFconext OIDC (when configured); guest codes for workshop participants; provider-prefixed identity system
**Frontend:** VHP4Safety-branded CSS token system (45+ custom properties), Cytoscape.js AOP graph (standalone + inline), WikiPathways Toolforge iframe embed, Reactome DiagramJS inline embed with CDN-failure fallback, login modal with branded provider buttons
**Deployment:** Docker Swarm at tgx1/tgx2 (Strato), `https://molaop-builder.vhp4safety.nl`. Gluster volume `/mnt/gluster/docker/molaop-builder/data` mounts to `/app/data` (Reactome NPZ/JSON files uploaded out-of-band 2026-05-07; gitignored).

**Known tech debt after v1.4:**
- **Phase 27 latent issues** (4 review warnings + 1 race): WR-01 catch-handler destroys mount on second-failure recovery, WR-02 `onDiagramLoaded` handler accumulation, WR-03 async `loadDiagram` failures bypass error card, WR-04 sticky `_failed` flag scope, plus `prefetchKeGenes` in-flight race leaving `flagItems` with empty gene list.
- **GO/WP sibling debt** (out of v1.4 scope): GO/WP admin XSS sinks share Reactome C-1 pattern; GO/WP proposal tables lack H-2 partial-unique pending index; GO/WP RDF routes lack empty-mappings 503 guard.
- **RVIEW-01 #2 visual highlight** structural-only — call shape verified, but no visible highlight on diagram canvas. Likely HGNC↔diagram-entity mapping mismatch.
- **`REACTOME_PROPOSAL_CARRY_FIELDS`** constant defined but never imported (carry-list hard-coded inline in `create_approved_mapping`).
- **Plan 26 frontmatter REXP-XX ID drift** vs canonical REQUIREMENTS.md (cosmetic).
- **Pre-existing baseline failures** carry forward: `test_login_redirect`, `test_guest_login_page_renders`; `/dataset/{metadata,versions,citation,datacite}` 500 (`metadata_manager` unconfigured); `/confidence_assessment` 500 (dead route, missing template); coverage 42.18% vs 45% threshold.
- **Carryover from v1.3:** Zenodo live DOI requires one-time publish with real `ZENODO_API_TOKEN`; ORCID/LS Login/SURFconext need human E2E testing with real OAuth credentials; IC weight calibration (default 0.15) needs domain expert review.

## Constraints

- **Tech stack**: Python/Flask — no framework migration
- **Database**: SQLite for v1 — migration to PostgreSQL is a future concern
- **Embeddings**: Pre-computed BioBERT; regeneration requires `scripts/`
- **Auth**: GitHub OAuth for curators; guest codes for workshop participants
- **Deployment**: Docker/Gunicorn; minimum 4GB RAM for embedding service

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| BioBERT embeddings for semantic matching | Domain-specific biological text encoder outperforms general models | ✓ Good — <1s response after precompute |
| Multi-signal scoring (gene + embedding + text + ontology) | Combines complementary signals for higher precision | ✓ Good — 23x speedup with batch processing |
| Pre-curated KE list vs live SPARQL | Avoids latency and rate-limit issues with AOP-Wiki | ✓ Good — reliable, fast dropdowns |
| SQLite for v1 | Sufficient for curator team scale; simplifies deployment | ✓ Good — WAL mode handles concurrent writes |
| GitHub OAuth | Low-friction auth for scientific community | ✓ Good |
| Dual-blueprint split (api_bp internal, v1_api_bp public) | Isolates stable public API from internal endpoints | ✓ Good — CORS and rate limiting scoped correctly |
| WAL PRAGMAs on every connection (not once) | Idempotent; guarantees WAL mode across all connections | ✓ Good |
| NPZ format + pre-normalized vectors | Eliminates pickle risk; dot product = cosine after normalization | ✓ Good — safe and fast |
| Proposal-first for all submissions | Human validation is core value; no auto-approval | ✓ Good — both KE-WP and KE-GO now go through proposal queue |
| JOIN alias pattern (m.ke_id AS mapping_ke_id) | Prevents sqlite3.Row dict() NULL-clobbering on LEFT JOIN | ✓ Good — pattern applied consistently in all models |
| Batch SPARQL VALUES query for GMT export | Avoids N+1 HTTP calls to WikiPathways | ✓ Good |
| Static OpenAPI YAML + unpkg CDN Swagger UI | No code generation; spec stays authoritative | ✓ Good — pinned to 5.31.2 |
| GoProposalModel mirrors ProposalModel exactly | Rename/adapt, not new design | ✓ Good — consistent patterns, easy to maintain |
| DATABASE_PATH as @property (post-v1.0 fix) | os.getenv() evaluated at access time, after load_dotenv() | ✓ Fixed — d7ac982 |
| Cytoscape.js for AOP graph | Field standard for AOP networks; CDN-only, no build system | ✓ Good — 468 AOPs render smoothly |
| Toolforge iframe for WikiPathways | CDN-compatible, no React/rxjs dependency; clean embed | ✓ Good — embeddable, gene highlighting works |
| CSS token system (45+ custom properties) | Centralized theming, eliminates inline hex values | ✓ Good — 660+ inline styles migrated |
| Shared AOPGraphCore IIFE module | DRY graph rendering for standalone + inline pages | ✓ Good — single source of truth |
| SPARQL precompute for KER adjacency | Avoids live SPARQL calls; 3,205 KERs cached as JSON | ✓ Good — instant graph rendering |
| cytoscape-node-html-label for gene badges | HTML overlay on graph nodes without SVG manipulation | ✓ Good — clean badge rendering |
| Lazy gene data fetch per node tap | Avoids N API calls on graph render | ✓ Good — responsive UX |
| Provider-prefixed identity (github:, orcid:, ls:, surf:) | Avoids username collision across OAuth providers | ✓ Good — clean migration |
| authlib OIDC auto-discovery for multi-provider OAuth | Single registration pattern for all OIDC providers | ✓ Good — 4 providers via one codepath |
| go-basic.obo (not go.obo) for hierarchy parsing | Full go.obo breaks ancestor traversal with non-acyclic relationships | ✓ Good — clean DAG |
| IC boost as post-combine GO-specific step | Keeps combine_scored_items() generic across WP/GO | ✓ Good — separation of concerns |
| KE-centric GMT Field 1 as KE{N} only | Clean identifier for fgsea/clusterProfiler gene set names | ✓ Good — locked user decision |
| Flat KE context fields in API responses | Avoids nested sub-objects for simple metadata | ✓ Good — easy CSV mapping |
| Dual KE embedding sets (title-only + with-desc) | Runtime toggle without regenerating embeddings | ✓ Good — instant switching |
| Prefix-based GO direction detection | GO naming conventions are rigid; deterministic | ✓ Good — no NLP needed |
| Default KE title direction to "unspecified" | ~40-60% accuracy on KE titles; avoid false positives | ✓ Good — safe default |
| Separate INTEGER columns for assessment dimensions | Queryable and API-filterable (not JSON blob) | ✓ Good — clean schema |
| Extend GoSuggestionService (not separate MfService) | Single service with aspect-aware loading | ✓ Good — DRY, shared scoring logic |
| Per-KE description overrides in SQLite table | Admin toggling at runtime without config file edits | ✓ Good — flexible |
| GoNamespaceField marshmallow custom field | Single conversion point for BP/MF normalization | ✓ Good — clean API layer |
| Reactome data files gitignored, deployed out-of-band to gluster | NPZ + JSON ~16 MB; bloating repo and git history is wasteful when target is a Docker volume | ✓ Good — keeps repo lean; documented in CLAUDE.md and live-endpoint-tests.md |
| Two-pass dbId-to-stId for Reactome disease exclusion | Content Service `containedEvents` mixes int + dict entries; one-pass dropped 11 integer entries | ✓ Good — fully cured the disease-branch leak (1,964 → 1,954) |
| Hybrid Reactome scoring 60/40 (embedding/gene) with multi-evidence bonus | Mirrors GO/WP but tuned to short Reactome descriptions where name carries more signal | ✓ Good — 1,954 ranked candidates from KE 55, top hybrid 0.59 |
| `create_approved_mapping` single-INSERT carry-fields with rollback | Two-step INSERT-then-UPDATE produced NULL provenance windows under partial failure (H-1) | ✓ Good — atomic, with `delete_mapping` rollback path on `update_proposal_status` failure |
| Partial-unique index on `ke_reactome_proposals (ke_id, reactome_id) WHERE status='pending' AND mapping_id IS NULL` | App-level duplicate check + DB constraint = race-safe (H-2) | ✓ Good — `DUPLICATE_PENDING` sentinel + 409 mapping in API |
| Persistent IDs (`{ncbi, hgnc, symbol}`) in shared SPARQL helper | HGNC routinely renames genes (e.g. `C11orf95 → ZFTA`); persistent IDs don't drift | ✓ Good — single shared rewrite restored gene-overlap across WP, GO, Reactome services |
| Cache cutover via in-query version comment (`# ke-genes-query-v2`) | Changes `md5(query)` so old cache rows become unreachable; expires silently in TTL | ✓ Good — no DB migration needed |
| DiagramJS lazy CDN script injection with three-layer failure detection | Reactome bundle is heavy GWT; lazy load avoids paying cost when tab unused | ✓ Good — RVIEW-01 #1 + #3 confirmed in browser |
| Reactome viewer accepts structural-only flagItems | HGNC↔internal-entity mapping is opaque; visual highlight is best-effort | ⚠️ Revisit — accepted by Plan 27-CONTEXT but may want to investigate in a future phase |
| Scoped CSS reset on `#reactome-inline-embed-frame button` | Global `button` selector cascaded into DiagramJS native zoom/fit/fullscreen icons, blowing them up to magenta slabs | ✓ Good — post-deploy hotfix `09426fa`; concrete reminder that global selectors leak into third-party widgets |

## Current State

v1.4 Reactome Integration **shipped** 2026-05-08. Five milestones complete (v1.0 MVP, v1.1 Visuals, v1.2 Curation Depth, v1.3 GO Assessment Quality, v1.4 Reactome Integration). The tool now supports KE→WP, KE→GO (BP + MF), and KE→Reactome mapping, all with proposal→admin-approval workflows, full provenance, public REST API at `/api/v1/`, GMT + RDF/Turtle exports, and inline pathway viewers (WikiPathways via Toolforge iframe; Reactome via DiagramJS embed). The shared `get_genes_from_ke()` SPARQL helper now returns persistent `{ncbi, hgnc, symbol}` triples (Phase 28 fixed a pre-existing HGNC-accession-vs-symbol bug that had silently disabled gene-overlap scoring across all three suggestion services since 2025-08-08). All 18 v1.4 requirements satisfied; one (RVIEW-01 #2 visual gene highlight) accepted as structural-only per Plan 27-CONTEXT.

**Next:** Run `/gsd:new-milestone` to scope v1.5. Carry-forward candidates listed in Active above. Open question: is the next milestone curation-depth-driven (e.g. KEGG, HPO, AOP-network curation tools), polish-and-cleanup (sibling debt sweep across GO/WP), or new-direction (Zenodo live DOI, OAuth provider testing, external integrations)?

---
*Last updated: 2026-05-08 after v1.4 milestone completion*
