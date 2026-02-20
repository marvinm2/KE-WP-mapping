---
phase: 02-data-model-and-audit-trail
verified: 2026-02-20T15:30:00Z
status: passed
score: 16/16 must-haves verified
re_verification: false
---

# Phase 2: Data Model and Audit Trail — Verification Report

**Phase Goal:** Every mapping carries complete provenance — who approved it, when, at what confidence, with what suggestion score — and every mapping has a stable identifier that will not change after publication
**Verified:** 2026-02-20T15:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Starting the app against an existing database adds new columns without error and without losing existing rows | VERIFIED | `init_db()` calls all four migration methods; each checks PRAGMA table_info before altering; test confirmed idempotent on second Database() call |
| 2 | Every row in mappings and ke_go_mappings has a non-null uuid after migration runs | VERIFIED | `_migrate_mappings_uuid_and_provenance` and `_migrate_go_mappings_uuid_and_provenance` both run SQLite randomblob() backfill WHERE uuid IS NULL; unique indexes created |
| 3 | New columns approved_by_curator, approved_at_curator exist on both mapping tables | VERIFIED | Runtime check confirmed both columns in `mappings` and `ke_go_mappings` PRAGMA table_info output |
| 4 | New columns uuid, suggestion_score, is_stale exist on both proposal tables | VERIFIED | Runtime check confirmed all three columns in `proposals` and `ke_go_proposals` PRAGMA table_info output |
| 5 | Admin approving a KE-WP proposal writes curator GitHub username and ISO timestamp into approved_by_curator and approved_at_curator on the mapping row | VERIFIED | `admin.py` approve_proposal() at lines 272–280: `approved_at = datetime.utcnow().isoformat()` then `mapping_model.update_mapping(..., approved_by_curator=admin_username, approved_at_curator=approved_at)` |
| 6 | POST /check with an existing approved KE-WP pair returns blocking_type=approved_mapping plus existing object and actions=[submit_revision] | VERIFIED | Runtime test returned `{'blocking_type': 'approved_mapping', 'existing': {..., 'uuid': '...', 'approved_by_curator': None, ...}, 'actions': ['submit_revision']}`; `api.py` line 104 calls `check_mapping_exists_with_proposals` |
| 7 | POST /check with a pending proposal for the same KE-WP pair returns blocking_type=pending_proposal plus existing object and actions=[flag_stale] | VERIFIED | Runtime test returned `{'blocking_type': 'pending_proposal', 'actions': ['flag_stale']}`; pending proposals take priority over approved mappings |
| 8 | POST /check_go_entry returns the same enriched structure for KE-GO pairs | VERIFIED | `api.py` line 1315 calls `check_go_mapping_exists_with_proposals`; runtime test returned `approved_mapping` blocking type with uuid for GO pair |
| 9 | POST /flag_proposal_stale sets is_stale=True on a proposals row; authenticated curators can call it; returns 200 JSON | VERIFIED | `api.py` lines 1325–1353: endpoint exists with `@login_required`, `@submission_rate_limit`; runtime test confirmed `is_stale=1` set in database |
| 10 | Submitting /submit without confidence_level returns 400 (server-side enforcement) | VERIFIED | `MappingSchema` validated — `MappingSchema().load({...without confidence_level...})` raises `ValidationError: {'confidence_level': [...]}`; `api.py` returns 400 on schema failure |
| 11 | Every new KE-WP and KE-GO proposal row has a non-null UUID4 string generated at insert time | VERIFIED | `ProposalModel.create_proposal()` generates `proposal_uuid = str(uuid_lib.uuid4())` at line 827; `GoProposalModel.create_proposal()` same at line 1302; runtime confirmed 36-char UUIDs in both tables |
| 12 | After selecting a KE and a pathway, a live check fires and shows a duplicate warning card if the pair already exists | VERIFIED | `main.js` `checkForDuplicatePair()` at line 2760 fires on pathway selection events (lines 1290, 2745, 3102); calls `$.post('/check', ...)` |
| 13 | The duplicate warning card shows a Flag as Stale button calling /flag_proposal_stale and a Submit Revision button for approved mappings | VERIFIED | `renderDuplicateWarning()` at line 2774 renders both card variants; flag-stale button calls `$.post('/flag_proposal_stale', ...)` at line 2806; `renderDuplicateWarning_go()` at line 2833 mirrors for GO form |
| 14 | The confidence level step appears as a required selection before mapping can be submitted; UI blocks submission without selection | VERIFIED | `index.html` lines 192–207: `#confidence-confirm` section with `#confidence-select-group`; `main.js` submit guard checks `$('#confidence_level').val()`; `#confidence-select-error` shown on missing value |
| 15 | The browse table on /explore shows Curator and Approved columns with provenance data; legacy mappings use fallback | VERIFIED | `explore.html` lines 51–52: `<th>Curator</th><th>Approved</th>`; lines 65–66: `{{ row['approved_by_curator'] or row['created_by'] or '—' }}` and `{{ (row['approved_at_curator'] or row['created_at'] or '').split('T')[0].split(' ')[0] }}`; uuid NOT in explore table |
| 16 | Visiting /mappings/<uuid> returns a mapping detail page with all provenance fields; unknown UUID returns 404 | VERIFIED | `main.py` lines 457–463: `mapping_detail()` route calls `get_mapping_by_uuid()`, aborts 404 on None; `mapping_detail.html` renders all provenance fields including UUID, Curator, Approved; back link to /explore |

