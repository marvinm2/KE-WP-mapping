# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.1 — Visuals

**Shipped:** 2026-03-04
**Phases:** 5 | **Plans:** 18 | **Commits:** 29

### What Was Built
- VHP4Safety-branded CSS token system replacing 660+ inline styles across templates and JS
- WikiPathways Toolforge iframe embed (explore modal + inline mapping workflow + gene highlighting)
- Interactive AOP network graph (Cytoscape.js) with 468 AOPs, type-colored nodes, dagre layout
- Inline AOP graph on mapper page with mapping-status borders and one-click KE selection
- Gene set visualization with count badges and drill-down gene lists with GeneCards links

### What Worked
- Visual verification checkpoints (08-05, 09-03, 10-04, 11-03, 12-03) caught issues early — user approval at each phase prevented late rework
- Shared AOPGraphCore IIFE pattern allowed standalone and inline graphs to share rendering logic without duplication
- SPARQL precompute approach (ker_adjacency.json) eliminated live query latency and rate-limit concerns
- CDN-only architecture maintained throughout — no build system needed for Cytoscape.js, dagre, or node-html-label

### What Was Inefficient
- Phase 8 took 102 minutes (5 plans) — the 660 inline style migration was mechanical but time-consuming; could have been partially automated
- Phases 11 and 12 were added mid-milestone (originally v1.1 was Phases 8-10 only) — scope expanded after seeing the graph's potential
- ROADMAP.md accumulated stale progress table entries (Phase 8/10 had duplicate "Complete" columns)

### Patterns Established
- Visual verification checkpoint as final plan in every UI phase (human approval gate)
- AOPGraphCore shared module pattern for multi-page Cytoscape instances
- Lazy data fetch per node tap (genes, biolevels) instead of bulk preload
- CSS custom property tokens for all colors, z-indices, and layout values

### Key Lessons
1. UI phases benefit from visual checkpoints — catching styling issues in-browser is faster than describing them in text
2. Shared JS modules (IIFE pattern) scale well for multi-page features without a build system
3. Mid-milestone scope expansion works if requirements and phases are clearly defined before execution

### Cost Observations
- Model mix: ~80% opus, ~20% sonnet (verification checkpoints used sonnet)
- Sessions: ~8 sessions over 9 days
- Notable: Phases 9-12 averaged ~5 min/plan vs Phase 8's ~20 min/plan — later phases reused established patterns

---

## Milestone: v1.2 — Curation Depth

**Shipped:** 2026-03-06
**Phases:** 4 | **Plans:** 9 | **Commits:** 17

### What Was Built
- Collapsed section summaries showing KE/pathway/confidence context in workflow steps
- Full proposer provenance chain on WP and GO mappings (DB + API + UI)
- KE-centric GMT export format with gene union across all approved mappings per KE
- Multi-provider OAuth (ORCID, LS Login, SURFconext) with provider-prefixed identity system
- GO hierarchy integration: OBO parser, IC scores, specificity boost, ancestor redundancy filter
- Extended public API with KE context metadata, GO hierarchy data, and proposer identity

### What Worked
- Milestone audit before completion caught no gaps — 32/32 requirements cleanly satisfied
- Provider-prefixed identity pattern (github:, orcid:, ls:, surf:) made multi-auth clean with no collision risk
- IC boost as GO-specific post-processing (not inside combine_scored_items) preserved scoring architecture cleanly
- Precompute pattern extended naturally from BioBERT/KER to GO hierarchy (data/go_hierarchy.json)

### What Was Inefficient
- Phase 13 Plan 01 took 25 min (UI step summaries) — jQuery DOM manipulation required careful testing of toggle/reset edge cases
- Nyquist validation missing for all 4 phases (informational, not blocking)
- OAuth providers cannot be E2E tested without real credentials — tech debt carried forward

### Patterns Established
- Provider-prefixed identity: all usernames stored as provider:name across DB, API, and UI
- KE-centric GMT: union genes across mappings per KE with order-preserving deduplication
- Post-combine scoring adjustments: apply boost then filter, before sort+limit
- Hierarchy data loaded once at startup, converted to optimized structures (sets for ancestors)

### Key Lessons
1. Precompute scripts need User-Agent headers for academic data sources — OBO Foundry, UniProt, etc. block bare urllib
2. Explicit SELECT column lists (not SELECT *) require manual maintenance when adding columns — caught twice (proposed_by, go_namespace)
3. Multi-provider OAuth is straightforward with authlib OIDC auto-discovery — single registration pattern for all providers
4. IC weight calibration needs domain expert review, not just default tuning

### Cost Observations
- Model mix: ~90% opus, ~10% sonnet
- Sessions: ~4 sessions over 2 days
- Notable: Average plan execution ~7 min; fastest plan was 1 min (16-02 OpenAPI spec update)

