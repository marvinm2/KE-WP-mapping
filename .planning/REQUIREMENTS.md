# Requirements: v1.6 User & Admin Experience

**Defined:** 2026-05-14
**Core Value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.

## v1.6 Requirements

### Landing & Stats

- [ ] **LAND-01**: Public landing page at `/` with hero, headline mapping counts (KE-WikiPathways / KE-GO / KE-Reactome / total), and CTAs into mapper / Explore / AOP Explorer.
- [ ] **LAND-02**: Mapper accessible at `/mapper` (current `/` mapper view moves; `/` is now landing). Curators are notified of the bookmark change 24-48h before deploy.
- [ ] **LAND-03**: Landing page is fast — server-rendered Jinja, no client-side data fetch required for first paint.
- [ ] **STATS-01**: `/stats` page includes KE-Reactome in the headline counts row (4 cards: KE-WP / KE-GO / KE-Reactome / Total) — currently missing.
- [ ] **STATS-02**: `/stats` Confidence Breakdown table includes a KE-Reactome column.
- [ ] **STATS-03**: `/stats` Filter and Export controls support Reactome (JSON/CSV download via `/api/v1/reactome-mappings`).
- [ ] **STATS-04**: `/stats` Export Formats button row includes KE-Reactome GMT and Turtle.

### Source-data versioning

- [ ] **VER-01**: `SourceVersionService` fetches the current release identifier for WikiPathways (`data.wikipathways.org/current/` archive folder), Reactome (`/ContentService/data/database/version`), GO (`go-basic.obo` `data-version:` line), and AOP-Wiki (quarterly XML dump filename date). 24-hour in-process TTL cache; never blocks page render on upstream failure.
- [ ] **VER-02**: Landing page displays source-data version badges (one per resource) reading from the service.
- [ ] **VER-03**: `/stats` page displays source-data version badges.
- [ ] **VER-04**: Downloads cards display the source-data version for the resource they export.

### AOP Explorer (rename + merge + parity)

- [ ] **AOPX-01**: `/aop-network` renamed to `/aop-explorer` in nav, page title, and template name.
- [ ] **AOPX-02**: `/aop-network` URL preserved as HTTP 301 redirect to `/aop-explorer` (inbound links from papers/Slack/slides must not break).
- [ ] **AOPX-03**: "Coverage Gaps" tab removed from `/explore`; functionality merged into AOP Explorer via a visible segmented-control filter (All KEs / Unmapped only / Gaps in WikiPathways / Gaps in GO / Gaps in Reactome) — never a hidden dropdown.
- [ ] **AOPX-04**: AOP Explorer graph displays gene-count badges per KE node (parity with the inline mapper graph; lift via shared `AOPGraphCore` IIFE).
- [ ] **AOPX-05**: AOP Explorer graph displays green-border for mapped KEs (parity with the inline mapper graph).
- [ ] **AOPX-06**: AOP Explorer shows an OECD AOP development-status badge per AOP using the 7 canonical values: "Under Development: Contributions and Comments Welcome", "Under Development", "Open for Adoption", "Under Review / Internal Review", "EAGMST Under Review", "EAGMST Approved", "WPHA/WNT Endorsed".
- [ ] **AOPX-07**: AOP Explorer has an OECD-status filter to narrow to a subset of statuses; never hides any status by default.
- [ ] **AOPX-08**: `data/aop_oecd_status.json` precomputed artifact populated from the AOP-Wiki XML dump (or HTML scrape fallback). Updated quarterly with the dump.

### Mapper page (density + previews)

- [ ] **MAPR-01**: KE context panel collapses by default with KE title + biolevel chip + AOP context visible as a summary row; click-to-expand reveals full description.
- [ ] **MAPR-02**: Suggestion cards (WikiPathways / GO / Reactome) reduce vertical padding and chip spacing without dropping data fidelity.
- [ ] **MAPR-03**: Submit + assessment area presented as a sticky footer (with iOS Safari `env(safe-area-inset-bottom)` handling and a < 600 px inline-fallback layout).
- [ ] **MAPR-04**: Inline AOP graph rendering is preserved across the density-pass CSS sweep — no regression in graph layout, gene-badge positioning, node-html-label rendering, or DiagramJS controls.
- [ ] **MAPR-05**: Confidence-assessment preview shows the KE description (currently missing).
- [ ] **MAPR-06**: Mapping preview shows the pathway description (currently missing).
- [ ] **MAPR-07**: Mapper page has an OECD AOP status filter + per-AOP badge (uses the AOPX-08 precomputed data).

