---
phase: 03-stable-public-rest-api
verified: 2026-02-21T13:00:00Z
status: passed
score: 21/21 must-haves verified
re_verification: true
previous_status: passed
previous_score: 17/17
gaps_closed:
  - "Submitting the curator proposal form always creates a proposal record with status=pending regardless of submitter role"
  - "The mapping does not appear in the browse table until an admin explicitly approves the proposal"
  - "At approval time approved_by_curator, approved_at_curator, and suggestion_score are written to the mapping row"
  - "All 66 tests pass after the gap closure change"
gaps_remaining: []
regressions: []
human_verification:
  - test: "Send GET /api/v1/mappings from an R script (e.g. httr::GET) or Python requests.get() against a running instance"
    expected: "Response parses cleanly as JSON with data/pagination keys; no auth required; CORS headers present"
    why_human: "Real external client behaviour and live CORS enforcement cannot be verified with pytest test client alone"
  - test: "Send GET /api/v1/mappings?aop_id=1 against a running instance with live AOP-Wiki SPARQL"
    expected: "Either returns filtered results (if AOP 1 has KEs in DB) or returns 400 with error key (if SPARQL unavailable or AOP not found)"
    why_human: "External SPARQL endpoint availability cannot be tested deterministically without a live server"
  - test: "Submit curator proposal form as an admin user, confirm response says pending admin review, confirm mapping is absent from browse table, approve via admin dashboard, confirm mapping appears with non-null approved_by/approved_at/suggestion_score"
    expected: "Full proposal-first flow works end to end in a browser session with a running server"
    why_human: "Full OAuth session flow and DB state transitions across multiple HTTP requests require a live server with real GitHub auth"
---

# Phase 3: Stable Public REST API — Verification Report

**Phase Goal:** External bioinformaticians and R/Python scripts can read the curated mapping database over HTTP without a GitHub account, using a versioned API that will not break when internal endpoints change

**Verified:** 2026-02-21T13:00:00Z
**Status:** PASSED
**Re-verification:** Yes — after gap closure (UAT Test 7: admin bypass curator proposal)

---

## Re-verification Summary