---

## Milestone: v1.3 — GO Assessment Quality

**Shipped:** 2026-03-11
**Phases:** 6 | **Plans:** 12 | **Commits:** 27

### What Was Built
- KE description toggle with dual embedding sets (title-only + with-description), global config, per-KE admin overrides
- GO directionality detection via prefix matching, scoring boost for aligned direction, badge display on suggestion cards, direction tags in GMT/RDF/API exports
- Three-dimension assessment (Connection/Specificity/Evidence) with configurable weights replacing single confidence dropdown, live preview, dimension scores in DB and API
- GO Molecular Function suggestions alongside Biological Process with namespace badges, aspect filter, independent MF scoring thresholds
- Gap closure: go_namespace propagation through full approval chain (Phase 21) and bulk export SELECT fix (Phase 22)

### What Worked
- Milestone audit (before completion) caught 2 real gaps (namespace propagation, stale SELECT) that became Phases 21-22 — validated the audit workflow
- _NamespaceData namedtuple pattern cleanly bundled per-namespace data for scoring methods
- GoNamespaceField marshmallow custom field centralized BP/MF normalization at a single point
- Precompute pattern extended again (direction metadata, MF embeddings) without architectural changes

### What Was Inefficient
- Phases 21 and 22 were gap closure phases added after audit — could have been caught earlier if audit ran before Phase 20 completion
- ROADMAP.md progress table had inconsistent column formatting for v1.3 phases (missing milestone column)
- 12 SUMMARY.md files lack `one_liner` field — summary-extract returns null; accomplishments had to be manually composed

### Patterns Established
- Gap closure phases (decimal-like 21, 22) for audit-discovered issues — keeps main phases clean
- GoNamespaceField pattern for marshmallow custom type normalization (reusable for other enum-like fields)
- Per-namespace data bundling (_NamespaceData namedtuple) for multi-variant scoring services
- Direction detection: prefix matching for GO terms, compiled regex for KE titles, "unspecified" default

### Key Lessons
1. Run milestone audit early (after all original phases, before declaring complete) — audit caught 2 gaps that needed 2 additional phases
2. Explicit SELECT column lists continue to bite — get_all_mappings() missed go_direction, go_namespace, suggestion_score (3rd time this pattern caused issues)
3. SUMMARY.md files should include `one_liner` field for automated milestone accomplishment extraction
4. MF precomputed files and dual KE embedding files need to actually be generated — code supports graceful degradation but the data isn't there yet

### Cost Observations
- Model mix: ~85% opus, ~15% sonnet
- Sessions: ~6 sessions over 4 days
- Notable: Gap closure phases (21, 22) averaged ~10 min each — small, focused scope

---

## Milestone: v1.4 — Reactome Integration

**Shipped:** 2026-05-08
**Phases:** 6 | **Plans:** 27 | **Tasks:** 32 | **Commits:** 77 conventional + post-deploy CSS hotfix
**Timeline:** 2026-04-03 → 2026-05-08 (35 days)

### What Was Built
- Reactome precompute pipeline producing 1,954 Homo sapiens pathways across 5 data files (metadata JSON, gene annotations JSON, dual BioBERT NPZ embeddings, filtered stable-ID list); disease branch excluded via two-pass dbId-to-stId resolution
- `ReactomeSuggestionService` hybrid scorer (60/40 embedding/gene + multi-evidence bonus) wired through `ServiceContainer` lazy property; new SQLite tables with idempotent migration
- Curator workflow: third tab on mapper page, `/submit_reactome_mapping` + `/check_reactome_entry` + `/search_reactome` + `/suggest_reactome/<ke_id>` API routes; admin queue + approve/reject with single-INSERT carry-fields; race-safe partial-unique pending index
- Public surface: versioned `/api/v1/reactome-mappings` (paginated, JSON+CSV, filters), GMT exports (per-mapping + KE-centric), RDF/Turtle export with full provenance, Reactome tab + DataTable in `/explore`, OpenAPI documented
- DiagramJS inline pathway viewer with lazy CDN load, three-layer failure detection, PathwayBrowser fallback card
- Phase 28: rewrote `get_genes_from_ke()` to return persistent `{ncbi, hgnc, symbol}` triples — fixed pre-existing HGNC-accession-vs-symbol bug from 2025-08-08 that had silently disabled gene-overlap scoring across WP/GO/Reactome services

