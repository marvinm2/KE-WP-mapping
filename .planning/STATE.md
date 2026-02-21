# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.
**Current focus:** Phase 5 — Enhanced Data Export (In Progress)

## Current Position

Phase: 5 of 6 (Exports and Dataset Publication) — IN PROGRESS
Plan: 1 of 3 in current phase (05-01 complete — GMT and RDF exporter modules)
Status: Phase 5 Plan 1 Complete (standalone GMT + rdflib Turtle exporters)
Last activity: 2026-02-21 — Completed 05-01 (gmt_exporter.py + rdf_exporter.py rewritten)

Progress: [████████░░] 83% (Phase 5 started — 1/3 plans done in Phase 5)

## Performance Metrics

**Velocity:**
- Total plans completed: 15
- Average duration: 6.3 min
- Total execution time: ~1.6 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-deployment-hardening | 4 | 20 min | 5 min |
| 02-data-model-and-audit-trail | 4 (complete) | 26 min | 6.5 min |
| 03-stable-public-rest-api | 4 (complete) | 30 min | 7.5 min |
| 04-curator-ux-and-explore | 5 (complete) | 36 min | 7.2 min |

**Recent Trend:**
- Last 5 plans: 04-04 (4 min), 04-01 (4 min), 04-03 (9 min), 04-02 (15 min), 04-05 (13 min)
- Trend: Phase 4 complete — all curator UX and explore features human-verified

