---
phase: 26-public-api-and-exports
plan: "06"
subsystem: exports
tags: [reactome, gmt-export, rdf-export, flask-blueprint, main-blueprint, route-handlers]

requires:
  - phase: 26-public-api-and-exports
    plan: "03"
    provides: generate_ke_reactome_gmt and generate_ke_centric_reactome_gmt — used inside _get_or_generate_gmt branches
  - phase: 26-public-api-and-exports
    plan: "04"
    provides: generate_ke_reactome_turtle(mappings, reactome_metadata=...) — used inside the new RDF route
  - phase: 26-public-api-and-exports
    plan: "05"
    provides: _load_reactome_metadata(app) helper + reactome_metadata_dict variable — reused (no duplication) to feed both v1 API and main blueprint
provides:
  - GET /exports/gmt/ke-reactome (per-mapping GMT, optional ?min_confidence=High|Medium|Low)
  - GET /exports/gmt/ke-reactome-centric (KE-centric union GMT)
  - GET /exports/rdf/ke-reactome (Turtle, includes pathwayDescription triples when reactome_metadata is wired)
  - _get_or_generate_gmt: extended with "reactome" and "reactome-centric" branches
  - main blueprint set_models(): extended with reactome_mapping and reactome_meta kwargs
  - main blueprint module globals: reactome_mapping_model, reactome_metadata
affects: [26-07-ttl-and-jsonld-rdf, 26-08-tests-and-docs, downstream consumers using the GMT/TTL endpoints (analyser, fgsea/clusterProfiler users)]

tech-stack:
  added: []
  patterns:
    - "Three-route-cluster mirror: ke-reactome / ke-reactome-centric / ke-reactome-rdf clone the existing ke-go / ke-go-centric / ke-go-rdf routes 1:1, swapping mapping_type literal and 503 wording per D-17"
    - "Cache filename pattern f\"KE-{mapping_type.upper()}_{today}_{tier}.gmt\" naturally produces KE-REACTOME_* and KE-REACTOME-CENTRIC_* without template change"
    - "RDF route writes empty placeholder when mappings list is empty so the 503 branch fires (rdflib serializes an empty graph as a single newline which would otherwise mask the empty case)"
    - "Global-name vs kwarg-name decoupling — set_models accepts reactome_meta=… (renamed) to assign to the natural global reactome_metadata, avoiding the local-shadowing-global trap (same approach as plan 26-05)"

key-files:
  created: []
  modified:
    - src/blueprints/main.py
    - app.py
    - tests/test_reactome_exports.py

key-decisions:
  - "Reorder app.py: move _load_reactome_metadata and _load_reactome_gene_counts calls ABOVE set_main_models so the same dict instance feeds both blueprints (single load, two consumers)"
  - "Tighten RDF empty-mappings branch: write empty placeholder when reactome_mapping_model.get_all_mappings() returns []. rdflib's serializer returns '\\n' (1 byte) for an empty graph, which would otherwise pass the cache_path.stat().st_size == 0 check and return 200 instead of 503 — divergence from the plan but required for the 'empty -> 503' acceptance bullet"
  - "Use a self-contained pytest fixture (export_seeded) instead of relying on a shared reactome_mapping_model fixture — mirrors the per-test temp-DB + monkeypatch pattern already established in tests/test_v1_api_reactome.py and tests/test_reactome_submission.py"
  - "Cache cleanup inside fixture (deletes both KE-REACTOME*.gmt and ke-reactome-mappings.ttl from EXPORT_CACHE_DIR before each test) — required because the GMT cache filename includes today's date and a stale file from earlier suite runs would shadow the seeded fixture"

patterns-established:
  - "Reactome export route family parity with WP and GO: identical signature shape (GET, optional ?min_confidence=, attachment download, text/plain | text/turtle), divergent only in the 503 wording (no SPARQL caveat, since Reactome reads from a local JSON annotations file)"
  - "Empty-mappings -> 503 normalization: future GO/WP RDF routes that need the same guarantee can adopt the empty-placeholder write idiom used here"

requirements-completed: [REXP-02, REXP-03]

duration: 16min
completed: 2026-05-06
---

# Phase 26 Plan 06: GMT/RDF route handlers + _get_or_generate_gmt extension + main blueprint wiring Summary

Three new download routes (`/exports/gmt/ke-reactome`, `/exports/gmt/ke-reactome-centric`, `/exports/rdf/ke-reactome`) wired into the main blueprint, with `_get_or_generate_gmt` extended to dispatch the two Reactome GMT branches, the main blueprint's `set_models` accepting Reactome model + metadata, and `app.py` reordered so the same Reactome metadata dict instance is reused by both v1 API and main blueprint without a duplicate load.