### What Worked
- **Milestone-audit-then-deploy-then-re-audit cadence.** First audit returned `tech_debt` (RVIEW-01 partial, deploy-deferred). After deploy + browser sign-off, second audit returned `passed`. Workflow naturally separated "code complete" from "behaviorally verified".
- **Pre-existing latent-bug discovery during Phase 27 work.** Phase 27 verification revealed empty `flagItems` highlights, which surfaced the underlying SPARQL HGNC-accession-vs-symbol defect — became Phase 28 (a single shared helper rewrite that fixed three suggestion services in one stroke).
- **Pattern reuse held strong.** Reactome models, schemas, admin templates, API serializers, and exporters all mirror the GO/WP equivalents with documented diffs (no IC/direction/namespace bells). Plan 26-01's `KEWP→VOCAB` rename prep cleanly unblocked the Reactome RDF generator.
- **`scoring_config.yaml` extension to a 3rd ontology** required no architectural change — `ReactomeSuggestionConfig` dataclass + dedicated YAML section dropped in cleanly.
- **DB-level race-safety on pending duplicates** (H-2 fix): partial-unique index + `DUPLICATE_PENDING` sentinel + `IntegrityError` 409 path closed an entire class of concurrent-submit bugs.
- **Live-endpoint smoke suite** (`.claude/live-endpoint-tests.sh`): derived from blueprint route table, found exact 5 pre-existing config issues + the real Reactome-data-volume gap on first run; differentiated v1.4-introduced regressions from baseline noise.

### What Was Inefficient
- **Reactome precomputed data files are gitignored** (correct call — ~16 MB) but the deploy procedure docs didn't capture the `scp ... tgx1:/mnt/gluster/docker/molaop-builder/data/` step. First production smoke after deploy showed `total_suggestions=0` for every KE because the data volume was empty. Fixed in this session; should be folded into the standing deploy runbook.
- **DiagramJS native button styling cascade.** Global `button { background: magenta; padding: 10px 20px }` rule cascaded into DiagramJS's injected zoom/fit/fullscreen icon buttons inside the embed, blowing them up to magenta slabs. Required a post-deploy CSS scoped reset (`#reactome-inline-embed-frame button`). Reminder: third-party widgets that inject DOM are exposed to global selectors; future embeds need scoped resets pre-emptively.
- **Plan 26 frontmatter REXP-XX ID drift** vs canonical REQUIREMENTS.md — plans used REXP-01 for "API model" while canonical REXP-01 is "GMT export". Cosmetic, but the audit traceability had to manually reconcile. SUMMARY frontmatter `requirements_completed` field was blank on several plans (26-07, 26-08, 28A, 28C, 28D), forcing the audit to fall back to VERIFICATION.md content.
- **MILESTONES.md auto-extraction noise.** `gsd-tools milestone complete` extracts SUMMARY one-liners verbatim, including "1. [Rule 1 - Bug] ..." headers and "Auto tasks 1 + 2 complete" stubs. Required manual rewrite of the v1.4 entry to match prior milestones' tone.
- **Phase 27 `human_needed` status** sat for ~1 day after code-complete because the deploy hadn't happened. The phase verification correctly reflected its state, but the workflow ran into ambiguity: "human_needed" wasn't in the audit status determination matrix, so the first audit had to invent a `partial` classification.

### Patterns Established
- **Persistent-ID over symbol-string in shared SPARQL helpers.** HGNC routinely renames genes (e.g. `C11orf95 → ZFTA`). Persistent IDs (NCBI Gene + HGNC accession) don't drift; symbol becomes a denormalized display field. New convention for any future cross-database gene helpers.
- **Cache cutover via in-query version comment.** `# ke-genes-query-v2 — ...` inside the f-string changes `md5(query)` so old cached responses become unreachable on the new key — automatic, no DB migration. Cleaner than schema bumps for SPARQL response caches.
- **Single-INSERT carry-fields with rollback** (H-1). Prefer atomic INSERT-with-all-provenance + `delete_mapping` rollback path on follow-up failure over INSERT-then-UPDATE which can leave NULL provenance windows. Generalize to other approval flows.
- **Partial-unique pending index on proposal tables** (H-2). `WHERE status='pending' AND mapping_id IS NULL` lets approvals coexist without violating the constraint, while blocking concurrent-pending duplicates at the DB level. Should backport to `ke_go_proposals` and `ke_wp_proposals`.
- **Scoped CSS reset for third-party widget mounts.** Any embed that injects DOM (DiagramJS, future Reactome viewer descendants) needs `#mount-id button { /* reset */ }` to escape the global app button rules. Pre-emptive pattern, not reactive.
- **Live-endpoint smoke suite as deploy gate.** Blueprint-route-derived bash + curl + python tests catch deploy gaps that pytest doesn't (volume mounts, OAuth provider config, dead routes, template typos). Should be standard for every Flask deploy.