*Updated after each plan completion*
| Phase 01-deployment-hardening P01 | 12 | 2 tasks | 3 files |
| Phase 01-deployment-hardening P03 | 5 | 2 tasks | 8 files |
| Phase 01-deployment-hardening P04 | 2 | 1 task | 1 file |
| Phase 02-data-model-and-audit-trail P01 | 3 | 2 tasks | 1 file |
| Phase 02-data-model-and-audit-trail P02 | 6 | 2 tasks | 3 files |
| Phase 02-data-model-and-audit-trail P04 | 14 | 2 tasks | 5 files |
| Phase 02-data-model-and-audit-trail P03 | 9 | 2 tasks | 2 files |
| Phase 03-stable-public-rest-api P01 | 5 | 2 tasks | 2 files |
| Phase 03-stable-public-rest-api P02 | 7 | 2 tasks | 3 files |
| Phase 03-stable-public-rest-api P03 | 10 | 1 task | 1 file |
| Phase 03-stable-public-rest-api P04 | 8 | 2 tasks | 4 files |
| Phase 04-curator-ux-and-explore P04 | 4 | 2 tasks | 4 files |
| Phase 04-curator-ux-and-explore P01 | 4 | 2 tasks | 4 files |
| Phase 04-curator-ux-and-explore P03 | 9 | 2 tasks | 2 files |
| Phase 04-curator-ux-and-explore P02 | 15 | 2 tasks | 2 files |
| Phase 04-curator-ux-and-explore P05 | 13 | 1 task | 0 files |
| Phase 05-exports-and-dataset-publication P01 | 3 | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Research]: Dual-Blueprint split — keep existing `api_bp` for UI-internal endpoints; new `v1_api_bp` with `/api/v1` prefix for the stable public API
- [Research]: Phase 1 (deployment) must precede all other work; data loss and memory blow-up are irreversible and block curator onboarding
- [Research]: Data provenance columns (CURAT-01, EXPLO-04) must be added in Phase 2 before any curation feeds publication figures
- [01-02]: Start with 2 Gunicorn workers (not 4) — conservative for BioBERT ~440MB model; scale up after measuring docker stats
- [01-02]: HEALTHCHECK start-period increased from 20s to 60s — BioBERT preload_app=True takes ~30-40s at startup
- [01-02]: Use appuser in crontab (not root) — appuser owns /app/data and /app/logs where backup writes
- [01-02]: Retain backups for 7 days — balances storage cost against recovery window before external curators submit data
- [Phase 01-deployment-hardening]: DATABASE_PATH default is /app/data/ke_wp_mapping.db — must match Docker volume mount point
- [Phase 01-deployment-hardening]: WAL mode set via PRAGMA on every connection (not once at DB creation) — idempotent and ensures mode survives reconnects
- [Phase 01-deployment-hardening]: FLASK_ENV must be set before app import in conftest to prevent module-level create_app() using wrong config
- [Phase 01-deployment-hardening]: NPZ matrix format with pre-normalized vectors: eliminates pickle deserialization risk; dot product equals cosine similarity after unit normalization at save time
- [01-04]: Guard warm-up with FLASK_ENV=production — prevents BioBERT load during pytest (FLASK_ENV=testing) and plain python app.py (FLASK_ENV defaults to development)
- [01-04]: try/except wraps warm-up so startup failure is non-fatal — workers still lazy-load BioBERT on first request if master-process preload fails
- [02-01]: Backfill existing mapping rows with SQLite randomblob() UUID expression — runs atomically inside init_db() transaction, avoids loading rows into Python
- [02-01]: Unique index on uuid uses CREATE UNIQUE INDEX IF NOT EXISTS — idempotent and enforces uniqueness for all future inserts
- [02-01]: Proposal table uuid is nullable and not backfilled — new proposals get uuid via create_proposal() when wired in a later Phase 2 plan
- [02-02]: pending_proposal takes priority over approved_mapping in enriched check methods — most actionable blocking state shown first (flag stale, then resubmit)
- [02-02]: flag_proposal_stale endpoint placed in api_bp (not admin_bp) — curators (not only admins) need to flag stale proposals; @login_required is sufficient
- [02-02]: GO proposal admin approval flow not yet implemented — admin.py has no GO proposal approval route; GoMappingModel provenance update deferred until that route is added
- [Phase 02-data-model-and-audit-trail]: UUID shown in mapping_detail.html (permanent detail page) but NOT in curator explore table — admin/API only per locked decision
- [Phase 02-data-model-and-audit-trail]: mapping_detail.html uses standalone HTML with navigation include — no base template inheritance; all templates in this project are standalone
- [Phase 02-data-model-and-audit-trail]: checkForDuplicatePair() fires inside setTimeout after pathway selection to ensure wp_id hidden field is updated before AJAX call
- [Phase 02-data-model-and-audit-trail]: data-score attribute added to suggestion-item HTML using scores.final_score; avoids extra AJAX round-trip for suggestion score capture
- [Phase 02-data-model-and-audit-trail]: mapping_type='wp' vs mapping_type='go' on flag-stale buttons routes /flag_proposal_stale to correct proposal model
- [03-01]: suggestion_score column is REAL, nullable — NULL for all pre-Phase-3 rows; non-null only after curator approval of a scored proposal
- [03-01]: go_namespace DEFAULT 'biological_process' — all current GO mappings are BP; column present for MF/CC extensibility
- [03-01]: suggestion_score added to ALLOWED_FIELDS in update_mapping() — required so the kwarg is not silently dropped by the dynamic SET clause builder
- [03-02]: CORS after_request hook scoped to v1_api_bp — does not affect internal blueprints; blueprint-scoped CORS is the correct isolation pattern
- [03-02]: csrf.exempt(v1_api_bp) must be called before app.register_blueprint(v1_api_bp) — order matters for CSRF exemption
- [03-02]: AOP SPARQL resolution raises ValueError on any failure, mapped to 400 — prevents 500 on upstream SPARQL unavailability
- [03-02]: total_pages=0 when total=0 — math.ceil(0/50)=0 correctly represents empty result set
- [03-03]: v1_client fixture calls v1_mod.set_models() with fresh temp-file DB — required because TestingConfig uses :memory: which creates separate DB per sqlite3.connect() call, making routes fail with 'no such table'
- [03-03]: Seed helpers take model instances as arguments rather than flask_app.service_container — cleaner isolation, avoids cross-test contamination
- [03-04]: All /submit submissions create pending proposals regardless of submitter role — closes UAT Test 7; mapping created only at admin approval
- [03-04]: JOIN alias pattern (m.ke_id AS mapping_ke_id) prevents sqlite3.Row dict() NULL-clobbering of p.ke_id on new-pair proposals with mapping_id=NULL
- [03-04]: submit_client test fixture directly replaces api_mod.proposal_model/mapping_model attributes using temp-file DB — same :memory: isolation workaround as v1_client
- [Phase 04-curator-ux-and-explore]: ?format=csv param checked before Accept header in _respond_collection — allows download-button anchor hrefs to trigger CSV without setting Accept headers
- [Phase 04-curator-ux-and-explore]: Content-Disposition: attachment added to CSV responses — needed for browser download trigger from anchor href
- [04-01]: Single bulk SPARQL for all AOP->KE relationships — locked KE-01 decision prohibits live SPARQL per KE selection; one call fetches 1567 KEs x 3614 AOP-KE rows
- [04-01]: ke_aop_membership.json gitignored (data/*.json) — generated artifact, regenerated by precompute script, not stored in repo
- [04-01]: Linear scan over ~1561 ke_metadata entries in /api/ke_detail — fast enough for list size; ke_metadata_index property in ServiceContainer available for future O(1) optimization
- [04-01]: <path:ke_id> URL converter for /api/ke_detail route — ensures "KE%2055" decodes to "KE 55" correctly in Flask routing
- [Phase 04-curator-ux-and-explore]: explore() route drops dataset= server render entirely - KE-WP DataTable is AJAX-only via /api/v1/mappings
- [Phase 04-curator-ux-and-explore]: Filter chip CSS duplicated inline in explore.html (not only main.css) because 04-03 and 04-02 execute in the same wave
- [Phase 04-curator-ux-and-explore]: Coverage Gaps uses /get_aop_kes + /api/v1/mappings?aop_id client-side diff - avoids new dedicated endpoint
- [Phase 04-curator-ux-and-explore]: loadKEDetail() replaces showKEPreview+loadKEContext+displayKEContext — one call to /api/ke_detail/ per KE selection, no live SPARQL
- [Phase 04-curator-ux-and-explore]: KE context panel is <details id=ke-context-panel> element — collapsibility via native HTML, .ke-context-panel CSS applies directly
- [Phase 04-curator-ux-and-explore]: ?ke_id= URL param cleaned from URL via history.replaceState immediately after read; applied after Select2 init via 100ms setTimeout
- [05-01]: GMT term name format KE{N}_{Title_Slug}_{Target_ID} locked by user; numeric part extracted with re.sub(r'\D', '', ke_id), title normalised via unicodedata NFKD + ASCII encode
- [05-01]: Batch SPARQL VALUES query for all WP IDs in one round-trip — avoids N+1 HTTP calls to WikiPathways endpoint
- [05-01]: rdflib Graph.serialize(format='turtle') returns str in rdflib >= 6.0 — no decode needed; KEWP and MAPPING namespaces bound per Graph
- [05-01]: Exporter functions accept pre-fetched mapping dicts — no DB access inside exporter modules

### Pending Todos

None yet.

### Blockers/Concerns

- [Pre-Phase 1]: Database path must be changed to `/app/data/ke_wp_mapping.db` and mounted as a Docker volume before any external user submits data — data loss risk is irreversible
- [Resolved 02-02]: curator_github was NOT stored at approval time — now fixed; approved_by_curator + approved_at_curator written at every approve_proposal() call
- [Resolved 04-01]: Explore filter by `aop_id` — resolved via precompute approach: ke_aop_membership.json written by precompute script, loaded via ServiceContainer, served by /api/ke_detail with no live SPARQL

## Session Continuity

**Last session:** 2026-02-21T19:14:12Z
**Stopped at:** Completed 05-01-PLAN.md (GMT + RDF exporter modules)
**Resume file:** .planning/phases/05-exports-and-dataset-publication/05-01-SUMMARY.md
