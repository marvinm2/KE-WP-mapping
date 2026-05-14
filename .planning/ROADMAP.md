# Roadmap: KE-WP / KE-GO Mapping Tool

## Milestones

- ✅ **v1.0 MVP** — Phases 1–7 (shipped 2026-02-23)
- ✅ **v1.1 Visuals** — Phases 8–12 (shipped 2026-03-04)
- ✅ **v1.2 Curation Depth** — Phases 13–16 (shipped 2026-03-06)
- ✅ **v1.3 GO Assessment Quality** — Phases 17–22 (shipped 2026-03-11)
- ✅ **v1.4 Reactome Integration** — Phases 23–28 (shipped 2026-05-08)
- ✅ **v1.5 Scoring & Polish** — Phases 29–33 (shipped 2026-05-11)
- 🚧 **v1.6 User & Admin Experience** — Phases 34–39 (in progress, scoped 2026-05-14)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–7) — SHIPPED 2026-02-23</summary>

- [x] Phase 1: Deployment Hardening (4/4 plans) — completed 2026-02-19
- [x] Phase 2: Data Model and Audit Trail (4/4 plans) — completed 2026-02-20
- [x] Phase 3: Stable Public REST API (4/4 plans) — completed 2026-02-21
- [x] Phase 4: Curator UX and Explore (5/5 plans) — completed 2026-02-21
- [x] Phase 5: Exports and Dataset Publication (4/4 plans) — completed 2026-02-22
- [x] Phase 6: API Documentation (3/3 plans) — completed 2026-02-22
- [x] Phase 7: KE-GO Proposal Workflow (4/4 plans) — completed 2026-02-23

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Visuals (Phases 8–12) — SHIPPED 2026-03-04</summary>

- [x] Phase 8: Brand Refresh and CSS Cleanup (5/5 plans) — completed 2026-02-24
- [x] Phase 9: WikiPathways Embed Viewer (3/3 plans) — completed 2026-03-03
- [x] Phase 10: AOP Network Graph (4/4 plans) — completed 2026-03-04
- [x] Phase 11: Inline AOP Graph on Mapper Page (3/3 plans) — completed 2026-03-04
- [x] Phase 12: Gene Set Visualization on AOP Graph (3/3 plans) — completed 2026-03-04

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Curation Depth (Phases 13–16) — SHIPPED 2026-03-06</summary>

- [x] Phase 13: Low-Risk Foundations (3/3 plans) — completed 2026-03-04
- [x] Phase 14: Auth Expansion (2/2 plans) — completed 2026-03-06
- [x] Phase 15: GO Hierarchy Integration (2/2 plans) — completed 2026-03-06
- [x] Phase 16: API Metadata Capstone (2/2 plans) — completed 2026-03-06

Full details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 GO Assessment Quality (Phases 17–22) — SHIPPED 2026-03-11</summary>

- [x] Phase 17: KE Description Toggle (2/2 plans) — completed 2026-03-09
- [x] Phase 18: Directionality Detection and Tagging (3/3 plans) — completed 2026-03-10
- [x] Phase 19: Structured Three-Dimension Assessment (3/3 plans) — completed 2026-03-10
- [x] Phase 20: GO Molecular Function Suggestions (2/2 plans) — completed 2026-03-10
- [x] Phase 21: Wire GO Namespace Through Approval Chain (1/1 plan) — completed 2026-03-11
- [x] Phase 22: Fix Bulk Export SELECT for Direction and Namespace (1/1 plan) — completed 2026-03-11

Full details: `.planning/milestones/v1.3-ROADMAP.md`

</details>

<details>
<summary>✅ v1.4 Reactome Integration (Phases 23–28) — SHIPPED 2026-05-08</summary>

- [x] Phase 23: Reactome Data Infrastructure (3/3 plans) — completed 2026-04-03
- [x] Phase 24: Database Models and Suggestion Service (2/2 plans) — completed 2026-04-29
- [x] Phase 25: Proposal Workflow and Admin UI (6/6 plans) — completed 2026-05-05
- [x] Phase 26: Public API and Exports (8/8 plans) — completed 2026-05-06
- [x] Phase 27: Reactome Pathway Viewer (4/4 plans) — completed 2026-05-06
- [x] Phase 28: KE Gene SPARQL Returns Persistent Identifiers (4/4 plans) — completed 2026-05-07

