---
phase: 05-exports-and-dataset-publication
plan: 01
subsystem: api
tags: [gmt, rdf, turtle, rdflib, sparql, wikipathways, go-annotations, exporters]

# Dependency graph
requires:
  - phase: 02-data-model-and-audit-trail
    provides: uuid, approved_by_curator, approved_at_curator, suggestion_score columns on mappings
  - phase: 03-stable-public-rest-api
    provides: MappingModel.get_all_mappings() dict list interface

provides:
  - src/exporters/gmt_exporter.py — generate_ke_wp_gmt, generate_ke_go_gmt, _make_ke_slug
  - src/exporters/rdf_exporter.py — generate_ke_wp_turtle, generate_ke_go_turtle (rdflib-based)

affects:
  - 05-02 (download routes calling these exporters)
  - 05-03 (dataset publication consuming the Turtle output)

# Tech tracking
tech-stack:
  added: [rdflib==6.3.2]
  patterns:
    - Standalone exporter modules with no Flask context required
    - Batch SPARQL VALUES query for all WP IDs in one round-trip
    - GMT row-skip convention when gene list is empty
    - rdflib Graph per call, serialize(format='turtle') returns str (rdflib >= 6.0)

key-files:
  created:
    - src/exporters/gmt_exporter.py
  modified:
    - src/exporters/rdf_exporter.py
    - src/exporters/__init__.py
    - requirements.txt

key-decisions:
  - "GMT term name format locked as KE{N}_{Title_Slug}_{Target_ID} — one row per KE-pathway pair"
  - "Batch SPARQL VALUES query for all WP IDs at once rather than per-pathway queries"
  - "GMT rows with no genes silently skipped (not written) per GMT convention"
  - "rdflib Graph replaces string-concatenation RDFExporter class entirely"
  - "Provenance triples: DCTERMS.creator for approved_by_curator, DCTERMS.date for approved_at_curator, KEWP.suggestionScore for suggestion_score"

patterns-established:
  - "Exporter functions accept pre-fetched mapping dicts — no DB access inside exporter"
  - "_make_ke_slug shared helper: unicodedata NFKD normalise -> ASCII -> re.sub non-alphanumeric -> strip underscores"

requirements-completed: [EXPRT-01, EXPRT-02, EXPRT-03]

# Metrics
duration: 3min
completed: 2026-02-21
---

# Phase 05 Plan 01: GMT and RDF Exporter Modules Summary

**Standalone GMT and Turtle exporters: batch WikiPathways SPARQL for gene lists, rdflib Graph with Phase 2/3 provenance, no Flask dependency**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-21T19:11:12Z
- **Completed:** 2026-02-21T19:14:12Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `generate_ke_wp_gmt`: collects all unique WP IDs, fires single batch SPARQL VALUES query, builds tab-separated GMT rows with `KE{N}_{Slug}_{WP_ID}` term names; skips gene-less rows
- `generate_ke_go_gmt`: loads `data/go_bp_gene_annotations.json` once per call, maps GO IDs to HGNC symbols, same term-name format with GO ID suffix
- `generate_ke_wp_turtle` / `generate_ke_go_turtle`: rdflib Graph with typed literals for all Phase 2/3 provenance fields (uuid, approved_by_curator, approved_at_curator, suggestion_score); output validated by rdflib round-trip parse
- Both modules importable standalone with zero Flask context

## Task Commits

Each task was committed atomically:

1. **Task 1: GMT exporter with batch WikiPathways SPARQL and GO annotation lookup** - `819cd1b` (feat)
2. **Task 2: Replace rdf_exporter.py with rdflib Graph implementation** - `170aad7` (feat)

**Plan metadata:** (committed after SUMMARY.md)

## Files Created/Modified

- `src/exporters/gmt_exporter.py` - GMT generation for KE-WP and KE-GO; `_make_ke_slug`, `_fetch_pathway_genes_batch`, `generate_ke_wp_gmt`, `generate_ke_go_gmt`
- `src/exporters/rdf_exporter.py` - rdflib-based Turtle export; `generate_ke_wp_turtle`, `generate_ke_go_turtle`; old string-concatenation class removed
- `src/exporters/__init__.py` - Removed stale `RDFExporter` import; `ExportManager.exporters` dict updated
- `requirements.txt` - Added `rdflib==6.3.2`

## Decisions Made

- GMT term name format `KE{N}_{Title_Slug}_{Target_ID}` locked by user — numeric part extracted with `re.sub(r'\D', '', ke_id)`, title normalised via `unicodedata.normalize("NFKD", ...)` then `re.sub(r'[^a-zA-Z0-9]+', '_', ...)`
- Batch SPARQL approach: all unique WP IDs bundled into one VALUES clause query to avoid N+1 HTTP calls to WikiPathways SPARQL endpoint
- rdflib `Graph.serialize(format="turtle")` returns `str` in rdflib >= 6.0 — no decode needed
- `KEWP = Namespace("https://ke-wp-mapping.org/vocab#")`, `MAPPING = Namespace("https://ke-wp-mapping.org/mapping/")` — consistent with existing old exporter namespace choices

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed stale RDFExporter import in __init__.py**
- **Found during:** Task 2 (rdf_exporter replacement)
- **Issue:** `src/exporters/__init__.py` imported `RDFExporter` which no longer exists after the class was removed; this blocked `from src.exporters.rdf_exporter import ...` at the package level
- **Fix:** Removed `from .rdf_exporter import RDFExporter` from `__init__.py`, removed from `__all__`, removed from `ExportManager.exporters` dict
- **Files modified:** src/exporters/__init__.py
- **Verification:** Verification script ran successfully; 66 tests passed
- **Committed in:** `170aad7` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking import)
**Impact on plan:** Essential fix for package import correctness. No scope creep.

## Issues Encountered

None — beyond the stale import documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `generate_ke_wp_gmt` and `generate_ke_go_gmt` ready to be called from download route handlers (Phase 05-02)
- `generate_ke_wp_turtle` and `generate_ke_go_turtle` ready for dataset publication routes
- CacheModel integration point wired but optional — cache_model=None works without caching
- All 66 existing tests pass; no regressions

---
*Phase: 05-exports-and-dataset-publication*
*Completed: 2026-02-21*
