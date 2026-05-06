---
phase: 26-public-api-and-exports
plan: "05"
subsystem: public-api
tags: [reactome, v1-api, flask-blueprint, pagination, aop-filter, csv-export]

requires:
  - phase: 26-public-api-and-exports
    plan: "02"
    provides: ReactomeMappingModel.get_reactome_mappings_paginated(...) and .get_reactome_mapping_by_uuid(...) — 11-column SELECT contract consumed by the new serializer
  - phase: 24-database-models-and-suggestion-service
    provides: ServiceContainer.reactome_mapping_model (already wired, used by app.py at startup)
provides:
  - GET /api/v1/reactome-mappings (paginated, JSON+CSV, filters ke_id/reactome_id/confidence_level/aop_id)
  - GET /api/v1/reactome-mappings/<uuid> (single mapping by stable UUID, 404 with descriptive error)
  - _serialize_reactome_mapping (transform DB row -> v1 mapping object per D-05)
  - _REACTOME_MAPPING_CSV_FIELDS (15-field CSV header order per D-05/D-56)
  - Extended set_models() signature with reactome_mapping/reactome_meta/reactome_counts kwargs
  - Reactome metadata + gene-count loaders in app.py (graceful fallback to {} on missing JSON)
affects: [26-06-explore-tab, 26-07-rdf-export, 26-08-tests-and-docs]

tech-stack:
  added: []
  patterns:
    - "v1 API list+detail route pair: clones list_go_mappings/get_go_mappings 1:1 with field swaps and AOP filter added (one-line WP-pattern departure per D-08)"
    - "Module-level globals + set_models() injection — extended for the third mapping type without disturbing existing wiring"
    - "_resolve_aop_ke_ids reused as a callable; no extraction or refactor (mirror Pattern 4)"
    - "_flatten_for_csv reused as-is — Reactome rows share the provenance/ke_aop_context shape"
    - "Startup-time JSON load with graceful fallback ({} on OSError/JSONDecodeError); per-row serialization stays O(1)"

key-files:
  created:
    - tests/test_v1_api_reactome.py
  modified:
    - src/blueprints/v1_api.py
    - app.py

key-decisions:
  - "Avoid global/local shadowing in set_models() by renaming kwargs (reactome_meta, reactome_counts) instead of matching the global names — keeps the natural global names (reactome_metadata, reactome_gene_counts) for the serializer to read"
  - "AOP filter mirrors WP, not GO (D-08): added to Reactome route via _resolve_aop_ke_ids reuse — single function call, no refactor, no duplicate helper"
  - "Reactome JSON loaders live in app.py module scope (not inside create_app) so the create_app body stays compact; loading is single-process at startup, called once per Flask app instance"
  - "Test fixture re-wires v1_api.set_models with the Reactome model + small in-memory metadata/counts dicts — avoids dependency on the production data/*.json files (which may be absent in dev/test)"

patterns-established:
  - "Three-mapping-type symmetry in v1_api: WP, GO, Reactome routes share envelope, pagination helpers, CORS after_request, error wording shape, CSV detection — Reactome diverges only where D-05/D-08 require"
  - "Reactome enrichment dictionary contract: reactome_metadata = {reactome_id: {description: str, ...}}, reactome_gene_counts = {reactome_id: int} — locks the in-memory shape for downstream consumers (e.g. Phase 26-06 explore tab uses the same serializer output)"

requirements-completed: [REXP-01]

duration: 7min
completed: 2026-05-06
---

# Phase 26 Plan 05: v1_api Reactome routes + serializer + AOP filter Summary

Public read surface for approved KE-Reactome mappings: `_serialize_reactome_mapping` + `_REACTOME_MAPPING_CSV_FIELDS` constants, paginated `GET /api/v1/reactome-mappings` (with WP-parity AOP filter), `GET /api/v1/reactome-mappings/<uuid>`, extended `set_models` signature, and app.py wiring of Reactome metadata + gene counts loaded once at startup.

## Performance

- Duration: ~7 min
- Started: 2026-05-06T07:59:21Z
- Completed: 2026-05-06T08:06:32Z
- Tasks: 4
- Files modified: 2 (src/blueprints/v1_api.py, app.py); 1 created (tests/test_v1_api_reactome.py)

## Accomplishments