**Score:** 16/16 truths verified

---

## Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `src/core/models.py` | 4 migration methods + UUID in create_mapping + check_mapping_exists_with_proposals + get_mapping_by_uuid | VERIFIED | All migration methods present (lines 265–458); `uuid_lib.uuid4()` called in both `MappingModel.create_mapping()` (line 476) and `GoMappingModel.create_mapping()` (line 1051) and both proposal create methods (lines 827, 1302); enriched check methods at lines 595 and 1165; `get_mapping_by_uuid` at line 767; `get_go_mapping_by_uuid` at line 1266 |
| `src/blueprints/api.py` | /check enriched, /check_go_entry enriched, /flag_proposal_stale endpoint | VERIFIED | `check_entry()` calls `check_mapping_exists_with_proposals` (line 104); `check_go_entry()` calls `check_go_mapping_exists_with_proposals` (line 1315); `flag_proposal_stale()` endpoint at lines 1325–1353 |
| `src/blueprints/admin.py` | approve_proposal writes approved_by_curator/approved_at_curator | VERIFIED | Lines 272–280: `approved_at = datetime.utcnow().isoformat()` then `update_mapping(..., approved_by_curator=admin_username, approved_at_curator=approved_at)` |
| `src/core/schemas.py` | MappingSchema confidence_level required=True | VERIFIED | Runtime validation test confirmed `ValidationError` raised for missing `confidence_level` |
| `templates/index.html` | Confidence select-button group, suggestion_score hidden field, duplicate-warning divs | VERIFIED | Lines 139, 177, 192–207, 218: all five elements present (`#duplicate-warning`, `#suggestion_score`, `#confidence-confirm`, `#confidence-select-group`, `#duplicate-warning-go`) |
| `static/js/main.js` | Live duplicate check, GO duplicate check, inline warning cards, stale-flag CTAs, confidence enforcement, suggestion_score capture | VERIFIED | `checkForDuplicatePair` at line 2760; `checkForDuplicatePair_go` at line 2819; `renderDuplicateWarning` at line 2774; `renderDuplicateWarning_go` at line 2833; `flag_proposal_stale` calls at lines 2806, 2865; `data-score` attribute added to suggestion-item HTML at line 2220; `$('#suggestion_score').val(score)` at line 2726 |
| `templates/explore.html` | Curator + Approved columns replacing Timestamp; no UUID column | VERIFIED | `<th>Curator</th><th>Approved</th>` at lines 51–52; fallback chain at lines 65–66; grep for "uuid" returns no table column matches |
| `templates/admin_proposals.html` | suggestion_score and UUID in admin proposal detail modal | VERIFIED | Lines 306–307: `suggestion_score.toFixed(3)` and `proposal.uuid` rendered in admin modal JavaScript |
| `src/blueprints/main.py` | /mappings/<uuid> detail route + abort(404) | VERIFIED | Lines 457–463: `@main_bp.route("/mappings/<string:mapping_uuid>")` with `abort(404)` on None result |
| `templates/mapping_detail.html` | Standalone page showing all provenance fields + UUID | VERIFIED | File exists; shows ke_id, ke_title, wp_id, wp_title, connection_type, confidence_level, Curator (with fallback), Approved (with fallback), UUID; back link to /explore |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `Database.init_db()` | All four migration methods | Explicit method calls before conn.commit() | WIRED | Lines 188–193 in `models.py`: `self._migrate_mappings_uuid_and_provenance(conn)`, `self._migrate_go_mappings_uuid_and_provenance(conn)`, `self._migrate_proposals_phase2_fields(conn)`, `self._migrate_go_proposals_phase2_fields(conn)` |
| `MappingModel.create_mapping()` | uuid column in INSERT | `str(uuid_lib.uuid4())` | WIRED | Line 476: `mapping_uuid = str(uuid_lib.uuid4())`; included in INSERT at line 482 |
| `GoMappingModel.create_mapping()` | uuid column in INSERT | `str(uuid_lib.uuid4())` | WIRED | Line 1051: `mapping_uuid = str(uuid_lib.uuid4())`; included in INSERT at line 1057 |
| `admin.py approve_proposal()` | `update_mapping(approved_by_curator=..., approved_at_curator=...)` | `admin_username` from session, `datetime.utcnow().isoformat()` | WIRED | Lines 272–280: `approved_at = datetime.utcnow().isoformat()` then `mapping_model.update_mapping(..., approved_by_curator=admin_username, approved_at_curator=approved_at)` |
| `api.py /check` | `check_mapping_exists_with_proposals()` | Direct method call replacing old `check_mapping_exists()` | WIRED | Line 104: `result = mapping_model.check_mapping_exists_with_proposals(ke_id, wp_id)` |
| `api.py /check_go_entry` | `check_go_mapping_exists_with_proposals()` | Direct method call | WIRED | Line 1315: `result = go_mapping_model.check_go_mapping_exists_with_proposals(...)` |
| `api.py /flag_proposal_stale` | `UPDATE proposals SET is_stale=1` | `proposal_model.flag_proposal_stale()` or `go_proposal_model.flag_go_proposal_stale()` | WIRED | Lines 1342–1344: delegates to correct model based on `mapping_type` param |
| `main.js pathway selection event` | POST /check | `setTimeout(() => this.checkForDuplicatePair(), 100)` | WIRED | Lines 1290, 2745, 3102: timeout fires check after each pathway selection event |
| `duplicate warning card flag-stale button` | POST /flag_proposal_stale | `$.post('/flag_proposal_stale', {proposal_id, mapping_type})` | WIRED | Line 2806: delegated click handler on `.btn-flag-stale`; line 2865: same in GO version |
| `main.js GO term selection event` | POST /check_go_entry | `this.checkForDuplicatePair_go()` | WIRED | Line 3843: `selectGoTerm()` calls `this.checkForDuplicatePair_go()` |
| `suggestion card click handler` | hidden input #suggestion_score | `$('#suggestion_score').val(score)` | WIRED | Line 2726: score captured from `data-score` attribute; attribute added to suggestion-item HTML at line 2220 |
| `confidence select-button group` | hidden input #confidence_level | `btn-option click sets #confidence_level value` | WIRED | `main.js` syncs `#confidence_level` from btn-option data-value on click; verified by pattern at lines 196–207 in index.html |
| `templates/explore.html` | `row['approved_by_curator']` and `row['approved_at_curator']` | Jinja2 template with fallback chain | WIRED | Lines 65–66: `{{ row['approved_by_curator'] or row['created_by'] or '—' }}` and date split logic |
| `main.py /mappings/<uuid>` | `MappingModel.get_mapping_by_uuid(uuid)` | Route parameter mapped to model query | WIRED | Line 460: `mapping = mapping_model.get_mapping_by_uuid(mapping_uuid)` |