Full details: `.planning/milestones/v1.4-ROADMAP.md`

</details>

<details>
<summary>✅ v1.5 Scoring & Polish (Phases 29–33) — SHIPPED 2026-05-11</summary>

- [x] Phase 29: Pure-Semantic Ranking Shift (6/6 plans) — completed 2026-05-10
- [x] Phase 30: Reactome Suggestion Card Parity and Threshold Tuning (2/2 plans) — completed 2026-05-10
- [x] Phase 31: Reactome Viewer Polish (3/3 plans) — completed 2026-05-11
- [x] Phase 32: GO/WP Sibling Debt Sweep (7/7 plans) — completed 2026-05-11
- [x] Phase 33: Baseline Cleanup (3/3 plans) — completed 2026-05-11

Full details: `.planning/milestones/v1.5-ROADMAP.md`

</details>

### 🚧 v1.6 User & Admin Experience (Phases 34–39) — IN PROGRESS

- [x] **Phase 34: Assessment Metadata Schema Parity** — Idempotent ALTER migrations on KE-WP + KE-Reactome proposal/mapping tables for 4-question assessment persistence; bulk-export SELECT updated; API additive; analyser parser-mode reviewed (completed 2026-05-14)
- [ ] **Phase 35: Operational + Greenfield Parallel Track** — OAuth env config + landing page + source-version service + `/stats` Reactome absorption + OECD AOP status precompute (three independent workstreams)
- [ ] **Phase 36: Renames, Merges, and Naming Sweep** — AOP Explorer rename with 301 redirect, Coverage Gaps merged via segmented control, graph parity (gene badges + green border), OECD badges, "WP" → "WikiPathways" copy sweep, footer separators, upstream resource-link rewrites, Downloads regroup + preview + JSON/CSV
- [ ] **Phase 37: Backend-Dependent UI — Assessment-Question Sibling Parity** — KE-WP admin modal displays four-question answers; KE-Reactome mapper UI adopts 4-question rubric; KE-Reactome admin modal mirrors KE-WP
- [ ] **Phase 38: Admin Click Reduction** — Bulk approve (reusing single-INSERT carry-fields path with fault-injection coverage), keyboard shortcuts, persistent side panel, cheat-sheet, audit log, shared admin JS
- [ ] **Phase 39: Polish — Mapper Density + Login State + v1.5 Carry** — Mapper density pass (scoped selectors, Cytoscape resize), KE/pathway description in previews, OECD filter on mapper, login state preservation (Flask session only), v1.5 dead-helper sweep + WP `/submit` 503 symmetry

## Phase Details

### Phase 34: Assessment Metadata Schema Parity

**Goal**: Land idempotent schema migrations so all four KE-WP + KE-Reactome proposal/mapping tables persist the four-question assessment answers, and the public API surfaces them additively — unblocking Phase 37 admin UI and Phase 38 bulk approve.

**Depends on**: Nothing (first phase of v1.6; pure schema + serializer work).

**Requirements**: ASMT-01, ASMT-02, ASMT-03, ASMT-07, ASMT-08, ASMT-09, ASMT-10

**Success Criteria** (what must be TRUE):
1. After deploy, `PRAGMA table_info` confirms the four new columns (`proposed_relationship`, `proposed_basis`, `proposed_specificity`, `proposed_coverage`) exist on `proposals`, `mappings`, `ke_reactome_proposals`, `ke_reactome_mappings`; `mappings` and `ke_reactome_mappings` additionally carry `assessment_version` with all pre-v1.6 rows showing `'v1'` and new rows showing `'v2'`.
2. A round-trip test (`create_proposal` → `create_approved_mapping` → `get_all_mappings`) returns the four question answers on both WP and Reactome rows — explicit guard against the 4th-recurrence bulk-export SELECT drift seen in v1.0/v1.2/v1.3.
3. `GET /api/v1/mappings` and `GET /api/v1/reactome-mappings` emit the four answers + `assessment_version`; the molAOP-analyser `services/api_service.py` parser mode has been read and confirmed non-strict (or a paired PR is open), and `KE-MAPPING-API-REFERENCE.md` is updated in lockstep.
4. The `REACTOME_PROPOSAL_CARRY_FIELDS` constant (defined v1.4, never imported) is now imported by Reactome's `create_approved_mapping`, resolving the v1.4 carryover tech-debt.