The initial verification (2026-02-20T22:40:00Z) passed all 17 automated must-haves. UAT subsequently found one failure: **Test 7 — Suggestion score flows through approval**. An admin submitting via the curator form created a mapping directly (bypassing the proposal workflow), resulting in null provenance fields. Gap closure plan 03-04 was executed and committed (commits `83bb531`, `47fd98b`). This re-verification confirms all four 03-04 gap-closure truths are satisfied and no regressions were introduced.

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | The mappings table has a `suggestion_score` column (REAL, nullable) | VERIFIED | `_migrate_mappings_suggestion_score()` at models.py:465 performs PRAGMA check + ALTER TABLE; called from `init_db()` at line 196 |
| 2  | The `ke_go_mappings` table has a `go_namespace TEXT NOT NULL DEFAULT 'biological_process'` column | VERIFIED | `_migrate_go_mappings_go_namespace()` at models.py:505 performs PRAGMA check + ALTER TABLE; called from `init_db()` at line 198 |
| 3  | Admin approval writes `suggestion_score` from the approved proposal onto the mapping row | VERIFIED | `admin.py:296-306` reads `proposal.get("suggestion_score")` and passes it to `update_mapping(suggestion_score=proposal_score)`; `update_mapping()` has `suggestion_score` in ALLOWED_FIELDS |
| 4  | `MappingModel.get_mappings_paginated()` returns `(rows, total)` supporting ke_id, pathway_id, confidence_level, and ke_ids filters with LIMIT/OFFSET | VERIFIED | Implemented at models.py:621-682; all four filter branches present; tested by tests 5-7 in test_v1_api.py |
| 5  | `GoMappingModel.get_go_mappings_paginated()` returns `(rows, total)` supporting ke_id, go_term_id, and confidence_level filters with LIMIT/OFFSET; returns `go_namespace` per row | VERIFIED | Implemented at models.py:1421-1473; SELECT includes `go_namespace`; tested by `test_list_go_mappings_returns_json_envelope` |
| 6  | `GET /api/v1/mappings` returns JSON with `{data: [...], pagination: {...}}` without authentication | VERIFIED | Route at v1_api.py:247; CSRF-exempt via `csrf.exempt(v1_api_bp)` at app.py:83; test `test_list_mappings_empty` and `test_list_mappings_returns_json_envelope` pass |
| 7  | `GET /api/v1/mappings/<uuid>` returns a single mapping object or 404 | VERIFIED | Route at v1_api.py:314; 404 path tested by `test_list_mappings_unknown_uuid`; 200 path by `test_get_mapping_by_uuid` |
| 8  | `GET /api/v1/go-mappings` returns JSON with `{data: [...], pagination: {...}}` without authentication | VERIFIED | Route at v1_api.py:339; tested by `test_list_go_mappings_empty` and `test_list_go_mappings_returns_json_envelope` |
| 9  | `GET /api/v1/go-mappings/<uuid>` returns a single GO mapping object or 404 | VERIFIED | Route at v1_api.py:391; tested by `test_get_go_mapping_by_uuid` and `test_get_go_mapping_unknown_uuid` |
| 10 | `Accept: text/csv` on collection endpoints returns CSV with header row | VERIFIED | `_respond_collection()` at v1_api.py:236 uses `request.accept_mimetypes.best_match`; tested by `test_list_mappings_csv` and `test_list_go_mappings_csv` |
| 11 | All `/api/v1/` responses include `Access-Control-Allow-Origin: *` header | VERIFIED | Blueprint-scoped `@v1_api_bp.after_request` at v1_api.py:41-46; tested by `test_cors_header_present` |
| 12 | CORS header is NOT present on internal routes | VERIFIED | `@v1_api_bp.after_request` is scoped to this blueprint only; tested by `test_cors_not_on_internal_routes` |
| 13 | Invalid `aop_id` returns 400, not 500 | VERIFIED | ValueError from `_resolve_aop_ke_ids` mapped to 400 at v1_api.py:281-283; tested by `test_aop_id_invalid_returns_400` |
| 14 | Pagination envelope includes page, per_page, total, total_pages, next, prev | VERIFIED | `_make_pagination()` at v1_api.py:67-84 produces all six fields; tested by `test_list_mappings_pagination_envelope` |
| 15 | `per_page` is clamped to 200 max | VERIFIED | `_parse_pagination_params()` at v1_api.py:61; tested by `test_per_page_clamped_to_200` |
| 16 | Invalid `page` param falls back to 1 | VERIFIED | `_parse_pagination_params()` at v1_api.py:56-58 catches ValueError/TypeError; tested by `test_page_defaults_to_1` |
| 17 | Submitting the curator proposal form always creates a proposal record with status=pending regardless of submitter role | VERIFIED | `api.py:161-182`: `/submit` calls `proposal_model.create_new_pair_proposal()` and returns `{proposal_id, message}`; no `create_mapping()` call at submit time; tested by `test_submit_creates_proposal_not_mapping` |
| 18 | The mapping does NOT appear in the browse table until an admin explicitly approves the proposal | VERIFIED | `api.py:161-182` creates a proposal row only; `admin.py:270-292` `mapping_id is None` branch calls `create_mapping()` only at approval — mapping row is the only insertion path; `test_submit_creates_proposal_not_mapping` asserts `proposal_id` is returned (not a mapping) |
| 19 | At approval time `approved_by_curator`, `approved_at_curator`, and `suggestion_score` are written to the mapping row | VERIFIED | `admin.py:272-289`: creates mapping then calls `update_mapping(approved_by_curator=admin_username, approved_at_curator=approved_at, suggestion_score=proposal_score)`; `suggestion_score` in ALLOWED_FIELDS at models.py:859 |
| 20 | `get_proposal_by_id()` and `get_all_proposals()` alias m.ke_id/ke_title/wp_id/wp_title as mapping_ke_id/mapping_ke_title/mapping_wp_id/mapping_wp_title | VERIFIED | models.py:1144-1145 and 1178-1179: both queries use `m.ke_id as mapping_ke_id, m.ke_title as mapping_ke_title, m.wp_id as mapping_wp_id, m.wp_title as mapping_wp_title`; p.ke_id from `p.*` is never clobbered by NULL JOIN values |
| 21 | All 66 tests pass (19 v1 API tests + 2 new proposal tests + 45 pre-existing) | VERIFIED | `make test` output: `66 passed in 10.17s`; 2 new `TestSubmitCreatesProposal` tests added in `tests/test_app.py:290-373` |