---

## Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| CURAT-01 | 02-01, 02-02, 02-04 | Each approved mapping records the approving curator and timestamp (provenance/audit trail) | SATISFIED | `approved_by_curator` and `approved_at_curator` columns migrated (02-01); written at approval time in `admin.py` (02-02); displayed in explore table with fallback and in `mapping_detail.html` (02-04) |
| CURAT-02 | 02-02, 02-03 | Duplicate mapping detection prevents submitting the same KE→pathway or KE→GO pair twice | SATISFIED | Enriched `/check` and `/check_go_entry` endpoints return `blocking_type` + `actions` (02-02); live duplicate check fires on field selection with inline warning cards (02-03) |
| CURAT-03 | 02-01, 02-02, 02-03 | Confidence level stored with each approved mapping and visible in browse table | SATISFIED | `confidence_level` column already present; `MappingSchema` enforces required=True server-side (02-02); confidence select-button group adds UI enforcement and `suggestion_score` captured (02-03) |
| EXPLO-04 | 02-01, 02-04 | All API and explore-page responses include stable, permanent mapping IDs | SATISFIED | UUID column added to mappings + ke_go_mappings with unique index and backfill (02-01); `/mappings/<uuid>` stable detail route returns 404 for unknown UUIDs; `get_mapping_by_uuid()` model method (02-04) |

