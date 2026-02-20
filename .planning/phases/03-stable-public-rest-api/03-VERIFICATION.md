---
phase: 03-stable-public-rest-api
verified: 2026-02-20T22:40:00Z
status: passed
score: 17/17 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Send GET /api/v1/mappings from an R script (e.g. httr::GET) or Python requests.get() against a running instance"
    expected: "Response parses cleanly as JSON with data/pagination keys; no auth required; CORS headers present"
    why_human: "Real external client behaviour and live CORS enforcement cannot be verified with pytest test client alone"
  - test: "Send GET /api/v1/mappings?aop_id=1 against a running instance with live AOP-Wiki SPARQL"
    expected: "Either returns filtered results (if AOP 1 has KEs in DB) or returns 400 with error key (if SPARQL unavailable or AOP not found)"
    why_human: "External SPARQL endpoint availability cannot be tested deterministically without a live server"
---

# Phase 3: Stable Public REST API — Verification Report

**Phase Goal:** External bioinformaticians and R/Python scripts can read the curated mapping database over HTTP without a GitHub account, using a versioned API that will not break when internal endpoints change

**Verified:** 2026-02-20T22:40:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | The mappings table has a `suggestion_score` column (REAL, nullable) | VERIFIED | `_migrate_mappings_suggestion_score()` at models.py:465 performs PRAGMA check + ALTER TABLE; called from `init_db()` at line 196 |
| 2  | The `ke_go_mappings` table has a `go_namespace TEXT NOT NULL DEFAULT 'biological_process'` column | VERIFIED | `_migrate_go_mappings_go_namespace()` at models.py:505 performs PRAGMA check + ALTER TABLE with correct DDL; called from `init_db()` at line 198 |
| 3  | Admin approval writes `suggestion_score` from the approved proposal onto the mapping row | VERIFIED | `admin.py:273-281` reads `proposal.get("suggestion_score")` and passes it to `update_mapping(suggestion_score=proposal_score)`; `update_mapping()` has `suggestion_score` in ALLOWED_FIELDS at models.py:859 |
| 4  | `MappingModel.get_mappings_paginated()` returns `(rows, total)` supporting ke_id, pathway_id, confidence_level, and ke_ids filters with LIMIT/OFFSET | VERIFIED | Implemented at models.py:621-682; all four filter branches present; tested by tests 5-7 in test_v1_api.py |
| 5  | `GoMappingModel.get_go_mappings_paginated()` returns `(rows, total)` supporting ke_id, go_term_id, and confidence_level filters with LIMIT/OFFSET; returns `go_namespace` per row | VERIFIED | Implemented at models.py:1421-1473; SELECT includes `go_namespace`; tested by `test_list_go_mappings_returns_json_envelope` |
| 6  | `GET /api/v1/mappings` returns JSON with `{data: [...], pagination: {...}}` without authentication | VERIFIED | Route at v1_api.py:247; CSRF-exempt via `csrf.exempt(v1_api_bp)` at app.py:83; test `test_list_mappings_empty` and `test_list_mappings_returns_json_envelope` pass |
| 7  | `GET /api/v1/mappings/<uuid>` returns a single mapping object or 404 | VERIFIED | Route at v1_api.py:314; 404 path tested by `test_list_mappings_unknown_uuid`; 200 path by `test_get_mapping_by_uuid` |
| 8  | `GET /api/v1/go-mappings` returns JSON with `{data: [...], pagination: {...}}` without authentication | VERIFIED | Route at v1_api.py:339; tested by `test_list_go_mappings_empty` and `test_list_go_mappings_returns_json_envelope` |
| 9  | `GET /api/v1/go-mappings/<uuid>` returns a single GO mapping object or 404 | VERIFIED | Route at v1_api.py:391; tested by `test_get_go_mapping_by_uuid` and `test_get_go_mapping_unknown_uuid` |
| 10 | `Accept: text/csv` on collection endpoints returns CSV with header row | VERIFIED | `_respond_collection()` at v1_api.py:236 uses `request.accept_mimetypes.best_match`; tested by `test_list_mappings_csv` and `test_list_go_mappings_csv` — both assert `Content-Type: text/csv` and `uuid` in first line |
| 11 | All `/api/v1/` responses include `Access-Control-Allow-Origin: *` header | VERIFIED | Blueprint-scoped `@v1_api_bp.after_request` at v1_api.py:41-46; tested by `test_cors_header_present` |
| 12 | CORS header is NOT present on internal routes | VERIFIED | `@v1_api_bp.after_request` is scoped to this blueprint only; tested by `test_cors_not_on_internal_routes` asserting `Access-Control-Allow-Origin` absent on `/check` |
| 13 | Invalid `aop_id` returns 400, not 500 | VERIFIED | ValueError from `_resolve_aop_ke_ids` mapped to 400 at v1_api.py:281-283; tested by `test_aop_id_invalid_returns_400` via monkeypatch |
| 14 | Pagination envelope includes page, per_page, total, total_pages, next, prev | VERIFIED | `_make_pagination()` at v1_api.py:67-84 produces all six fields; tested by `test_list_mappings_pagination_envelope` |
| 15 | `per_page` is clamped to 200 max | VERIFIED | `_parse_pagination_params()` at v1_api.py:61; tested by `test_per_page_clamped_to_200` |
| 16 | Invalid `page` param falls back to 1 | VERIFIED | `_parse_pagination_params()` at v1_api.py:56-58 catches ValueError/TypeError; tested by `test_page_defaults_to_1` |
| 17 | All 64 tests pass (19 new v1 API tests + 45 pre-existing) | VERIFIED | `make test` output: `64 passed in 9.84s` |

