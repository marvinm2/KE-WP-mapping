# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.
**Current focus:** Phase 4 — Curator UX and Explore (In Progress)

## Current Position

Phase: 4 of 6 (Curator UX and Explore)
Plan: 4 of 5 in current phase (04-04 complete — public stats page + CSV export)
Status: Phase 4 In Progress (1 of 5 plans complete)
Last activity: 2026-02-21 — Completed 04-04 (/stats public page, ?format=csv on /api/v1/mappings)

Progress: [████░░░░░░] 20% (Phase 4: 1/5 plans done)

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: 6 min
- Total execution time: 0.75 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-deployment-hardening | 4 | 20 min | 5 min |
| 02-data-model-and-audit-trail | 4 (complete) | 26 min | 6.5 min |
| 03-stable-public-rest-api | 4 (complete) | 30 min | 7.5 min |
| 04-curator-ux-and-explore | 1 (in progress) | 4 min | 4 min |

**Recent Trend:**
- Last 5 plans: 03-02 (7 min), 03-03 (10 min), 03-04 (8 min), 04-04 (4 min)
- Trend: Phase 4 in progress — public stats page and CSV export param added

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Pre-Phase 1]: Database path must be changed to `/app/data/ke_wp_mapping.db` and mounted as a Docker volume before any external user submits data — data loss risk is irreversible
- [Resolved 02-02]: curator_github was NOT stored at approval time — now fixed; approved_by_curator + approved_at_curator written at every approve_proposal() call
- [Pre-Phase 4]: Explore filter by `aop_id` requires a design decision — pre-compute AOP membership into the database (preferred) vs. live SPARQL join per request

## Session Continuity

**Last session:** 2026-02-21T13:44:24.538Z
**Stopped at:** Completed 04-04-PLAN.md (public stats page + CSV export param)
**Resume file:** None