No orphaned requirements found — all four IDs declared in plan frontmatter are accounted for, and REQUIREMENTS.md traceability table maps exactly CURAT-01, CURAT-02, CURAT-03, EXPLO-04 to Phase 2.

---

## Anti-Patterns Found

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| `templates/explore.html` lines 117, 120, 123 | `placeholder=` attribute in `<input>` elements | Info | HTML form field hint text, not code stubs. Proposal modal fields for curator name/email/affiliation. Not a phase 2 concern. |

No blockers or warnings found in phase 2 modified files. No TODO/FIXME/HACK markers. No empty implementations. No stub return patterns.

---

## Human Verification Required

### 1. Curator Provenance Visible After Approval

**Test:** Log in as admin, approve a pending proposal, then visit `/explore` and `/mappings/<uuid>`.
**Expected:** The Curator column shows the admin's GitHub username; the Approved column shows today's date.
**Why human:** Requires an active session, admin credentials, and a pending proposal row in the production database.

### 2. Live Duplicate Check Fires on Pathway Selection

**Test:** Log in as a curator on `/`, select a KE, then select a pathway already in the database from the suggestion cards or browse panel.
**Expected:** The `#duplicate-warning` div appears below the pathway selection with the existing mapping details and a "Submit Revision Proposal" button.
**Why human:** Browser interaction required; jQuery AJAX timing (100ms setTimeout) and DOM mutation cannot be verified programmatically.

### 3. Flag as Stale Flow

**Test:** Find a KE-WP pair that has a pending proposal (not yet approved). Select it in the submission form. Confirm the warning card shows "Flag as Stale for Admin Review" button. Click it.
**Expected:** Button changes to "Flagged — admin has been notified"; `is_stale=1` set in database.
**Why human:** Requires an active pending proposal in the database and browser interaction.

### 4. Confidence Select Step UX

**Test:** Complete the 4-question assessment for a new KE-WP pair. Confirm the `#confidence-confirm` section appears with the recommended level pre-selected. Clear the selection and try to submit.
**Expected:** `#confidence-select-error` message appears inline; form does not submit.
**Why human:** Multi-step browser interaction with jQuery-driven show/hide logic.

### 5. /mappings/<uuid> Returns 404 for Unknown UUID

**Test:** Visit `http://localhost:5000/mappings/00000000-0000-0000-0000-000000000000`.
**Expected:** 404 page (rendered by Flask error handler).
**Why human:** Requires the server running; 404 rendering depends on Flask error handler template wiring.

---

## Gaps Summary

No gaps found. All 16 observable truths are verified. All required artifacts exist, are substantive (not stubs), and are wired. All four requirement IDs are satisfied with implementation evidence. All key links are traced end-to-end.

The phase goal is achieved: every mapping carries complete provenance (approved_by_curator, approved_at_curator, confidence_level, suggestion_score) and every mapping has a stable UUID identifier at `/mappings/<uuid>` that will not change after publication.

---

_Verified: 2026-02-20T15:30:00Z_
_Verifier: Claude (gsd-verifier)_