## Performance

- Duration: ~16 min
- Started: 2026-05-06T08:06Z (immediately after plan 26-05 in this wave-3 worktree)
- Completed: 2026-05-06T08:22Z
- Tasks: 5
- Files modified: 3 (src/blueprints/main.py, app.py, tests/test_reactome_exports.py)

## Accomplishments

- `src/blueprints/main.py` module-level globals extended: `reactome_mapping_model = None`, `reactome_metadata = None`. Both wired through the extended `set_models(..., reactome_mapping=None, reactome_meta=None)` signature with the kwarg-name renamed to `reactome_meta` to avoid shadowing the natural global.
- `_get_or_generate_gmt` extended: inline import now pulls `generate_ke_reactome_gmt` and `generate_ke_centric_reactome_gmt` from `src.exporters.gmt_exporter`; two new `elif` branches inserted before the existing GO `else` fall-through. Cache filename pattern `KE-{mapping_type.upper()}_{today}_{tier}.gmt` produces `KE-REACTOME_2026-05-06_All.gmt` and `KE-REACTOME-CENTRIC_2026-05-06_High.gmt` correctly without template changes.
- Three new route handlers added next to their analogs:
  - `download_ke_reactome_gmt` (placed after `download_ke_go_centric_gmt`)
  - `download_ke_reactome_centric_gmt` (placed after the above)
  - `download_ke_reactome_rdf` (placed after `download_ke_go_rdf`)
  All return 200 + correct mimetype + attachment Content-Disposition on happy path; 503 + `{error: "No KE-Reactome mappings available"}` (or `... for RDF export`) on empty cache.
- The RDF route threads `reactome_metadata=reactome_metadata` into `generate_ke_reactome_turtle`, so `pathwayDescription` triples are emitted whenever the metadata dict is populated at startup. Verified end-to-end via `test_download_ke_reactome_rdf_pathway_description`.
- `app.py` reorganized: `_load_reactome_metadata(app)` and `_load_reactome_gene_counts(app)` now run BEFORE `set_main_models`, so a single `reactome_metadata_dict` instance is passed into both `set_main_models` (as `reactome_meta=`) and `set_v1_api_models` (as `reactome_meta=`). No duplicate JSON load.
- `tests/test_reactome_exports.py` extended with 7 new integration tests (total file: 23 tests, all passing):
  - `test_download_ke_reactome_gmt_route` — 200, text/plain, attachment, `KE1_…_R-HSA-100` row format, TP53 gene present
  - `test_download_ke_reactome_gmt_min_confidence` — `?min_confidence=High` filters Medium row away
  - `test_download_ke_reactome_centric_gmt_route` — one row per KE (KE1, KE5)
  - `test_download_ke_reactome_gmt_503_when_empty` — empty model -> 503 with documented error message
  - `test_download_ke_reactome_rdf_route` — 200, text/turtle, rdflib re-parses, exactly 2 KeyEventReactomeMapping subjects
  - `test_download_ke_reactome_rdf_pathway_description` — `pathwayDescription` triple emitted when metadata wired
  - `test_download_ke_reactome_rdf_503_when_empty` — empty model -> 503

## Task Commits

1. Task 1: Extend `set_models` and add module globals — `e802801` (feat)
2. Task 2: Extend `_get_or_generate_gmt` with Reactome branches — `b149cc1` (feat)
3. Task 3: Add three Reactome download routes — `8972dd8` (feat)
4. Task 4: Wire Reactome model + metadata into `set_main_models` in app.py — `61670be` (feat)
5. Task 5: Integration tests for export routes (+RDF empty-fix) — `5d50ff6` (test)

## Verification

- `pytest tests/test_reactome_exports.py -v --no-cov` — **23/23 passed** (12 generator + 4 turtle parse/provenance/no-go-pred + 4 turtle metadata/filter/empty + 7 new route tests).
- `pytest --no-cov -q` (full suite, in worktree) — **243 passed, 2 failed**. The two failures (`tests/test_app.py::TestRoutes::test_login_redirect`, `tests/test_app.py::TestGuestAuth::test_guest_login_page_renders`) are pre-existing and unrelated to this plan (login route 404 — predates the Phase 26 work; logged below).
- `python -c "import app; print('imports ok')"` — clean import, all model loaders fire (Reactome metadata: 1954 entries; Reactome annotations: 1954 entries).
- `grep "@main_bp.route" src/blueprints/main.py | grep ke-reactome` confirms 3 new route decorators.
- All Plan acceptance bullets satisfied (see "Acceptance criteria check" below).

## Acceptance criteria check