### Naming sweep (user-visible only)

- [ ] **NAME-01**: User-visible "WP" → "WikiPathways" across templates, CSS class names visible to users, and JS string literals that render to user-visible text. Internal API field names + URL paths unchanged.
- [ ] **NAME-02**: Mapper tab labels "KE-WP Mapping" → "KE-WikiPathways Mapping" (also Explore and Downloads).
- [ ] **NAME-03**: Explore table column headers "WP ID" / "WP Title" → "WikiPathways ID" / "WikiPathways Title".
- [ ] **NAME-04**: Downloads card titles and descriptions use "WikiPathways" not "WP" in display text.

### Resource links & footer

- [ ] **LINK-01**: "Key Event details page" link from the mapper points to the upstream AOP-Wiki KE page when the upstream page is richer than the internal `/ke-details` view.
- [ ] **LINK-02**: "Pathway details page" link from the mapper points to the upstream WikiPathways / Reactome / GO page for the selected pathway (rather than the internal `/pw-details` view).
- [ ] **LINK-03**: Footer "Documentation API Downloads" links visually separated (bullet / pipe / spacing fix — current concatenation reads as one string).
- [ ] **LINK-04**: Internal `/ke-details` and `/pw-details` route handlers preserved (deep links from external systems must still resolve even though the in-product nav points upstream).

### Explore page

- [ ] **EXPL-01**: KE-WikiPathways tab label includes the `(N)` mapping count (parity with KE-GO `(7)` and KE-Reactome `(2)`).
- [ ] **EXPL-02**: Confidence column rendered as a coloured badge (High / Medium / Low) instead of plain text.
- [ ] **EXPL-03**: Each Explore table shows an AOP-context column indicating which AOP each KE belongs to (with AOP ID).
- [ ] **EXPL-04**: Each Explore table shows a last-updated / approved-at date column.
- [ ] **EXPL-05**: AOP filter dropdown includes the AOP ID prefix (e.g., "AOP 237 — Title").

### Downloads page

- [ ] **DOWN-01**: Cards regrouped by resource (WikiPathways cards together, GO together, Reactome together) instead of by format.
- [ ] **DOWN-02**: Each download card has a per-type preview showing the first ~20 lines of the file (GMT / RDF / CSV / JSON), via `itertools.islice` server-side endpoint.
- [ ] **DOWN-03**: JSON and CSV download cards surfaced alongside GMT + RDF (currently only reachable via `/stats` filter+export).

### Multi-provider OAuth (production rollout)

- [ ] **AUTH-01**: ORCID provider button visible in the login modal when `ORCID_CLIENT_ID` env is configured on tgx1.
- [ ] **AUTH-02**: LS Login (Elixir AAI) provider button visible in the login modal when `LSAAI_CLIENT_ID` env is configured on tgx1.
- [ ] **AUTH-03**: SURFconext provider button visible in the login modal when `SURF_CLIENT_ID` env is configured AND `SURF_ENABLED=true` feature flag is set (handles 1-2 week production approval gate).
- [ ] **AUTH-04**: Provider-prefixed identity invariant enforced at the DB level via `CHECK (identity LIKE '%:%')` on identity-bearing columns; grep audit confirms no `lstrip('github:')` or single-provider parsing remains.
- [ ] **AUTH-05**: Human E2E test of each provider (login → submit proposal → admin approve) signed off — carries from v1.2.
- [ ] **AUTH-06**: TLS chain verified (`curl -vI` on each redirect URI, certificate expiry > 30 days) before flipping each provider into production.

### Assessment metadata persistence (KE-WP + KE-Reactome parity)