**Plans**: 4 plans across 3 waves
- [x] 34-01-PLAN.md — Migrations + dead-constant extension + Wave-0 test scaffolds (ASMT-01, 02, 03, 10)
- [x] 34-02-PLAN.md — Model-layer writes/reads (WP + Reactome) + bulk-export SELECT + Reactome round-trip test (ASMT-02, 03, 08, 10)
- [x] 34-03-PLAN.md — WP `/submit` + admin approve + HTTP round-trip test (ASMT-02, 08)
- [x] 34-04-PLAN.md — v1 API serializer (nested `assessment` object) + test amendment + cross-repo doc + CHANGELOG (ASMT-07, 09)

---

### Phase 35: Operational + Greenfield Parallel Track

**Goal**: Three independent workstreams ship in parallel — (a) multi-provider OAuth surfaced in production with provider-prefixed identity hardened at the DB level, (b) landing page + source-version service + `/stats` Reactome absorption, (c) OECD AOP status precompute data on disk — none of which block each other.

**Depends on**: Nothing (parallel with Phase 34).

**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, LAND-01, LAND-02, LAND-03, STATS-01, STATS-02, STATS-03, STATS-04, VER-01, VER-02, VER-03, VER-04, AOPX-08

**Success Criteria** (what must be TRUE):
1. With ORCID/LSAAI/SURF env vars set on tgx1, the login modal renders the corresponding provider button conditionally (`*_configured` template flag), each redirect URI's TLS chain has been verified with `curl -vI` (expiry > 30 days) before the cutover, and SURFconext is gated behind a `SURF_ENABLED=true` feature flag to absorb the 1-2 week production approval window. A DB-level `CHECK (identity LIKE '%:%')` constraint enforces provider-prefixed identity; a grep audit confirms no `lstrip('github:')` or single-provider parsing remains.
2. `GET /` renders a server-rendered landing page (no client-side data fetch for first paint) with hero, four headline counts (KE-WP, KE-GO, KE-Reactome, total), three CTAs, and source-version badges; `/mapper` serves the mapper view; curators received a comms note 24-48h before deploy about the bookmark change.
3. `/stats` shows KE-Reactome as a 4th headline card, in the Confidence Breakdown table, in Filter+Export controls, and in the Export Formats button row (GMT + Turtle). Source-version badges appear on Stats and on every Downloads card next to its resource.
4. `SourceVersionService.snapshot()` returns release identifiers for WikiPathways (`data.wikipathways.org/current/` archive folder), Reactome (`/ContentService/data/database/version`), GO (`go-basic.obo` `data-version:` line), and AOP-Wiki (quarterly XML dump filename date) with a 24-hour in-process TTL; an upstream failure renders `"unavailable"` and a tooltip rather than blocking the page.
5. `data/aop_oecd_status.json` exists on the Gluster volume populated with one of the 7 canonical OECD statuses per AOP, sourced from the AOP-Wiki XML dump after a front-loaded 30-minute investigation (HTML scrape via `beautifulsoup4` only as fallback if XML lacks the field).

**Plans**: TBD

---

### Phase 36: Renames, Merges, and Naming Sweep

**Goal**: Group all cosmetic + routing changes — AOP Explorer rename with mandatory 301 redirect, Coverage Gaps absorbed into AOP Explorer as a visible segmented-control filter, graph parity (gene badges + green border), OECD badges on AOPs, "WP" → "WikiPathways" user-visible copy sweep, footer separator fix, upstream `/ke-details`/`/pw-details` link rewrites, Downloads regrouped by resource with previews and JSON/CSV variants — into one deliverable that exercises the same template surface once.

**Depends on**: Phase 35 (OECD precompute data must exist before AOP Explorer can render OECD badges; landing page must exist so nav rename is coherent).

