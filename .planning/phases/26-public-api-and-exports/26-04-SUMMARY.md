---
phase: 26-public-api-and-exports
plan: "04"
subsystem: exporters
tags: [rdf, turtle, reactome, exports, rdflib, provenance]

# Dependency graph
requires:
  - phase: 26-public-api-and-exports
    provides: "Plan 26-01 — VOCAB namespace constant (renamed from KEWP) and existing generate_ke_wp_turtle / generate_ke_go_turtle as analog templates"
  - phase: 23-reactome-mapping
    provides: "ReactomeMappingModel rows with reactome_id, pathway_name, species, ke_id, ke_title, confidence_level, suggestion_score, approved_by_curator, approved_at_curator"
provides:
  - "generate_ke_reactome_turtle(mappings, min_confidence=None, reactome_metadata=None) — third Turtle generator alongside KE-WP and KE-GO"
  - "VOCAB.KeyEventReactomeMapping rdf:type plus reactomeId / pathwayName / species / pathwayDescription predicates (D-20)"
  - "Optional reactome_metadata kwarg keyed by reactome_id, drives vocab#pathwayDescription emission"
  - "7 rdflib re-parse tests in tests/test_reactome_exports.py — class IRI + core predicates, typed provenance literals (xsd:dateTime, xsd:decimal), GO-predicate exclusion, optional pathwayDescription, min_confidence filter, empty input"
affects:
  - "26-06 (route wiring) — download_ke_reactome_rdf can now `from src.exporters.rdf_exporter import generate_ke_reactome_turtle` and pass reactome_metadata to enable pathwayDescription triples"
  - "Downstream RDF consumers (ELIXIR, FAIR catalogues) ingesting the v1.4 Reactome dataset"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GO-analog mirroring with three localized swaps: (1) drop goDirection/goNamespace, (2) add species predicate, (3) add optional pathwayDescription driven by external metadata dict"
    - "Provenance triple set kept identical across WP/GO/Reactome — dcterms:creator, dcterms:date^^xsd:dateTime, vocab#suggestionScore^^xsd:decimal — for predictable downstream ingestion"

key-files:
  created: []
  modified:
    - "src/exporters/rdf_exporter.py (+78 lines, one new public function `generate_ke_reactome_turtle`)"
    - "tests/test_reactome_exports.py (+107 lines, 7 new Turtle tests appended after the 9 GMT tests from plan 26-03)"

key-decisions:
  - "Used VOCAB.KeyEventReactomeMapping (not KEWP) — plan 26-01 already renamed the namespace constant in wave 1; new function reuses the renamed symbol verbatim"
  - "Optional reactome_metadata kwarg degrades gracefully — when None or missing key, the function still produces valid Turtle without pathwayDescription. Plan 26-06's route should pass the full metadata dict to enable description emission"
  - "Reactome rows do NOT emit goDirection or goNamespace triples — Reactome has no direction concept and species is its own predicate, so the GO-only block is omitted entirely (verified by `test_turtle_no_go_predicates`)"

patterns-established:
  - "Pattern: third Turtle generator follows the WP/GO 1:1 mirror with surgical swaps — keeps maintenance overhead low and the predicate vocabulary internally consistent"
  - "Pattern: external-metadata-driven optional triples — `reactome_metadata` is a sidecar dict the route layer can build from precomputed Reactome metadata cache; the exporter never reaches into the database itself"

requirements-completed: [REXP-03]

# Metrics
duration: 13min
completed: 2026-05-06
---

# Phase 26 Plan 04: RDF exporter — generate_ke_reactome_turtle Summary

**Third Turtle generator added to `src/exporters/rdf_exporter.py`, mirroring `generate_ke_go_turtle` with the GO-only direction/namespace block dropped and species + optional pathwayDescription added per D-20; verified end-to-end via 7 rdflib re-parse tests asserting class IRI, core predicates, typed provenance literals, and GO-predicate exclusion.**

## Performance

- **Duration:** ~13 min
- **Started:** 2026-05-06T07:49:00Z (worktree created)
- **First commit:** 2026-05-06T07:59:49Z (Task 1)
- **Completed:** 2026-05-06T08:02:18Z
- **Tasks:** 2 (auto / TDD)
- **Files modified:** 2 (1 source, 1 test)

## Accomplishments

- `generate_ke_reactome_turtle(mappings, min_confidence=None, reactome_metadata=None)` returns a Turtle string parseable by rdflib's `Graph.parse(format="turtle")`.
- For each row, the parsed graph contains the full D-20 triple set: `rdf:type vocab#KeyEventReactomeMapping`, `dcterms:identifier`, `vocab#keyEventId`, `vocab#keyEventName`, `vocab#reactomeId`, `vocab#pathwayName`, `vocab#species` (when present), `vocab#confidenceLevel`.
- Provenance triples match GO/WP exactly: `dcterms:creator` (provider-prefixed identity), `dcterms:date^^xsd:dateTime`, `vocab#suggestionScore^^xsd:decimal`.
- Optional `reactome_metadata={reactome_id: {"description": "..."}}` drives an additional `vocab#pathwayDescription` triple per row when the description is present.
- `min_confidence="high"` filters rows before serialisation; empty input yields a graph with only `@prefix` declarations.
- 7 rdflib re-parse tests cover: class IRI + core predicates, typed provenance literals (xsd:dateTime, xsd:decimal), GO-predicate exclusion (`goDirection`/`goNamespace` absent), optional pathwayDescription emission and omission, min_confidence filter, empty input.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add `generate_ke_reactome_turtle` to `src/exporters/rdf_exporter.py`** — `2018465` (feat)
2. **Task 2: rdflib re-parse tests appended to `tests/test_reactome_exports.py`** — `2c37d82` (test)