- [x] **ASMT-01**: KE-WP `proposals` table gains four columns — `proposed_relationship`, `proposed_basis`, `proposed_specificity`, `proposed_coverage` — persisting answers to the four current KE-WP assessment questions. Migration idempotent (mirror Phase 19 KE-GO pattern).
- [x] **ASMT-02**: KE-WP `mappings` table gains the same four columns + `assessment_version` flag; existing approved mappings get `assessment_version='v1'` (legacy, derived confidence only).
- [x] **ASMT-03**: KE-Reactome `ke_reactome_proposals` and `ke_reactome_mappings` tables gain the same four columns + `assessment_version` flag.
- [ ] **ASMT-04**: KE-Reactome mapper UI replaces today's 3-button confidence selector with the 4-question KE-WP assessment.
- [ ] **ASMT-05**: KE-Reactome admin proposal modal displays the four-question answers + derived confidence (parity with KE-WP admin modal).
- [ ] **ASMT-06**: KE-WP admin proposal modal displays the four-question answers (currently shows only derived confidence).
- [ ] **ASMT-07**: Public API `/api/v1/mappings` and `/api/v1/reactome-mappings` emit the four step answers + `assessment_version` (additive — analyser ignores unknown keys; verify parser mode is non-strict before lockstep PR).
- [x] **ASMT-08**: Bulk export SELECT for `get_all_mappings` (KE-WP) and the Reactome equivalent include the new columns — explicit guard against the 4th-recurrence SELECT drift pattern.
- [ ] **ASMT-09**: `KE-MAPPING-API-REFERENCE.md` in the `molAOP-analyser` repo updated in lockstep with the API contract change (paired PR required per cross-tool checklist in `molAOP_services/CLAUDE.md`).
- [x] **ASMT-10**: `REACTOME_PROPOSAL_CARRY_FIELDS` constant (defined v1.4, unused) finally imported by `create_approved_mapping` for Reactome — resolves v1.4 tech-debt.

### Admin click reduction

- [ ] **ADMIN-01**: Bulk-select checkboxes added to each admin proposal queue (KE-WP, KE-GO, KE-Reactome) with header "select-all".
- [ ] **ADMIN-02**: Bulk-approve endpoints `POST /admin/{proposals|go-proposals|reactome-proposals}/bulk-approve` accept a list of proposal IDs and loop over the existing single-INSERT `create_approved_mapping` carry-fields path in one transaction. Response shape: `{approved: [uuids], failed: [{id, reason}]}`. Atomicity model: all-or-nothing per v1.4 H-1 invariant (TBC during phase planning).
- [ ] **ADMIN-03**: Keyboard shortcuts `a` (approve) and `r` (reject) — focus-context guarded (never fire while form input or text-area is focused).
- [ ] **ADMIN-04**: Persistent side panel that stays open across the proposal queue, auto-advancing to the next pending proposal after each approve/reject.
- [ ] **ADMIN-05**: Cheat-sheet modal accessible via `?` key explaining available keyboard shortcuts.
- [ ] **ADMIN-06**: Bulk-approve operation produces an audit-log line with the UUIDs of all approved mappings (recoverable if a bulk-approve turns out to be a mistake).
- [ ] **ADMIN-07**: Shared admin JS extracted into `static/js/admin_proposals.js` (currently inlined per-template across all three siblings).

### Login state preservation

- [ ] **LOGIN-01**: When an unauthenticated curator clicks "Submit" on a fully-filled mapping (KE + pathway + assessment), the page state (KE, pathway, all assessment answers) is stored in Flask server-side session before the OAuth redirect.
- [ ] **LOGIN-02**: Post-OAuth callback rehydrates the stored state and presents the assessment + submit step ready to submit (no re-click of assessment buttons).
- [ ] **LOGIN-03**: Stored state is one-shot consumed — cleared on successful submit OR on session timeout.
- [ ] **LOGIN-04**: Stored state cleared on explicit logout to prevent cross-user leak on shared workstations (workshop laptops).
- [ ] **LOGIN-05**: State is NEVER stored in localStorage or URL hash (defeats SURFconext exact-match `redirect_uri` and leaks across users).

### v1.5 tech-debt sweep

- [ ] **DEBT-01**: Dead `setupMethodFilterButtons` helper + residual `currentMethodFilter` state at `static/js/main.js:384/1613/2603/2814` removed (v1.5 audit §6.1).
- [ ] **DEBT-02**: WP `/submit` defensive-guard symmetry — add `if not mapping_model: return jsonify({"error": ...}), 503` to match the GO branch at `api.py:1478` (v1.5 audit §6.3).

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Gene Identifier System