- `_serialize_reactome_mapping(row)` returns the D-05 shape — uuid, ke_id, ke_name, reactome_id, pathway_name, species, confidence_level, pathway_description, reactome_gene_count, ke_aop_context, ke_bio_level, plus the standard provenance dict (suggestion_score, approved_by, approved_at, proposed_by). No GO-only fields leak in.
- `_REACTOME_MAPPING_CSV_FIELDS` is the 15-element list in the order specified by D-05/D-56 (uuid, ke_id, ke_name, reactome_id, pathway_name, species, confidence_level, suggestion_score, approved_by, approved_at, proposed_by, ke_aop_context, ke_bio_level, pathway_description, reactome_gene_count).
- `set_models()` extended with `reactome_mapping`, `reactome_meta`, `reactome_counts` kwargs; three new module-level globals (`reactome_mapping_model`, `reactome_metadata`, `reactome_gene_counts`).
- `GET /api/v1/reactome-mappings` — paginated list with filters `ke_id`, `reactome_id`, `confidence_level`, `aop_id`, `page`, `per_page`. CSV via `?format=csv` or `Accept: text/csv`. AOP filter wired through `_resolve_aop_ke_ids` reuse (D-08). `aop_id` preserved on pagination next/prev URLs.
- `GET /api/v1/reactome-mappings/<uuid>` — single mapping with 404 + descriptive error (`Reactome mapping not found: <uuid>`) and 500 fallback. Both routes inherit CORS via the existing `@v1_api_bp.after_request` decorator.
- `app.py` loads `data/reactome_pathway_metadata.json` and `data/reactome_gene_annotations.json` once at startup, computes per-pathway gene counts, and passes all three (model + metadata dict + counts dict) into `set_v1_api_models`. Graceful fallback to `{}` when the JSON files are absent (dev/test envs).
- 16-test integration suite (`tests/test_v1_api_reactome.py`) — 3 serializer/constant smoke tests + 11 list-route tests + 2 detail-route tests. Covers pagination total, every filter (ke_id, reactome_id, confidence_level), CSV header completeness, AOP filter happy-path, AOP filter ValueError -> 400, response key shape, AOP-id preservation in pagination URL, CORS header, and enrichment field population. Uses Flask test client + `monkeypatch` for `_resolve_aop_ke_ids` (no live SPARQL hits).

## Task Commits

1. Task 1+2 (RED): Failing test suite for the v1 Reactome API surface — `b3ccd1a` (test)
2. Task 1 (GREEN): Serializer + CSV constant + extended set_models — `ab008c4` (feat)
3. Task 2 (GREEN): list_reactome_mappings + get_reactome_mapping routes — `df8365a` (feat)
4. Task 3: app.py wires Reactome model + metadata + gene_counts — `aae4646` (feat)

## Files Created/Modified

- `src/blueprints/v1_api.py` — +150 lines. Three new globals (`reactome_mapping_model`, `reactome_metadata`, `reactome_gene_counts`); extended `set_models` signature and assignment block; new `_REACTOME_MAPPING_CSV_FIELDS` constant; new `_serialize_reactome_mapping` function; two new route handlers (`list_reactome_mappings`, `get_reactome_mapping`).
- `app.py` — +47 lines. Two module-level helpers (`_load_reactome_metadata`, `_load_reactome_gene_counts`); inside `create_app`, both helpers are invoked and their results passed as `reactome_meta=...`/`reactome_counts=...` to `set_v1_api_models`, alongside the existing `services.reactome_mapping_model` reference.
- `tests/test_v1_api_reactome.py` — New 365-line integration test suite. Single fixture (`v1r_client`) re-wires `v1_api.set_models` with a fresh temp DB and small in-memory metadata/counts dicts. Local `_seed_reactome` helper inserts rows directly into `ke_reactome_mappings` via SQL.

## Decisions Made

- **Kwarg rename to avoid global/local shadow.** The plan's Option 1 was used: kwargs named `reactome_meta` and `reactome_counts` (not `reactome_metadata`/`reactome_gene_counts`) so the function body can `global reactome_metadata, reactome_gene_counts` without colliding with parameter names. Module-level globals keep their natural names so the serializer reads from `reactome_metadata` / `reactome_gene_counts` directly. Caller in `app.py` passes `reactome_meta=...` / `reactome_counts=...`.
- **AOP filter parity with WP, not GO.** The Reactome route adds `aop_id` support via direct `_resolve_aop_ke_ids` reuse — exactly the shape `list_mappings` (WP) uses. The GO route does not have this filter; deviating from the GO template here is intentional and matches D-08.
- **Reactome metadata loaded at module level (not lazily).** `_load_reactome_metadata` and `_load_reactome_gene_counts` run once at `create_app` time. Loading is cheap (small JSON files), and the dicts are read-only after startup, so a single load per process is sufficient. Graceful `{}` fallback keeps the test/dev environment workable when the precomputed JSON files are absent.
- **Test data is dict-driven, not via `create_mapping`.** Direct SQL inserts via `_seed_reactome` allow fields like `approved_by_curator`, `approved_at_curator`, and `species` to be set in a single statement. This mirrors the test fixture pattern already used in `tests/test_reactome_mapping_model.py` (Phase 26-02).