**Score:** 17/17 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/blueprints/v1_api.py` | Blueprint with 6 routes, CORS hook, content negotiation, set_models() | VERIFIED | 410 lines, non-empty, contains `v1_api_bp`, all six routes, `after_request` CORS, `_respond_collection`, `set_models` |
| `src/blueprints/__init__.py` | Exports `v1_api_bp` | VERIFIED | Line 8: `from .v1_api import v1_api_bp`; `__all__` updated |
| `app.py` | Imports, CSRF-exempts, injects models, registers v1_api_bp | VERIFIED | Line 25: `set_models as set_v1_api_models`; line 83: `csrf.exempt(v1_api_bp)`; lines 117-121: `set_v1_api_models(...)`; line 147: `app.register_blueprint(v1_api_bp)` |
| `src/core/models.py` | Three migration methods, two paginated query methods, `suggestion_score` in `update_mapping` ALLOWED_FIELDS | VERIFIED | All methods present and substantive; `suggestion_score: "suggestion_score"` in ALLOWED_FIELDS at line 859 |
| `src/blueprints/admin.py` | `approve_proposal()` passes `suggestion_score` to `update_mapping()` | VERIFIED | Lines 273-281: reads `proposal.get("suggestion_score")`, passes as kwarg |
| `tests/test_v1_api.py` | 19-test suite for /api/v1/ | VERIFIED | 348 lines, 19 test functions across 5 test classes; uses `v1_client` fixture with per-test temp-file DB |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py create_app()` | `src/blueprints/v1_api.py set_models()` | `set_v1_api_models()` call after CSRFProtect | WIRED | app.py:25 imports `set_models as set_v1_api_models`; app.py:117-121 calls it with mapping, go_mapping, cache |
| `src/blueprints/v1_api.py _resolve_aop_ke_ids()` | `src/core/models.py CacheModel` | `cache_model.get_cached_response()` / `cache_model.cache_response()` | WIRED | v1_api.py:181,239 calls both methods on the injected `cache_model` |
| `src/blueprints/v1_api.py list_mappings()` | `src/core/models.py MappingModel.get_mappings_paginated()` | `mapping_model.get_mappings_paginated(...)` | WIRED | v1_api.py:286-293 calls with all filter params |
| `src/blueprints/admin.py approve_proposal()` | `src/core/models.py MappingModel.update_mapping()` | `suggestion_score` kwarg passed at approval time | WIRED | admin.py:274-281; `suggestion_score` in ALLOWED_FIELDS at models.py:859 |
| `src/core/models.py Database._migrate_mappings_suggestion_score()` | `mappings` table | `ALTER TABLE mappings ADD COLUMN suggestion_score REAL` | WIRED | models.py:477; called from `init_db()` at line 196 |
| `tests/test_v1_api.py` | `src/blueprints/v1_api.py` | Flask test client hitting `/api/v1/` routes | WIRED | test_v1_api.py imports `v1_mod` and uses `v1_client` fixture to hit live routes |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| API-01 | 03-01, 03-02, 03-03 | Versioned `/api/v1/` blueprint, entirely separate from existing internal suggestion endpoints | SATISFIED | `v1_api_bp` at `url_prefix="/api/v1"` is completely independent of `api_bp`; no cross-imports; CORS hook scoped to v1_api_bp only |
| API-02 | 03-01, 03-02, 03-03 | `GET /api/v1/mappings` — paginated KE-WP mapping list, filterable by KE ID, AOP ID, and pathway ID | SATISFIED | Route at v1_api.py:247; all three filters implemented; paginated with LIMIT/OFFSET; 64 tests pass |
| API-03 | 03-01, 03-02, 03-03 | `GET /api/v1/go-mappings` — paginated KE-GO mapping list, filterable by KE ID and GO term ID | SATISFIED | Route at v1_api.py:339; ke_id and go_term_id filters; go_namespace returned per row |
| API-04 | 03-02, 03-03 | Content negotiation on collection endpoints — `Accept: text/csv` returns tabular data for R/Python scripts | SATISFIED | `_respond_collection()` uses `request.accept_mimetypes.best_match()`; tested by `test_list_mappings_csv` and `test_list_go_mappings_csv` |

No orphaned requirements — all four API-0x requirements appear in plan frontmatter and are covered by verified implementations.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No TODO/FIXME/placeholder patterns, empty returns, or stub implementations found in phase-modified files |

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

---

## Commits Verified

All five commits referenced in summaries exist in git history:

| Commit | Description |
|--------|-------------|
| `da63db0` | feat(03-01): add suggestion_score/go_namespace migrations and paginated query methods |
| `561759e` | feat(03-01): wire suggestion_score from proposal to mapping at admin approval |
| `eaf7107` | feat(03-02): create v1_api_bp blueprint with all six public API routes |
| `f112d88` | feat(03-02): register v1_api_bp in __init__.py and app.py |
| `f82c1b6` | feat(03-03): add v1 public REST API test suite |

---

## Summary

Phase 3 fully achieves its goal. The codebase now provides a stable, versioned public REST API at `/api/v1/` that:

- Requires no authentication (CSRF-exempt blueprint, no session check in route handlers)
- Is entirely separate from internal endpoints (separate Blueprint, no shared code paths, scoped CORS)
- Serves both JSON and CSV to R/Python clients via content negotiation
- Is regression-tested by 19 passing integration tests covering all contract-required behaviors
- Has all four requirements (API-01 through API-04) satisfied with implementation evidence

The 40% coverage failure in `make test` is a pre-existing condition from the 80% threshold applied to the entire codebase including exporters and admin blueprints with low test coverage — it is unrelated to Phase 3 and predates this work (noted in the 03-01 and 03-02 summaries).

---

_Verified: 2026-02-20T22:40:00Z_
_Verifier: Claude (gsd-verifier)_