### Key Lessons
1. **Latent bugs surface when downstream features become observable.** The 2025-08-08 SPARQL HGNC bug had silently produced empty gene-overlap for ~9 months because no UI rendered the result. Phase 27's `flagItems()` was the first user-visible consequence. Lesson: when a planned feature unexpectedly produces an empty result, suspect upstream signal sources before tuning the feature.
2. **Browser-only success criteria need to be declared from the start.** Plan 27-04 declared three RVIEW-01 SCs as "manual-only deploy verification" — the milestone audit handled this gracefully via `human_needed` status, but it required a dedicated re-audit after deploy. Future phases with browser-only gates should produce a deploy-time UAT script in the same plan.
3. **Gitignored data + deployed-out-of-band needs runbook step.** The data-volume mount is the right architectural choice (keeps repo lean, decouples deploy timing), but it implies a manual `scp` step that has to be in the deploy procedure. Otherwise the first prod smoke is misleading (suggestions look broken).
4. **Pre-existing baseline issues should be triaged at first audit.** The 5 unrelated 500/dead-route findings (`/dataset/*`, `/confidence_assessment`) had been latent for a long time but only surfaced when the live smoke suite ran. Worth running the smoke against `main` once a milestone, independent of any deploy.
5. **`milestone complete` CLI is a starting point, not a finished entry.** The auto-extracted accomplishments need a humanizing pass before MILESTONES.md is shippable. Consider adding a SUMMARY.md `one_liner` field convention enforced at plan-summary time.

### Cost Observations
- Model mix: predominantly opus 4.6/4.7
- Sessions: ~12 sessions over 35 calendar days
- Notable: Phase 25 (proposal workflow) was the biggest single phase (6 plans, ~80 tests) — review-fix loop landed 3 blockers (C-1 XSS, H-1 non-transactional approve, H-2 race) before verification passed. Phase 28 (SPARQL helper rewrite) was the smallest meaningful phase — 4 surgical plans, ~120 lines net change, fixed an entire class of bugs.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Commits | Phases | Key Change |
|-----------|---------|--------|------------|
| v1.0 MVP | ~50 | 7 | Established proposal workflow, API, exports |
| v1.1 Visuals | 29 | 5 | Added visual verification checkpoints, shared JS modules |
| v1.2 Curation Depth | 17 | 4 | Multi-provider auth, GO hierarchy, provenance chain |
| v1.3 GO Assessment Quality | 27 | 6 | Directionality, 3-dim assessment, MF terms, audit-driven gap closure |
| v1.4 Reactome Integration | 77 | 6 | Third ontology, DiagramJS embed, persistent-ID SPARQL helper, deploy-then-re-audit cadence |

### Cumulative Quality

| Milestone | Plans | Coverage | Key Addition |
|-----------|-------|----------|-------------|
| v1.0 | 28 | ~40% | 70 tests, full API + export suite |
| v1.1 | 18 | ~40% | CSS tokens, Cytoscape graph, WikiPathways embed |
| v1.2 | 9 | ~40% | GO hierarchy, multi-provider OAuth, KE-centric GMT |
| v1.3 | 12 | ~40% | Directionality, 3-dim assessment, MF suggestions |
| v1.4 | 27 | 42.18% | Reactome ontology end-to-end, DiagramJS embed, persistent-ID helper, +49 Reactome-specific tests |

### Top Lessons (Verified Across Milestones)

1. Precompute over live queries — BioBERT embeddings (v1.0), KER adjacency (v1.1), GO hierarchy (v1.2), direction metadata + MF embeddings (v1.3), Reactome NPZ + JSON (v1.4) all benefit from offline computation
2. Proposal-first workflow extends naturally — KE-WP (v1.0), KE-GO (v1.0), visual features (v1.1), MF terms (v1.3), KE-Reactome (v1.4) all follow the same review pattern; race-safety hardens (v1.4 H-2 partial-unique pending index should backport)
3. CDN-only architecture holds — no build system needed through 28 phases and 94 plans; new third-party widgets (Reactome DiagramJS) integrate cleanly via lazy script injection + CSS scoped resets
4. Explicit SELECT column lists require vigilance when adding DB columns — caught in v1.0 (proposed_by), v1.2 (go_namespace), v1.3 (go_direction, go_namespace, suggestion_score); v1.4 added carry-fields for Reactome via single-INSERT to avoid this class entirely
5. Milestone audit before completion catches real gaps — v1.3 audit found 2 gaps (became Phases 21-22); v1.4 audit found RVIEW-01 deploy-deferred + Reactome data-volume mount gap (closed before declaring complete)
6. **(new from v1.4)** Latent bugs surface when downstream features become observable — the 2025-08-08 SPARQL HGNC defect was invisible until Phase 27's `flagItems()` exposed an empty result; suspect upstream signal sources before tuning new features
7. **(new from v1.4)** Browser-only / deploy-only success criteria need explicit deploy-time UAT scripts captured in the originating plan — the audit workflow can route around them, but it requires a dedicated re-audit after deploy