- **GENEID-01**: Migrate gene-identifier storage and APIs from HGNC symbols to NCBI Gene IDs (or Ensembl Gene IDs). Significant data-model change; affects all gene-overlap signals across WP/GO/Reactome and the public API gene fields.

### Assessment Rubric Versioning

- **RUBVER-01**: Persist rubric version + selected-label-text per question alongside the integer/enum answer, so historical proposals remain interpretable if the rubric wording or option count changes in a future milestone.

### Per-mapping Source-data Version

- **VERMAP-01**: Per-mapping `source_version_at_approval` columns capturing the upstream resource release at the time of approval (enables version-aware diff alerts when upstream releases new versions).

### Reactome Viewer

- **RVIEWHL-01**: Visible gene highlight on Reactome DiagramJS canvas (v1.4 / v1.5 carry, currently structural-only via `flagItems`). Needs HGNC↔diagram-entity mapping investigation, possibly NCBI-ID-based flagging.

### Standing carry-forward (coordination-dependent)

- **ICCAL-01**: IC weight calibration session with domain expert (open since v1.2).

## Out of Scope

Explicitly excluded for v1.6. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| KE-GO assessment rubric changes | KE-GO retains its existing 3-dim Connection/Specificity/Evidence rubric (Phase 19). v1.6 assessment work is parity port KE-WP → KE-Reactome only. |
| Hide non-endorsed AOPs by default | Breaks nano-AOP / qAOP / emerging-tox workflows. Filter exists; default stays "show all". |
| AI auto-approve of proposals | Defeats human-in-the-loop value prop. |
| Email-digest of pending proposals | Curator team is 3-5 people; no SMTP infrastructure; over-engineered at current scale. |
| Embedded full `/stats` dashboard on landing | Landing is a hero + headline-numbers funnel, not a dashboard duplicate. /stats stays as the deep dashboard, linked from landing. |
| Cross-AOP mega-graph | Illegible at 3,000+ KE nodes across 468 AOPs. AOP Explorer stays one-AOP-at-a-time. |
| OAuth account-linking | Already deferred as AUTH-08 since v1.2. |
| Custom-subset download builder on Downloads | `/explore` filtered export already does this; would duplicate functionality. |
| Tabbed mapper sub-pages (separate KE / pathway / assessment pages) | Breaks single-flow narrative and the login-redirect state contract. |
| Gene-identifier system swap | Significant data-model change; warrants its own milestone. Listed in v2. |
| Rubric versioning on assessment metadata | Defer until KE-WP/Reactome parity is in. Listed in v2. |
| Visible gene highlight on Reactome diagram canvas | Listed in v2 as RVIEWHL-01. |
| New pathway-resource integrations (KEGG, HPO, etc.) | v1.6 is refinement, not expansion. |
| Migration to PostgreSQL | SQLite WAL still meets curator-team scale. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation 2026-05-14.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LAND-01 | Phase 35 | Pending |
| LAND-02 | Phase 35 | Pending |
| LAND-03 | Phase 35 | Pending |
| STATS-01 | Phase 35 | Pending |
| STATS-02 | Phase 35 | Pending |
| STATS-03 | Phase 35 | Pending |
| STATS-04 | Phase 35 | Pending |
| VER-01 | Phase 35 | Pending |
| VER-02 | Phase 35 | Pending |
| VER-03 | Phase 35 | Pending |
| VER-04 | Phase 35 | Pending |
| AOPX-01 | Phase 36 | Pending |
| AOPX-02 | Phase 36 | Pending |
| AOPX-03 | Phase 36 | Pending |
| AOPX-04 | Phase 36 | Pending |
| AOPX-05 | Phase 36 | Pending |
| AOPX-06 | Phase 36 | Pending |
| AOPX-07 | Phase 36 | Pending |
| AOPX-08 | Phase 35 | Pending |
| MAPR-01 | Phase 39 | Pending |
| MAPR-02 | Phase 39 | Pending |
| MAPR-03 | Phase 39 | Pending |
| MAPR-04 | Phase 39 | Pending |
| MAPR-05 | Phase 39 | Pending |
| MAPR-06 | Phase 39 | Pending |
| MAPR-07 | Phase 39 | Pending |
| NAME-01 | Phase 36 | Pending |
| NAME-02 | Phase 36 | Pending |
| NAME-03 | Phase 36 | Pending |
| NAME-04 | Phase 36 | Pending |
| LINK-01 | Phase 36 | Pending |
| LINK-02 | Phase 36 | Pending |
| LINK-03 | Phase 36 | Pending |
| LINK-04 | Phase 36 | Pending |
| EXPL-01 | Phase 36 | Pending |
| EXPL-02 | Phase 36 | Pending |
| EXPL-03 | Phase 36 | Pending |
| EXPL-04 | Phase 36 | Pending |
| EXPL-05 | Phase 36 | Pending |
| DOWN-01 | Phase 36 | Pending |
| DOWN-02 | Phase 36 | Pending |
| DOWN-03 | Phase 36 | Pending |
| AUTH-01 | Phase 35 | Pending |
| AUTH-02 | Phase 35 | Pending |
| AUTH-03 | Phase 35 | Pending |
| AUTH-04 | Phase 35 | Pending |
| AUTH-05 | Phase 35 | Pending |
| AUTH-06 | Phase 35 | Pending |
| ASMT-01 | Phase 34 | Complete |
| ASMT-02 | Phase 34 | Complete |
| ASMT-03 | Phase 34 | Complete |
| ASMT-04 | Phase 37 | Pending |
| ASMT-05 | Phase 37 | Pending |
| ASMT-06 | Phase 37 | Pending |
| ASMT-07 | Phase 34 | Pending |
| ASMT-08 | Phase 34 | Complete |
| ASMT-09 | Phase 34 | Pending |
| ASMT-10 | Phase 34 | Complete |
| ADMIN-01 | Phase 38 | Pending |
| ADMIN-02 | Phase 38 | Pending |
| ADMIN-03 | Phase 38 | Pending |
| ADMIN-04 | Phase 38 | Pending |
| ADMIN-05 | Phase 38 | Pending |
| ADMIN-06 | Phase 38 | Pending |
| ADMIN-07 | Phase 38 | Pending |
| LOGIN-01 | Phase 39 | Pending |
| LOGIN-02 | Phase 39 | Pending |
| LOGIN-03 | Phase 39 | Pending |
| LOGIN-04 | Phase 39 | Pending |
| LOGIN-05 | Phase 39 | Pending |
| DEBT-01 | Phase 39 | Pending |
| DEBT-02 | Phase 39 | Pending |