## Deviations from Plan

None — plan executed exactly as written. Acceptance-grep counts:

- `^_REACTOME_MAPPING_CSV_FIELDS = ` matches: 1 (line 199)
- `^def _serialize_reactome_mapping\b` matches: 1 (line 220)
- `reactome_mapping=None, reactome_meta=None, reactome_counts=None` present in extended `set_models` signature: yes
- `^reactome_mapping_model = None|^reactome_metadata = None|^reactome_gene_counts = None` count: 3
- `@v1_api_bp\.route\("/reactome-mappings", methods=\["GET"\]\)` matches: 1 (line 542)
- `@v1_api_bp\.route\("/reactome-mappings/<uuid>"` matches: 1 (line 614)
- `_resolve_aop_ke_ids(` count: 3 (definition + WP route + new Reactome route)
- `reactome_mapping_model\.get_reactome_mappings_paginated|reactome_mapping_model\.get_reactome_mapping_by_uuid` count: 2
- `reactome_meta=|reactome_counts=` matches in `app.py`: 2
- `reactome_mapping=services\.reactome_mapping_model` matches in `app.py`: 1 (the new set_v1_api_models call site; the two pre-existing matches in set_api_models / set_admin_models are unchanged)
- `_load_reactome_metadata|_load_reactome_gene_counts` count in `app.py`: 4 (two definitions + two call sites)
- `pytest tests/test_v1_api_reactome.py -q --no-cov`: 16 passed
- `pytest tests/test_v1_api.py tests/test_v1_api_reactome.py -q --no-cov`: 36 passed (no regression in the existing v1_api suite)
- `pytest tests/ -q --no-cov --ignore=tests/test_app.py`: 202 passed (no regression elsewhere)

## Issues Encountered

- **Pre-existing test failures in `tests/test_app.py`.** `TestRoutes::test_login_redirect` and `TestGuestAuth::test_guest_login_page_renders` fail on the worktree base (and on `4736009`); these are already documented in `.planning/phases/26-public-api-and-exports/deferred-items.md`. They do not touch the v1 API surface and are unaffected by this plan.
- **Manual smoke (server kill+restart) was sandbox-blocked.** The Flask dev-server launch step from the plan's verification section could not run inside the executor sandbox. Coverage equivalent to the manual smoke is provided by 16 Flask test-client integration tests that exercise the same routes end-to-end.

## Self-Check: PASSED

- FOUND: `src/blueprints/v1_api.py` (modified — adds globals, extended set_models, _serialize_reactome_mapping, _REACTOME_MAPPING_CSV_FIELDS, two new routes)
- FOUND: `app.py` (modified — adds two helpers, extends set_v1_api_models call)
- FOUND: `tests/test_v1_api_reactome.py` (created — 16 tests, all passing)
- FOUND: commit `b3ccd1a` (Task RED tests)
- FOUND: commit `ab008c4` (Task 1 GREEN — serializer + set_models)
- FOUND: commit `df8365a` (Task 2 GREEN — routes)
- FOUND: commit `aae4646` (Task 3 — app.py wiring)
- FOUND: `pytest tests/test_v1_api_reactome.py -q --no-cov` -> 16 passed
- FOUND: `pytest tests/test_v1_api.py tests/test_v1_api_reactome.py -q --no-cov` -> 36 passed (no regression)

## Next Phase Readiness

- Plan 26-06 (explore-tab integration) can now consume `GET /api/v1/reactome-mappings` directly from the templates/explore.html AJAX DataTable, mirroring how the WP tab consumes `/api/v1/mappings` today. The response shape (D-05) and pagination envelope are locked.
- Plan 26-07 (RDF/Turtle export) does NOT depend on this plan — it operates on `ReactomeMappingModel.get_all_mappings()` rows directly. No coupling.
- Plan 26-08 (OpenAPI YAML + downloads page + docs_api) can document the now-live routes against the actual response objects rather than against a spec stub. The 15-element `_REACTOME_MAPPING_CSV_FIELDS` order is the exact CSV column order to document.
- The `_resolve_aop_ke_ids` helper now has three call sites (WP, internal `api/get_aop_kes`, Reactome). If a future cross-cutting refactor consolidates AOP resolution, this is the centralisation point.

---
*Phase: 26-public-api-and-exports*
*Completed: 2026-05-06*
