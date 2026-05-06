---
phase: 26-public-api-and-exports
plan: "08"
subsystem: docs
tags: [openapi, downloads, docs_api, reactome, documentation]
status: partial-checkpoint
requires:
  - phase: 26
    plan: "05"
    why: Defines /api/v1/reactome-mappings JSON shape via _serialize_reactome_mapping
  - phase: 26
    plan: "06"
    why: Provides /exports/gmt/ke-reactome*, /exports/rdf/ke-reactome download endpoints
provides:
  - "static/openapi/openapi.yaml: /reactome-mappings paths + ReactomeMapping/ReactomeMappingsResponse schemas"
  - "templates/downloads.html: 3 new Reactome cards (2 orange GMT + 1 dark RDF)"
  - "templates/docs_api.html: Python + R consumer examples for /api/v1/reactome-mappings"
  - "static/css/main.css: download-card--orange, download-card__badge--orange, btn-link-orange"
affects:
  - downloads page (UI)
  - /api/docs Swagger UI rendering of openapi.yaml
  - API Consumer Guide page rendering
tech-stack:
  added: []
  patterns:
    - "OpenAPI 3.0.3 path/schema mirror — copy GO block, swap term/id names + add aop_id parameter"
    - "Project palette CSS token reuse (--color-secondary-orange) for new visual variant"
    - "Reuse shared Provenance schema across WP/GO/Reactome (no separate ReactomeProvenance type)"
key-files:
  created: []
  modified:
    - "static/openapi/openapi.yaml"
    - "templates/downloads.html"
    - "templates/docs_api.html"
    - "static/css/main.css"
decisions:
  - "Reused shared Provenance component schema — Reactome's provenance fields (suggestion_score, approved_by, approved_at, proposed_by) are an exact subset of the existing schema, no parallel definition needed"
  - "Skipped global tags-block edit — openapi.yaml has no top-level tags: array; tags are referenced inline by operations only. KE-Reactome Mappings tag is established by inline usage on listReactomeMappings/getReactomeMapping operations (Swagger UI auto-creates groups from inline tags)"
  - "Orange CSS variant uses existing --color-secondary-orange (#EB5B25) brand token rather than introducing new palette entries"
  - "Card 6a (RDF) uses --dark badge per project convention that all RDF cards share dark theme; orange is reserved for the GMT cards only"
metrics:
  completed_date: "2026-05-06 (auto tasks only)"
  duration: ~25min auto tasks; checkpoint pending verification
---

# Phase 26 Plan 08: Documentation Surface (OpenAPI + downloads.html + docs_api.html) Summary

OpenAPI spec, downloads page, and API consumer guide now expose the Reactome public API surface — three documentation-only changes (D-21, D-22, D-23) covering REXP-01..03. **Partial summary at human-verify checkpoint** — auto tasks complete and committed; visual verification of the downloads page and docs_api.html in browser is the remaining gate.

## What Changed

### Task 1 — D-21: OpenAPI spec extension (`f4ecec1`)

`static/openapi/openapi.yaml` now describes the Reactome API:

- **Paths added (after `/go-mappings/{uuid}`, before `components:`):**
  - `GET /reactome-mappings` (operationId `listReactomeMappings`, tag `KE-Reactome Mappings`) with parameters `ke_id`, `reactome_id`, `confidence_level`, `aop_id`, `page`, `per_page`, `format`. 200 returns ReactomeMappingsResponse JSON or text/csv; 400 for invalid AOP / SPARQL unavailable; 429 shared TooManyRequests.
  - `GET /reactome-mappings/{uuid}` (operationId `getReactomeMapping`) — 200 wraps a single ReactomeMapping in `{ data: ... }`; 404 ErrorResponse; 429 shared.
- **Schemas added (next to GoMappingsResponse):**
  - `ReactomeMapping` — field-by-field mirror of `_serialize_reactome_mapping` (src/blueprints/v1_api.py:220): `uuid`, `ke_id`, `ke_name`, `reactome_id` (pattern `^R-HSA-[0-9]+$`), `pathway_name`, `species` (nullable), `confidence_level` (enum), `pathway_description` (nullable), `reactome_gene_count` (integer), `ke_aop_context` (array of strings), `ke_bio_level` (nullable), `provenance` (`$ref` shared `Provenance`).
  - `ReactomeMappingsResponse` — `{ data: [ReactomeMapping], pagination: $ref Pagination }`.
- **Reused unchanged:** `Pagination`, `Provenance`, `ErrorResponse`, `responses.TooManyRequests`.

### Task 2 — D-22: downloads.html cards + orange CSS variant (`f57b09f`)

`templates/downloads.html` gains three cards in PATTERNS-section-15 positions:

- **Card 2a (after Card 2 KE-GO GMT):** *KE-Reactome GMT* — orange variant, links to `/exports/gmt/ke-reactome` and `?min_confidence=High`.
- **Card 4a (after Card 4 KE-Centric GO GMT):** *KE-Centric Reactome GMT* — orange variant, links to `/exports/gmt/ke-reactome-centric` and `?min_confidence=High`.
- **Card 6a (after Card 6 KE-GO RDF):** *KE-Reactome RDF/Turtle* — `--dark` variant per project convention that RDF cards share dark theme.

`static/css/main.css` gains the new orange variant rules mirroring the existing blue/teal/dark structure:

- `.download-card--orange { border-top: 4px solid var(--color-secondary-orange); }`
- `.download-card__badge--orange { background: #fdece4; color: var(--color-secondary-orange); }`
- `.btn-link-orange { background: var(--color-secondary-orange); color: white; ... }`
- `.btn-link-orange:hover { opacity: 0.9; color: white; }`