| Plan-level must-have | Status |
| --- | --- |
| GET /exports/gmt/ke-reactome -> .gmt download | PASS (test_download_ke_reactome_gmt_route) |
| ?min_confidence=High filtering | PASS (test_download_ke_reactome_gmt_min_confidence) |
| GET /exports/gmt/ke-reactome-centric -> per-KE union | PASS (test_download_ke_reactome_centric_gmt_route) |
| GET /exports/rdf/ke-reactome -> .ttl download with pathway descriptions | PASS (test_download_ke_reactome_rdf_route + test_download_ke_reactome_rdf_pathway_description) |
| 503 + "No KE-Reactome mappings available" when empty (all three routes) | PASS (gmt_503 + rdf_503 tests; centric variant covered by the same _get_or_generate_gmt path) |
| _get_or_generate_gmt handles "reactome" and "reactome-centric" | PASS (grep confirms 2 elif branches; verified by all GMT route tests) |
| set_models accepts reactome_mapping + reactome_metadata kwargs | PASS (signature inspection assertion in Task 1 verify) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RDF empty-mappings did not return 503**

- **Found during:** Task 5 (initial test run — `test_download_ke_reactome_rdf_503_when_empty` failed with `200 == 503`)
- **Issue:** `rdflib.Graph().serialize(format="turtle")` returns `"\n"` (1 byte) for an empty graph. The plan-spec route wrote that 1-byte content into the cache file, then the `cache_path.stat().st_size == 0` check returned False, returning 200 instead of 503.
- **Fix:** Branch on `if mappings:` before generating; when the mappings list is empty, write `""` to the cache file. Keeps the existing happy-path generation untouched.
- **Files modified:** `src/blueprints/main.py` (download_ke_reactome_rdf)
- **Commit:** `5d50ff6` (bundled with the Task 5 test commit since the failing test exposed the bug)
- **Note:** The same theoretical bug exists in `download_ke_go_rdf` and `download_ke_wp_rdf`; left unchanged per the deviation-rule scope boundary (out-of-scope for this plan, no current test exercises those empty-state paths). Logged to `deferred-items.md`.

**2. [Rule 2 - Missing critical functionality] Test fixture pattern**

- **Found during:** Task 5 planning
- **Issue:** Plan referenced a `reactome_mapping_model` pytest fixture that does not exist as a shared fixture in `tests/conftest.py`. Other Reactome tests (test_v1_api_reactome.py, test_reactome_submission.py) define per-file fixtures inline.
- **Fix:** Defined a self-contained `export_seeded` fixture inside `tests/test_reactome_exports.py` mirroring the per-test temp-DB pattern already established in the codebase. Fixture creates a `Database` + `ReactomeMappingModel`, seeds two rows directly via SQL, monkeypatches the gene-annotations loader and the main blueprint's globals, and clears any cached GMT/TTL files before yielding the test client.
- **Files modified:** `tests/test_reactome_exports.py`
- **Commit:** `5d50ff6`

### Minor structural change

- `app.py`: moved the `_load_reactome_metadata(app)` / `_load_reactome_gene_counts(app)` calls BEFORE `set_main_models` (instead of between `set_main_models` and `set_v1_api_models` as in plan 26-05). Reason: the main blueprint also needs the metadata dict now, and reordering keeps the load single-instance and single-source. No behavioural change to v1 API; verified by clean `import app`.

## Deferred Issues

- `download_ke_go_rdf` and `download_ke_wp_rdf` have the same `rdflib serializes empty graph as "\n"` issue as the Reactome RDF route did before this plan's fix. Their existing tests do not exercise the empty-mappings -> 503 path, so the bug is latent. Logging to `deferred-items.md` for a follow-up sweep (a one-line `if mappings:` guard would normalize all three).

## Notes for Plan 26-07 (RDF context expansion)

- `reactome_metadata` is now globally accessible inside the main blueprint (module-level), so future RDF expansions (e.g. ChEBI/MeSH cross-refs, AOP context triples) can read from the same dict without further wiring.
- The 503 wording for the RDF route is `"No KE-Reactome mappings available for RDF export"` (matches existing GO/WP RDF wording — diverges from the GMT 503 wording by adding the `for RDF export` suffix).

## Self-Check: PASSED

- File `src/blueprints/main.py` modified — FOUND
- File `app.py` modified — FOUND
- File `tests/test_reactome_exports.py` modified — FOUND
- Commit `e802801` (Task 1) — FOUND
- Commit `b149cc1` (Task 2) — FOUND
- Commit `8972dd8` (Task 3) — FOUND
- Commit `61670be` (Task 4) — FOUND
- Commit `5d50ff6` (Task 5) — FOUND