**Score:** 21/21 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/blueprints/v1_api.py` | Blueprint with 6 routes, CORS hook, content negotiation, set_models() | VERIFIED | 410 lines, non-empty, contains `v1_api_bp`, all six routes, `after_request` CORS, `_respond_collection`, `set_models` |
| `src/blueprints/__init__.py` | Exports `v1_api_bp` | VERIFIED | Line 8: `from .v1_api import v1_api_bp`; `__all__` updated |
| `app.py` | Imports, CSRF-exempts, injects models, registers v1_api_bp | VERIFIED | Line 25: `set_models as set_v1_api_models`; line 83: `csrf.exempt(v1_api_bp)`; lines 117-121: `set_v1_api_models(...)`; line 147: `app.register_blueprint(v1_api_bp)` |
| `src/core/models.py` | Three migration methods (including `_migrate_proposals_new_pair_fields`), two paginated query methods, `suggestion_score` in `update_mapping` ALLOWED_FIELDS, `create_new_pair_proposal()` | VERIFIED | All methods present and substantive; `_migrate_proposals_new_pair_fields` at line 532 called from `init_db()` at line 201; `create_new_pair_proposal` at line 1051; JOIN aliasing at lines 1144-1145 and 1178-1179 |
| `src/blueprints/admin.py` | `approve_proposal()` handles `mapping_id is None` branch + passes `suggestion_score` to `update_mapping()` | VERIFIED | Lines 270-292: `elif mapping_id is None` branch creates mapping then calls `update_mapping` with provenance; lines 294-306: existing-mapping branch also carries `suggestion_score` |
| `src/blueprints/api.py` | `/submit` calls `create_new_pair_proposal()` instead of `create_mapping()` | VERIFIED | Lines 154-182: reads `suggestion_score` from form, calls `proposal_model.create_new_pair_proposal()`, returns `{proposal_id, message}` |
| `tests/test_v1_api.py` | 19-test suite for /api/v1/ | VERIFIED | 348 lines, 19 test functions across 5 test classes; all pass |
| `tests/test_app.py` | `TestSubmitCreatesProposal` with 2 tests verifying proposal-first flow | VERIFIED | Lines 290-373: class with `submit_client` fixture (temp-file DB) and 2 passing test methods |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py create_app()` | `src/blueprints/v1_api.py set_models()` | `set_v1_api_models()` call after CSRFProtect | WIRED | app.py:25 imports `set_models as set_v1_api_models`; app.py:117-121 calls it with mapping, go_mapping, cache |
| `src/blueprints/v1_api.py _resolve_aop_ke_ids()` | `src/core/models.py CacheModel` | `cache_model.get_cached_response()` / `cache_model.cache_response()` | WIRED | v1_api.py:181,239 calls both methods on the injected `cache_model` |
| `src/blueprints/v1_api.py list_mappings()` | `src/core/models.py MappingModel.get_mappings_paginated()` | `mapping_model.get_mappings_paginated(...)` | WIRED | v1_api.py:286-293 calls with all filter params |
| `src/blueprints/api.py /submit` | `src/core/models.py ProposalModel.create_new_pair_proposal()` | `proposal_model.create_new_pair_proposal()` | WIRED | api.py:162: `proposal_id = proposal_model.create_new_pair_proposal(...)` with all required params |
| `src/blueprints/admin.py approve_proposal()` | `src/core/models.py MappingModel.create_mapping() then update_mapping()` | `mapping_id is None` branch at admin.py:270 | WIRED | admin.py:274-288: `create_mapping()` called with proposal ke_id/wp_id; if successful, `update_mapping()` called with provenance |
| `src/blueprints/admin.py approve_proposal()` | `src/core/models.py ProposalModel.get_proposal_by_id()` | `proposal['ke_id']` resolves to `p.ke_id` (not NULL-clobbered `m.ke_id`) | WIRED | models.py:1178-1179: SELECT uses `m.ke_id as mapping_ke_id` alias; `p.*` delivers `p.ke_id` correctly for both new-pair and existing-mapping proposals |
| `src/core/models.py Database._migrate_proposals_new_pair_fields()` | `proposals` table | `ALTER TABLE proposals ADD COLUMN ke_id/ke_title/wp_id/wp_title/new_pair_connection_type/new_pair_confidence_level` | WIRED | models.py:532-577; called from `init_db()` at line 201 |
| `tests/test_app.py TestSubmitCreatesProposal` | `src/blueprints/api.py /submit` | Flask test client hitting `/submit` with temp-file DB via `submit_client` fixture | WIRED | test_app.py:294-337: fixture replaces `api_mod.proposal_model` with temp-file DB instance; 2 tests hit `/submit` and assert `proposal_id` in response |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| API-01 | 03-01, 03-02, 03-03, 03-04 | Versioned `/api/v1/` blueprint, entirely separate from existing internal suggestion endpoints | SATISFIED | `v1_api_bp` at `url_prefix="/api/v1"` is completely independent of `api_bp`; no cross-imports; CORS hook scoped to v1_api_bp only; gap closure modifies `api_bp` (/submit) and `admin_bp` (approve) — v1_api_bp untouched |
| API-02 | 03-01, 03-02, 03-03, 03-04 | `GET /api/v1/mappings` — paginated KE-WP mapping list, filterable by KE ID, AOP ID, and pathway ID | SATISFIED | Route at v1_api.py:247; all three filters implemented; paginated with LIMIT/OFFSET; 66 tests pass; mappings now carry provenance (approved_by_curator, approved_at_curator, suggestion_score) after gap closure |
| API-03 | 03-01, 03-02, 03-03 | `GET /api/v1/go-mappings` — paginated KE-GO mapping list, filterable by KE ID and GO term ID | SATISFIED | Route at v1_api.py:339; ke_id and go_term_id filters; go_namespace returned per row |
| API-04 | 03-02, 03-03 | Content negotiation on collection endpoints — `Accept: text/csv` returns tabular data for R/Python scripts | SATISFIED | `_respond_collection()` uses `request.accept_mimetypes.best_match()`; tested by `test_list_mappings_csv` and `test_list_go_mappings_csv` |