**Requirements**: AOPX-01, AOPX-02, AOPX-03, AOPX-04, AOPX-05, AOPX-06, AOPX-07, EXPL-01, EXPL-02, EXPL-03, EXPL-04, EXPL-05, NAME-01, NAME-02, NAME-03, NAME-04, LINK-01, LINK-02, LINK-03, LINK-04, DOWN-01, DOWN-02, DOWN-03

**Success Criteria** (what must be TRUE):
1. `GET /aop-network` returns a 301 redirect to `/aop-explorer` (route registration preserved — never removed); a regression test `test_aop_network_redirects_to_explorer` enforces this. The page title, nav link, and breadcrumbs all read "AOP Explorer".
2. AOP Explorer shows a visible segmented-control filter (All KEs / Unmapped only / Gaps in WikiPathways / Gaps in GO / Gaps in Reactome) — never a hidden dropdown — and the Coverage Gaps tab is removed from `/explore`. The standalone AOP graph renders gene-count badges (lazy fetch per node tap, not eager) and green-border for mapped KEs via shared `AOPGraphCore` options. Per-AOP OECD status badge appears with a status-filter dropdown that never hides any status by default.
3. A grep audit on user-visible templates, CSS class names visible to users, and JS string literals confirms "WP" has been replaced with "WikiPathways" in display text, while internal API field names (`wp_id`, `wp_title`), URL paths, and DB column names are unchanged. Mapper tab labels, Explore column headers, and Downloads card titles all use the long form. WikiPathways tab in Explore shows `(N)` mapping count; Confidence column rendered as coloured badge; AOP-context column with AOP ID; last-updated/approved-at date column; AOP filter dropdown shows `AOP <N> — Title` prefix on every page.
4. Mapper "Key Event details" and "Pathway details" links point to upstream AOP-Wiki / WikiPathways / Reactome / GO URLs when the upstream page is richer, while internal `/ke-details` and `/pw-details` route handlers continue to resolve (deep links from external systems must still 200). Footer "Documentation / API / Downloads" links are visually separated.
5. Downloads cards are regrouped by resource (WikiPathways together, GO together, Reactome together); each card shows a per-type preview block (first ~20 lines of GMT / RDF / CSV / JSON via `itertools.islice` server endpoint); JSON and CSV download variants are surfaced alongside GMT + RDF.

**Plans**: TBD

---

### Phase 37: Backend-Dependent UI — Assessment-Question Sibling Parity