**Coverage:**
- v1.6 requirements: 72 total (originally summarized as ~60 in milestone scoping; precise count after REQ-ID assignment is 72 across 14 categories: LAND 3, STATS 4, VER 4, AOPX 8, MAPR 7, NAME 4, LINK 4, EXPL 5, DOWN 3, AUTH 6, ASMT 10, ADMIN 7, LOGIN 5, DEBT 2)
- Mapped to phases: 72 (100%)
- Unmapped: 0

**Per-phase requirement counts (each requirement maps to exactly one phase — no duplicates):**
- Phase 34 (Schema Parity): 7 requirements — ASMT-01, 02, 03, 07, 08, 09, 10
- Phase 35 (Operational + Greenfield Parallel): 18 requirements — LAND-01..03 + STATS-01..04 + VER-01..04 + AUTH-01..06 + AOPX-08
- Phase 36 (Renames, Merges, Naming Sweep): 23 requirements — AOPX-01..07 + NAME-01..04 + LINK-01..04 + EXPL-01..05 + DOWN-01..03
- Phase 37 (Sibling-Parity UI): 3 requirements — ASMT-04, 05, 06
- Phase 38 (Admin Click Reduction): 7 requirements — ADMIN-01..07
- Phase 39 (Polish): 14 requirements — MAPR-01..07 + LOGIN-01..05 + DEBT-01..02

Total: 7 + 18 + 23 + 3 + 7 + 14 = 72 ✓

---

*Requirements defined: 2026-05-14*
*Traceability table populated: 2026-05-14 after roadmap creation (phases 34–39)*