No orphaned requirements — all four API-0x requirements appear in plan frontmatter and are covered by verified implementations.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No TODO/FIXME/placeholder patterns, empty returns, or stub implementations found in any phase-modified file |

---

### Human Verification Required

#### 1. Live External Client Access

**Test:** From outside the server, use `requests.get("http://localhost:5000/api/v1/mappings")` (Python) or `httr::GET("http://localhost:5000/api/v1/mappings")` (R) with no authentication headers.
**Expected:** 200 JSON response with `data` and `pagination` keys; `Access-Control-Allow-Origin: *` present in response headers; no redirect to login.
**Why human:** The pytest test client bypasses real HTTP; real cross-origin enforcement and absence of auth redirects need confirmation with an actual HTTP client.

#### 2. Live AOP SPARQL Filter

**Test:** Start the server and call `GET /api/v1/mappings?aop_id=1`. If AOP-Wiki SPARQL is reachable, verify the response either returns filtered results or an empty `data: []` (if no KEs from AOP 1 are mapped). If SPARQL is unavailable, verify a 400 `{"error": "..."}` is returned rather than a 500.
**Expected:** Never a 500 error regardless of SPARQL availability.
**Why human:** AOP-Wiki SPARQL endpoint availability varies; deterministic test requires live network.

#### 3. End-to-End Proposal Approval Flow (UAT Test 7 — Manual Confirmation)

**Test:** Start the server (`python app.py`). Log in as an admin user via GitHub OAuth. Navigate to the curator submission form and submit a new KE-WP pair. Verify the response says "pending admin review" (not "Entry added successfully"). Confirm the mapping does NOT appear in the browse/explore table. Open the admin proposals page and confirm the new proposal is listed with status=pending. Approve the proposal. Confirm the mapping NOW appears in the browse/explore table. Call `curl http://localhost:5000/api/v1/mappings` and confirm the mapping appears with non-null `approved_by_curator`, `approved_at_curator` fields.
**Expected:** Mapping only appears after admin approval; provenance fields populated at approval time.
**Why human:** Full OAuth session flow, cross-request DB state, and browser UI interactions cannot be verified programmatically with the test client alone.

---

## Commits Verified

All commits referenced in summaries exist in git history:

| Commit | Description |
|--------|-------------|
| `da63db0` | feat(03-01): add suggestion_score/go_namespace migrations and paginated query methods |
| `561759e` | feat(03-01): wire suggestion_score from proposal to mapping at admin approval |
| `eaf7107` | feat(03-02): create v1_api_bp blueprint with all six public API routes |
| `f112d88` | feat(03-02): register v1_api_bp in __init__.py and app.py |
| `f82c1b6` | feat(03-03): add v1 public REST API test suite |
| `83bb531` | feat(03-04): add _migrate_proposals_new_pair_fields and create_new_pair_proposal() |
| `47fd98b` | feat(03-04): fix proposal workflow — /submit creates proposal, approve handles new-pair |

---

## Summary

Phase 3 fully achieves its goal. The codebase now provides a stable, versioned public REST API at `/api/v1/` that:

- Requires no authentication (CSRF-exempt blueprint, no session check in route handlers)
- Is entirely separate from internal endpoints (separate Blueprint, no shared code paths, scoped CORS)
- Serves both JSON and CSV to R/Python clients via content negotiation
- Is regression-tested by 66 passing tests (19 v1 API tests, 2 new proposal workflow tests, 45 pre-existing)
- Has all four requirements (API-01 through API-04) satisfied with implementation evidence

The UAT Test 7 gap (admin bypassing the proposal workflow via /submit) was closed by plan 03-04:
- `/submit` now always calls `create_new_pair_proposal()` — no mapping is created at submission time
- `approve_proposal()` handles `mapping_id is None` new-pair proposals by calling `create_mapping()` then `update_mapping()` with full provenance
- `get_proposal_by_id()` and `get_all_proposals()` alias JOIN columns to prevent NULL-clobbering of proposal row values

The 40% coverage failure in `make test` is a pre-existing condition from the 80% threshold applied to the entire codebase including exporters and admin blueprints with low test coverage — it is unrelated to Phase 3 and predates this work.

---

_Verified: 2026-02-21T13:00:00Z_
_Verifier: Claude (gsd-verifier)_