**Goal**: With schema columns in place (Phase 34) and admin templates stable after the rename pass (Phase 36), port the KE-WP 4-question assessment UI to the KE-Reactome mapper tab (replacing today's 3-button confidence selector) and bring both KE-WP and KE-Reactome admin proposal modals to parity with the KE-GO admin modal — display all four question answers + derived confidence.

**Depends on**: Phase 34 (schema columns), Phase 36 (admin templates stable, no in-flight rename churn).

**Requirements**: ASMT-04, ASMT-05, ASMT-06

**Success Criteria** (what must be TRUE):
1. On the mapper page Reactome tab, a curator submitting a proposal sees the same 4-question assessment UI (relationship type / basis for mapping / KE-specificity / mechanism coverage) used on the WP tab; the legacy 3-button confidence selector is gone; submitted answers are persisted into `ke_reactome_proposals` (verified via DB inspection on a test submission).
2. Opening a KE-WP proposal in `/admin/proposals` shows the four question answers (today only the derived confidence is shown), with the same XSS-safe `escapeHtml` per-interpolation pattern locked in by v1.5 Phase 32.
3. Opening a KE-Reactome proposal in `/admin/reactome-proposals` shows the four question answers + derived confidence — three-way sibling parity (WP / GO / Reactome) preserved across all admin modal templates.

**Plans**: TBD

---

### Phase 38: Admin Click Reduction

**Goal**: Compress the proposal review path (today: list → details modal → modal-approve = ~4 clicks per proposal) via bulk-select + bulk-approve, keyboard shortcuts, persistent auto-advancing side panel, cheat-sheet, and shared admin JS — while preserving the single-INSERT carry-fields atomicity invariant from v1.4 H-1.

**Depends on**: Phase 37 (bulk approve must carry the four-question assessment fields uniformly across WP / GO / Reactome; touching admin templates after sibling-parity port avoids re-work).

**Requirements**: ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-04, ADMIN-05, ADMIN-06, ADMIN-07

**Success Criteria** (what must be TRUE):
1. Each admin proposal queue (KE-WP, KE-GO, KE-Reactome) has bulk-select checkboxes per row + a header "select-all"; a "Approve selected (n)" button POSTs to `/admin/{proposals|go-proposals|reactome-proposals}/bulk-approve` and returns `{approved: [uuids], failed: [{id, reason}]}`. The endpoint loops over the **existing single-INSERT `create_approved_mapping` carry-fields path in one transaction** — not a parallel bulk-SQL path. A fault-injection test asserts: bulk-approve 5 proposals, force the 3rd to fail, all 5 remain pending (v1.4 H-1 invariant preserved).
2. Keyboard shortcuts `a` (approve) and `r` (reject) fire on the focused proposal, with a focus-context guard that prevents firing while a form input, textarea, or select is focused; `?` opens a cheat-sheet modal listing the shortcuts.
3. A persistent side panel stays open across the proposal queue and auto-advances to the next pending proposal after each approve / reject — eliminating the close-modal-then-reopen cycle.
4. Each bulk-approve produces an audit-log line with the UUIDs of all approved mappings, recoverable if a bulk-approve turns out to be a mistake. Shared admin JS lives in `static/js/admin_proposals.js` (extracted IIFE); the three admin templates load it via `<script src=...>` rather than inlining duplicate handlers.

**Plans**: TBD

---

### Phase 39: Polish — Mapper Density, Login State, and v1.5 Carry

**Goal**: Land the highest-cascade-risk CSS change (mapper density pass) last so manual QA covers all v1.6 UI shifts in one sweep; preserve login state across the OAuth redirect using Flask server-side session only; fill in mapper preview gaps; add OECD filter on the mapper; finish v1.5 tech-debt sweep items.

**Depends on**: Phase 38 (all admin / mapper templates stable; density CSS is the last visual change so it cannot regress earlier phases).

**Requirements**: MAPR-01, MAPR-02, MAPR-03, MAPR-04, MAPR-05, MAPR-06, MAPR-07, LOGIN-01, LOGIN-02, LOGIN-03, LOGIN-04, LOGIN-05, DEBT-01, DEBT-02

**Success Criteria** (what must be TRUE):
1. Mapper density pass: KE context panel collapses by default with KE title + biolevel chip + AOP context visible as a summary row; suggestion cards (WP/GO/Reactome) have reduced vertical padding; submit + assessment area is a sticky footer with `env(safe-area-inset-bottom)` handling and a `< 600px` inline-fallback. **Every density-pass selector is scoped with a parent class** (v1.4 `09426fa` global-`button` cascade incident is the precedent); before/after screenshots captured at 1920/1366/768 widths; `aopGraphInline.cy.resize(); cy.fit()` is called after CSS container changes; inline AOP graph + DiagramJS controls render with no regression.
2. KE description appears in the confidence-assessment preview; pathway description appears in the mapping preview; the mapper page has an OECD AOP status filter + per-AOP badge using the AOPX-08 precomputed data.
3. Login state preservation: an unauthenticated curator clicking Submit on a fully-filled mapping has the full state (KE, pathway, all four assessment answers) stashed in Flask server-side session (`pending_submission`) before the OAuth redirect, rehydrated on the post-OAuth callback so the curator returns ready to submit without re-clicking assessment buttons. State is one-shot consumed (cleared on successful submit OR session timeout), cleared on explicit logout to prevent cross-user leak on shared workshop laptops, and **never** stored in localStorage or URL hash (which would defeat SURFconext exact-match `redirect_uri`).
4. v1.5 carry: dead `setupMethodFilterButtons` helper + residual `currentMethodFilter` state at `static/js/main.js:384/1613/2603/2814` removed (audit §6.1); WP `/submit` has the defensive `if not mapping_model: return jsonify({"error": ...}), 503` guard added to mirror the GO branch at `api.py:1478` (audit §6.3).

**Plans**: TBD

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Deployment Hardening | v1.0 | 4/4 | Complete | 2026-02-19 |
| 2. Data Model and Audit Trail | v1.0 | 4/4 | Complete | 2026-02-20 |
| 3. Stable Public REST API | v1.0 | 4/4 | Complete | 2026-02-21 |
| 4. Curator UX and Explore | v1.0 | 5/5 | Complete | 2026-02-21 |
| 5. Exports and Dataset Publication | v1.0 | 4/4 | Complete | 2026-02-22 |
| 6. API Documentation | v1.0 | 3/3 | Complete | 2026-02-22 |
| 7. KE-GO Proposal Workflow | v1.0 | 4/4 | Complete | 2026-02-23 |
| 8. Brand Refresh and CSS Cleanup | v1.1 | 5/5 | Complete | 2026-02-24 |
| 9. WikiPathways Embed Viewer | v1.1 | 3/3 | Complete | 2026-03-03 |
| 10. AOP Network Graph | v1.1 | 4/4 | Complete | 2026-03-04 |
| 11. Inline AOP Graph on Mapper Page | v1.1 | 3/3 | Complete | 2026-03-04 |
| 12. Gene Set Visualization on AOP Graph | v1.1 | 3/3 | Complete | 2026-03-04 |
| 13. Low-Risk Foundations | v1.2 | 3/3 | Complete | 2026-03-04 |
| 14. Auth Expansion | v1.2 | 2/2 | Complete | 2026-03-06 |
| 15. GO Hierarchy Integration | v1.2 | 2/2 | Complete | 2026-03-06 |
| 16. API Metadata Capstone | v1.2 | 2/2 | Complete | 2026-03-06 |
| 17. KE Description Toggle | v1.3 | 2/2 | Complete | 2026-03-09 |
| 18. Directionality Detection and Tagging | v1.3 | 3/3 | Complete | 2026-03-10 |
| 19. Structured Three-Dimension Assessment | v1.3 | 3/3 | Complete | 2026-03-10 |
| 20. GO Molecular Function Suggestions | v1.3 | 2/2 | Complete | 2026-03-10 |
| 21. Wire GO Namespace Through Approval Chain | v1.3 | 1/1 | Complete | 2026-03-11 |
| 22. Fix Bulk Export SELECT | v1.3 | 1/1 | Complete | 2026-03-11 |
| 23. Reactome Data Infrastructure | v1.4 | 3/3 | Complete | 2026-04-03 |
| 24. Database Models and Suggestion Service | v1.4 | 2/2 | Complete | 2026-04-29 |
| 25. Proposal Workflow and Admin UI | v1.4 | 6/6 | Complete | 2026-05-05 |
| 26. Public API and Exports | v1.4 | 8/8 | Complete | 2026-05-06 |
| 27. Reactome Pathway Viewer | v1.4 | 4/4 | Complete | 2026-05-06 |
| 28. KE Gene SPARQL Returns Persistent Identifiers | v1.4 | 4/4 | Complete | 2026-05-07 |
| 29. Pure-Semantic Ranking Shift | v1.5 | 6/6 | Complete | 2026-05-10 |
| 30. Reactome Suggestion Card Parity and Threshold Tuning | v1.5 | 2/2 | Complete | 2026-05-10 |
| 31. Reactome Viewer Polish | v1.5 | 3/3 | Complete | 2026-05-11 |
| 32. GO/WP Sibling Debt Sweep | v1.5 | 7/7 | Complete | 2026-05-11 |
| 33. Baseline Cleanup | v1.5 | 3/3 | Complete | 2026-05-11 |
| 34. Assessment Metadata Schema Parity | v1.6 | 4/4 | Complete   | 2026-05-14 |
| 35. Operational + Greenfield Parallel Track | v1.6 | 0/? | Not started | - |
| 36. Renames, Merges, and Naming Sweep | v1.6 | 0/? | Not started | - |
| 37. Backend-Dependent UI — Assessment-Question Sibling Parity | v1.6 | 0/? | Not started | - |
| 38. Admin Click Reduction | v1.6 | 0/? | Not started | - |
| 39. Polish — Mapper Density, Login State, and v1.5 Carry | v1.6 | 0/? | Not started | - |

---

*Last updated: 2026-05-14 — v1.6 User & Admin Experience roadmap added (phases 34–39)*
