---
phase: 05-exports-and-dataset-publication
verified: 2026-02-22T16:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
human_verification:
  - test: "Live Zenodo DOI issuance"
    expected: "Dataset published on Zenodo and data/zenodo_meta.json updated with a real DOI and deposition_id"
    why_human: "Requires a real ZENODO_API_TOKEN and an actual Zenodo API call. zenodo_meta.json currently has null doi. The upload, versioning, and publish workflow cannot be verified without live credentials. The 503 guard when the token is absent was verified programmatically. The plan itself states this test should be performed with a sandbox token."
---

# Phase 05: Exports and Dataset Publication — Verification Report

**Phase Goal:** The curated database is downloadable in formats that bioinformatics tools consume directly, and it is registered with a permanent DOI that researchers can cite in publications.
**Verified:** 2026-02-22T16:00:00Z
**Status:** passed
**Re-verification:** No — initial verification.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | generate_ke_wp_gmt returns a valid GMT string with KE{N}_{Slug}_{WP_ID} term names | VERIFIED | Function imported and tested; slug logic confirmed; 22-line real GMT file in static/exports/ with terms like KE245_Activation_PXR_SXR_WP3851 |
| 2 | generate_ke_go_gmt returns valid GMT using HGNC symbols from go_bp_gene_annotations.json | VERIFIED | Function tested; KE-GO GMT file confirmed with terms like KE55_Increase_Cell_injury_death_GO:0006915 and 667 gene symbols in first row |
| 3 | generate_ke_wp_turtle returns valid Turtle with full provenance (uuid, approved_by_curator, approved_at_curator, suggestion_score) | VERIFIED | rdflib round-trip parse succeeds; 10 triples generated for test mapping; @prefix declarations present |
| 4 | generate_ke_go_turtle returns valid Turtle with same provenance fields | VERIFIED | Function tested; ke-go-mappings.ttl in cache is 494 chars, parses to 7 triples, contains @prefix and KeyEventGOMapping |
| 5 | GMT rows are skipped when no genes are available | VERIFIED | Early-exit guard at line 131 in gmt_exporter.py: `if not genes: continue`; confidence-filter test confirms empty return |
| 6 | Both exporters are importable standalone with no Flask context | VERIFIED | grep confirms no `from flask` / `import flask` in either exporter; importation confirmed without Flask context |
| 7 | Admin can trigger export cache regeneration via POST /admin/exports/regenerate and receive JSON status | VERIFIED | Route registered at line 505 of admin.py; calls generate_ke_wp_gmt, generate_ke_go_gmt, generate_ke_wp_turtle, generate_ke_go_turtle; returns jsonify({"status": "ok", "files": [...], "message": ...}) |
| 8 | Admin can trigger Zenodo publish via POST /admin/exports/publish-zenodo; on success DOI written to data/zenodo_meta.json | VERIFIED (mechanism) | Route registered and wired to zenodo_publish(); writes DOI to data/zenodo_meta.json on success; 503 guard confirmed when token missing |
| 9 | Missing ZENODO_API_TOKEN causes publish endpoint to return 503 with clear error | VERIFIED | Test client confirmed: status 503, message "ZENODO_API_TOKEN not configured" |
| 10 | GET /downloads renders page with links to all four export types | VERIFIED | Test client GET /downloads returns 200; HTML contains /exports/gmt/ke-wp, /exports/gmt/ke-go, /exports/rdf/ke-wp, /exports/rdf/ke-go |
| 11 | GET /exports/gmt/ke-wp, /exports/gmt/ke-go, /exports/rdf/ke-wp, /exports/rdf/ke-go serve files as download attachments | VERIFIED | All five routes registered in Flask url_map; cache-then-serve pattern wired to exporter functions; existing cached files confirmed substantive |
| 12 | DOI badge appears in navbar when data/zenodo_meta.json has a non-null doi field | VERIFIED | inject_zenodo_meta() context processor in app.py (line 144); navigation.html contains `{% if zenodo_meta and zenodo_meta.doi %}` block with DOI link |
| 13 | Stats page has export download buttons and Downloads nav link is present | VERIFIED | stats.html lines 113-119 contain four /exports/* buttons and /downloads link; navigation.html line 19 has Downloads nav link; test client confirmed both |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/exporters/gmt_exporter.py` | GMT generation for KE-WP and KE-GO | VERIFIED | 203 lines; exports generate_ke_wp_gmt, generate_ke_go_gmt, _make_ke_slug; no Flask import |
| `src/exporters/rdf_exporter.py` | rdflib-based Turtle with provenance | VERIFIED | 142 lines; exports generate_ke_wp_turtle, generate_ke_go_turtle; old string-concatenation class removed; rdflib Graph per call |
| `src/exporters/zenodo_uploader.py` | Zenodo API deposit and new-version workflow | VERIFIED | 121 lines; exports zenodo_publish, _build_zenodo_metadata; EnvironmentError guard confirmed |
| `data/zenodo_meta.json` | Persistent DOI and deposition_id storage | VERIFIED | File exists with `{"deposition_id": null, "doi": null, "concept_doi": null, "published_at": null}` — correct initial state |
| `templates/downloads.html` | Public downloads page with 4 export cards | VERIFIED | 129 lines; 4 cards with /exports/* links; confidence-filtered links; DOI citation block; Note and Data Sources sections |
| `static/exports/.gitkeep` | Ensures static/exports/ exists in git | VERIFIED | File present at 0 bytes; directory contains real cached exports |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| src/exporters/gmt_exporter.py | sparql.wikipathways.org/sparql | _fetch_pathway_genes_batch() with VALUES clause | VERIFIED | Line 53: VALUES clause built; BIND(STRAFTER STR for HGNC symbol extraction; bdbHgncSymbol IRI pattern |
| src/exporters/gmt_exporter.py | data/go_bp_gene_annotations.json | json.load in generate_ke_go_gmt | VERIFIED | Line 164-174: path defaults to data/go_bp_gene_annotations.json; loaded once per call |
| src/exporters/rdf_exporter.py | rdflib.Graph | g.serialize(format='turtle') | VERIFIED | Line 44: `g = Graph()`; line 79: `return g.serialize(format="turtle")`; rdflib 6.3.2 pinned in requirements.txt |
| src/blueprints/admin.py | src/exporters/zenodo_uploader.py | zenodo_publish() in publish_zenodo route | VERIFIED | Line 568: `from src.exporters.zenodo_uploader import zenodo_publish, _build_zenodo_metadata` |
| src/blueprints/admin.py | src/exporters/gmt_exporter.py | generate_ke_wp_gmt/generate_ke_go_gmt in regenerate_exports route | VERIFIED | Line 511: `from src.exporters.gmt_exporter import generate_ke_wp_gmt, generate_ke_go_gmt` |
| src/blueprints/admin.py | src/exporters/rdf_exporter.py | generate_ke_wp_turtle/generate_ke_go_turtle in regenerate_exports route | VERIFIED | Line 512: `from src.exporters.rdf_exporter import generate_ke_wp_turtle, generate_ke_go_turtle` |
| templates/downloads.html | /exports/gmt/ke-wp | anchor href with min_confidence param | VERIFIED | Line 37 and 41: links to /exports/gmt/ke-wp and /exports/gmt/ke-wp?min_confidence=High |
| templates/components/navigation.html | data/zenodo_meta.json | inject_zenodo_meta context processor | VERIFIED | app.py line 144: context processor reads data/zenodo_meta.json per request; navigation.html line 6: {% if zenodo_meta and zenodo_meta.doi %} |
| src/blueprints/main.py | src/exporters/gmt_exporter.py | generate_ke_wp_gmt called on cache miss | VERIFIED | Line 539: `from src.exporters.gmt_exporter import generate_ke_wp_gmt, generate_ke_go_gmt` inside _get_or_generate_gmt() |
| app.py | src/blueprints/admin.py | set_admin_models with go_mapping and cache_model | VERIFIED | Line 116: `set_admin_models(..., go_mapping=services.go_mapping_model, cache_model=services.cache_model)` |
| app.py | src/blueprints/main.py | set_main_models with go_mapping and cache_model | VERIFIED | Line 117: `set_main_models(services.mapping_model, go_mapping=services.go_mapping_model, cache_model=services.cache_model)` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EXPRT-01 | 05-01, 05-03 | GMT format export for KE-WP mappings, directly loadable by clusterProfiler/fgsea without preprocessing | SATISFIED | generate_ke_wp_gmt produces tab-separated GMT; real cached file KE-WP_2026-02-22_All.gmt has 22 lines with HGNC symbols; /exports/gmt/ke-wp route serves as attachment |
| EXPRT-02 | 05-01, 05-03 | GMT format export for KE-GO mappings | SATISFIED | generate_ke_go_gmt produces tab-separated GMT with GO term name format; KE-GO_2026-02-22_All.gmt confirmed with 1 line and 667 gene symbols; /exports/gmt/ke-go route serves as attachment |
| EXPRT-03 | 05-01, 05-03 | RDF/Turtle export of the full curated mapping database | SATISFIED | generate_ke_wp_turtle and generate_ke_go_turtle produce rdflib-parseable Turtle with full provenance; /exports/rdf/ke-wp and /exports/rdf/ke-go routes serve as attachments |
| EXPRT-04 | 05-02 | Dataset published on Zenodo with a DOI for use as a publication citation | PARTIALLY SATISFIED | The Zenodo upload/publish mechanism is fully implemented and wired (zenodo_uploader.py, /admin/exports/publish-zenodo route, data/zenodo_meta.json persistence). However, data/zenodo_meta.json still has null doi — a live DOI has not been issued. The plan explicitly acknowledged this requires a real ZENODO_API_TOKEN and treats the 503 graceful error as sufficient verification for the phase gate. This is a human-action item, not a code gap. |

**Orphaned requirements check:** REQUIREMENTS.md maps EXPRT-01, EXPRT-02, EXPRT-03, EXPRT-04 to Phase 5. All four appear in plan frontmatter. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| src/exporters/gmt_exporter.py | 49, 89 | `return {}` | Info | Legitimate early-exit guards for empty WP IDs list and failed SPARQL request — not stubs |
| src/exporters/__init__.py | 16-50 | ExportManager class references pre-phase-5 JSON/Excel/Parquet exporters | Info | ExportManager is a pre-existing artifact for older export routes not in phase 5 scope. The stale `RDFExporter` import was correctly removed in 05-01. ExportManager is not injected into set_main_models in app.py (export_mgr=None), so the older /export route returns a 404-equivalent guard. No impact on phase 5 export functionality. |

No blockers or warnings found.

---

### Human Verification Required

#### 1. Live Zenodo DOI Issuance

**Test:** Configure a real or sandbox ZENODO_API_TOKEN. Log in as admin. Run POST /admin/exports/regenerate to populate static/exports/. Run POST /admin/exports/publish-zenodo. Confirm the response contains a DOI string. Confirm data/zenodo_meta.json is updated with a real deposition_id and doi. Visit any page and confirm the DOI badge appears in the navbar.
**Expected:** data/zenodo_meta.json contains a real DOI (e.g., `10.5281/zenodo.XXXXXXX`). Navbar shows "Cite: 10.5281/zenodo.XXXXXXX" as a link. Subsequent publish calls (with same deposition_id) create a new version rather than a new record.
**Why human:** Requires a real Zenodo account and API token. Cannot mock the Zenodo response chain (create deposit, upload files, set metadata, publish) without live credentials. This is the only gap between the mechanism being fully coded and EXPRT-04 being fully realized.

---

### Gaps Summary

No code gaps. All four requirements have complete, wired, substantive implementations verified against the actual codebase.

EXPRT-04 is in a "mechanism complete, action pending" state: the Zenodo publish workflow is fully implemented (zenodo_uploader.py, admin route, DOI persistence), but a live DOI has not been issued because it requires a real ZENODO_API_TOKEN. This is an operational step, not a code deficiency. The plan explicitly scoped verification to the 503 graceful guard rather than requiring live publishing.

The 66 existing tests all pass with no regressions.

---

## Summary

The phase goal is achieved at the code level. The curated database is downloadable via four public routes in GMT and RDF/Turtle formats that bioinformatics tools consume directly. The Zenodo DOI registration mechanism is fully implemented and wired. A live DOI issuance requires a one-time human action with a real API token — this is operational configuration, not missing code.

---

_Verified: 2026-02-22T16:00:00Z_
_Verifier: Claude (gsd-verifier)_