Color uses the existing `--color-secondary-orange` token (#EB5B25, defined main.css:11) — no new palette entry.

### Task 3 — D-23: docs_api.html Reactome consumer example (`8c8d883`)

`templates/docs_api.html` now describes the Reactome API in the same shape as KE-WP/KE-GO:

- Intro paragraph mentions KE-Reactome alongside KE-WP and KE-GO.
- Endpoints Overview table gains two rows: `GET /api/v1/reactome-mappings` and `GET /api/v1/reactome-mappings/{uuid}`.
- Python (requests) section #6: paginated fetch, AOP/confidence filter, CSV download — uses production URL `https://molaop-builder.vhp4safety.nl/api/v1`.
- R (httr2) section #6: basic fetch + AOP filter, mirrors GO example shape.

## Verification Status

### Automated (all green)

| Check | Command | Result |
|-------|---------|--------|
| OpenAPI YAML parses | `python -c "import yaml; yaml.safe_load(open('static/openapi/openapi.yaml'))"` | exits 0 |
| `/reactome-mappings` path present | `grep -c "/reactome-mappings:" static/openapi/openapi.yaml` | 1 |
| `/reactome-mappings/{uuid}` path | same grep with `{uuid}` | 1 |
| Schemas | `grep -c "ReactomeMapping:\|ReactomeMappingsResponse:" static/openapi/openapi.yaml` | 2 |
| operationIds | `grep -c "operationId: listReactomeMappings\|operationId: getReactomeMapping"` | 2 |
| `aop_id` param (WP + Reactome) | `grep -c "name: aop_id"` | 2 |
| Reactome refs in downloads.html | `grep -c "ke-reactome"` | 5 |
| GMT route refs | `grep -c "/exports/gmt/ke-reactome"` | 4 |
| RDF route ref | `grep -c "/exports/rdf/ke-reactome"` | 1 |
| Orange-variant cards | `grep -c "download-card download-card--orange"` | 2 |
| Orange CSS class present | `grep -c "download-card--orange" static/css/main.css` | 1 |
| Reactome refs in docs_api.html | `grep -c "reactome-mappings"` | 7 |
| Production URL in consumer example | `grep -c "molaop-builder.vhp4safety.nl/api/v1/reactome-mappings"` | 2 |
| downloads.html Jinja parse | `Environment.get_template('downloads.html')` | ok |
| docs_api.html Jinja parse | `Environment.get_template('docs_api.html')` | ok |

### Pending — human-verify checkpoint

Visual verification of the downloads page styling (`download-card--orange` and orange badge/button rendering against the project palette), the API consumer guide rendering, and the Swagger UI grouping of the new operations under the KE-Reactome Mappings tag — see plan `<task type="checkpoint:human-verify">`.

## Deviations from Plan

**1. [Rule 3 — Blocking adjustment] Skipped EDIT 1 (global tags list)**
- **Found during:** Task 1
- **Issue:** Plan instructs to find the existing top-level `tags:` block and append a `KE-Reactome Mappings` entry. The current `static/openapi/openapi.yaml` has no global `tags:` array — tags are only referenced inline on operations (`tags: [- KE-WP Mappings]`).
- **Fix:** Did not introduce a global `tags:` block. The new operations carry `tags: [- KE-Reactome Mappings]` inline, matching the convention already used for KE-WP Mappings and KE-GO Mappings. Swagger UI auto-creates the section grouping from inline tag references, so the user-visible grouping behaviour matches the plan's intent.
- **Files modified:** `static/openapi/openapi.yaml` only (no global tags block added)
- **Commit:** `f4ecec1`
- **Impact:** Zero functional change versus plan intent — Swagger/Redoc still groups operations by tag value.

**2. [Rule 2 — Schema reuse] Used shared `Provenance` schema instead of inline provenance object**
- **Found during:** Task 1
- **Issue:** Plan's example schema for `ReactomeMapping.provenance` showed an inline object with the four provenance fields. The spec already defines a `Provenance` component schema with exactly those fields and re-uses it across `Mapping` and `GoMapping`.
- **Fix:** `ReactomeMapping.provenance` uses `$ref: "#/components/schemas/Provenance"` to stay consistent with WP/GO and avoid drift if Provenance ever changes.
- **Impact:** None — same on-the-wire shape.

**3. [Rule 2 — Documentation completeness] Added two endpoint rows to docs_api.html Endpoints Overview table**
- **Found during:** Task 3
- **Issue:** Plan only mentions adding consumer example code blocks. The page also has an "Endpoints Overview" table that lists all four existing endpoints; omitting Reactome there would be inconsistent.
- **Fix:** Added two rows for `GET /api/v1/reactome-mappings` and `GET /api/v1/reactome-mappings/{uuid}` matching the existing table styling.
- **Files modified:** `templates/docs_api.html`
- **Commit:** `8c8d883`
- **Impact:** Improves consistency; aligns with the plan's spirit (D-23 says "mirroring the GO example").

## Authentication Gates

None — all changes are documentation-only edits to YAML, HTML, and CSS files in the repository.

## Self-Check: PASSED

Files exist:
- `static/openapi/openapi.yaml` (modified) — FOUND
- `templates/downloads.html` (modified) — FOUND
- `templates/docs_api.html` (modified) — FOUND
- `static/css/main.css` (modified) — FOUND

Commits exist on this branch:
- `f4ecec1` (Task 1) — FOUND
- `f57b09f` (Task 2) — FOUND
- `8c8d883` (Task 3) — FOUND

All automated acceptance criteria pass; partial summary committed pending visual checkpoint approval.