_TDD note: implementation landed first (Task 1) so the test file's imports could resolve cleanly; Task 1 was verified independently via the embedded one-liner smoke test (`KeyEventReactomeMapping` present, `reactomeId` present, `goDirection` absent), and Task 2 was verified via `pytest tests/test_reactome_exports.py -v -k turtle` (7 passed)._

## Files Created/Modified

- `src/exporters/rdf_exporter.py` — appended `generate_ke_reactome_turtle` after `generate_ke_go_turtle`. No changes to existing WP/GO generators or to the `VOCAB`/`MAPPING`/`DCTERMS` namespace bindings.
- `tests/test_reactome_exports.py` — appended 7 Turtle tests after the 9 GMT tests from plan 26-03. Total file now contains 16 tests.

## Decisions Made

- **Used the renamed `VOCAB` constant verbatim** — plan 26-01 (wave 1) renamed `KEWP -> VOCAB`, so the new function uses `VOCAB.KeyEventReactomeMapping`, `VOCAB.reactomeId`, `VOCAB.species`, `VOCAB.pathwayDescription`. The Turtle output uses the `ke-wp:` prefix alias (declared via `g.bind("ke-wp", VOCAB)`) so the human-readable serialisation matches the existing WP/GO files.
- **Followed the plan's `<action>` block byte-for-byte** for the field-swap section — no design tweaks. The only divergence from a literal copy of `generate_ke_go_turtle` is the species block (added) and the goDirection/goNamespace blocks (dropped), plus the new `reactome_metadata` kwarg branch at the bottom.
- **Did not modify the existing GO function's `goDirection`/`goNamespace` blocks** — they continue to live in `generate_ke_go_turtle` (lines 142, 145). The acceptance criterion `awk '/^def generate_ke_reactome_turtle/,/^def |^$/'` was the noisier of the two grep checks (it stops at the first blank line in the new function); the plan-author intent — "no GO predicates leak into the Reactome triple emission" — is satisfied (only mentions of `goDirection`/`goNamespace` in the new function are inside the docstring's "Drops goDirection/goNamespace" sentence).

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 auto-fixes were needed; the GO analog provided a clean template, the wave-1 `VOCAB` rename was already in place, and the test fixtures from plan 26-03 mapped cleanly to the rdflib re-parse assertions.

## Issues Encountered

- **Pre-existing test failures (out of scope, unchanged):** `tests/test_app.py::TestRoutes::test_login_redirect` and `tests/test_app.py::TestGuestAuth::test_guest_login_page_renders` continue to fail on the worktree base — confirmed by `git stash && pytest <those tests> --no-cov`, both fail before any 26-04 changes. They are unrelated to RDF exporters and remain logged in `.planning/phases/26-public-api-and-exports/deferred-items.md` per the GSD scope-boundary rule.
- **Pre-existing global coverage threshold (out of scope):** `make test` reports `Required test coverage of 45% not reached. Total coverage: 43.40%`. The new code is exercised by the 7 new tests; the threshold gap is from untouched modules (`src/exporters/zenodo_uploader.py`, `src/services/embedding.py`, `src/suggestions/*`) that the 26-04 surface does not touch. Existing deferred item.

## User Setup Required

None — no external service configuration required. The optional `reactome_metadata` dict will be wired in by plan 26-06's `download_ke_reactome_rdf` route; until then, calling the function with only `mappings` produces valid Turtle without `vocab#pathwayDescription` triples (graceful degradation matches the plan's threat-model expectation).

## Next Phase Readiness

- **Plan 26-06 (route wiring)** can now:
  - `from src.exporters.rdf_exporter import generate_ke_reactome_turtle`
  - Build a `reactome_metadata` dict from the precomputed Reactome metadata cache (one entry per `reactome_id` with at least a `description` key)
  - Call `generate_ke_reactome_turtle(rows, min_confidence=..., reactome_metadata=reactome_metadata)`
- **Plan 26-08 (test/coverage)** has 7 new tests it does not need to add; the existing `tests/test_reactome_exports.py` is the canonical location for any further Reactome export assertions.
- No blockers for downstream plans in the wave. The 11-column SELECT shape from plan 26-02 is consumed by the rows passed in here; the caller (plan 26-06) is responsible for ensuring `species`, `approved_by_curator`, `approved_at_curator`, `suggestion_score` keys are present on the row dicts (all are emitted conditionally and degrade silently if absent).

## Self-Check

- [x] `src/exporters/rdf_exporter.py` contains `def generate_ke_reactome_turtle` at line 150 (verified via `grep -nE "^def generate_ke_reactome_turtle\b"`)
- [x] `tests/test_reactome_exports.py` contains 7 new `test_turtle_*` functions (verified via `pytest -v -k turtle`: 7 passed)
- [x] Commit `2018465` exists in `git log --oneline` (Task 1)
- [x] Commit `2c37d82` exists in `git log --oneline` (Task 2)
- [x] `python -c "from src.exporters.rdf_exporter import generate_ke_reactome_turtle"` succeeds
- [x] Plan smoke test passes: `KeyEventReactomeMapping` and `reactomeId` present in output; `goDirection` absent
- [x] `pytest tests/test_reactome_exports.py --no-cov` → 16 passed, 0 failed (9 GMT from 26-03 + 7 Turtle from 26-04)
- [x] Manual plan verification: `python -c "from src.exporters.rdf_exporter import generate_ke_reactome_turtle; print(generate_ke_reactome_turtle([{...}]))"` produces valid Turtle starting with `@prefix ke-wp:` and containing `ke-wp:KeyEventReactomeMapping`

## Self-Check: PASSED

---
*Phase: 26-public-api-and-exports*
*Completed: 2026-05-06*
