# Architecture Research

**Domain:** Bioinformatics curation database REST API — biological pathway annotation tool
**Researched:** 2026-02-19
**Confidence:** HIGH

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client Layer                                  │
│  ┌────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │
│  │ Browser / UI   │  │  R (httr2)      │  │ Python (requests/   │   │
│  │ (Jinja2 pages) │  │  scripts        │  │ pandas) scripts     │   │
│  └───────┬────────┘  └────────┬────────┘  └──────────┬──────────┘   │
└──────────┼────────────────────┼───────────────────────┼─────────────┘
           │ HTML/forms         │ GET /api/v1/*          │ GET /api/v1/*
           ▼                    ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Flask Blueprint Layer                         │
├───────────────┬──────────────┬──────────────┬──────────────────────┤
│  main_bp      │  api_bp      │  admin_bp    │  auth_bp             │
│  (page routes)│  (current)   │  (/admin/*)  │  (GitHub OAuth)      │
│               │              │              │                       │
│  [proposed]   │  [proposed]  │              │                       │
│  v1_api_bp    │  keep as     │              │                       │
│  (/api/v1/*)  │  internal UI │              │                       │
│               │  API only    │              │                       │
└───────────────┴──────┬───────┴──────────────┴──────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Service Container (DI)                          │
│  ┌─────────────────┐  ┌────────────────┐  ┌────────────────────┐   │
│  │ MappingModel    │  │ PathwaySuggest │  │ GOSuggestionSvc    │   │
│  │ GoMappingModel  │  │ Service        │  │                    │   │
│  └─────────────────┘  └────────────────┘  └────────────────────┘   │
│  ┌─────────────────┐  ┌────────────────┐  ┌────────────────────┐   │
│  │ EmbeddingService│  │ CacheModel     │  │ RateLimiter        │   │
│  │ (BioBERT)       │  │ (SPARQL cache) │  │ MetricsCollector   │   │
│  └─────────────────┘  └────────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Data Layer                                    │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │  SQLite DB       │  │ Pre-computed     │  │ SPARQL Endpoints │   │
│  │  (mappings,      │  │ Embeddings       │  │ (AOP-Wiki,       │   │
│  │  proposals,      │  │ (.npy/.json)     │  │ WikiPathways)    │   │
│  │  go_mappings)    │  │                  │  │                  │   │
│  └─────────────────┘  └──────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `v1_api_bp` (new) | Stable versioned REST API for downstream R/Python consumers | Flask Blueprint, `url_prefix="/api/v1"` |
| `api_bp` (existing) | Internal UI API (suggestions, SPARQL proxies, form submissions) | Existing Flask Blueprint — retain as-is |
| `ServiceContainer` | Dependency injection of all models and services | Existing singleton; v1 blueprint reads from same container |
| `MappingModel` | CRUD + filtering + paginated queries for KE-WP mappings | Add `get_mappings_paginated()` method |
| `GoMappingModel` | CRUD + filtering + paginated queries for KE-GO mappings | Add `get_go_mappings_paginated()` method |
| Exporters | Stable serialisation to JSON, CSV, RDF, TSV, Parquet | Existing `src/exporters/` — freeze column names |
| Response schema | Consistent envelope structure for all v1 responses | Explicit dicts or marshmallow schemas |

---

## How Biological Database APIs Are Structured

### ChEMBL (EBI, Django-based, most mature reference)

ChEMBL is the leading reference for bioinformatics REST API design. Key patterns:

**URL structure:**
```
https://www.ebi.ac.uk/chembl/api/data/molecule.json
https://www.ebi.ac.uk/chembl/api/data/activity?limit=20&offset=40
https://www.ebi.ac.uk/chembl/api/data/molecule/CHEMBL25
```

**Pagination — offset/limit envelope:**
```json
{
  "molecules": [ ... ],
  "page_meta": {
    "limit": 20,
    "offset": 0,
    "total_count": 13520737,
    "next": "/chembl/api/data/molecule.json?limit=20&offset=20",
    "previous": null
  }
}
```
- Default limit: 20. Maximum limit: 1000.
- `next` / `previous` are relative URL strings — clients follow them directly.
- Offset-based (not cursor-based): appropriate for a stable, mostly-append dataset.

**Filtering — Django QuerySet syntax over URL:**
```
?molecule_properties__mw_freebase__lte=300
?assay_type=B&order_by=-activity_id
```
Double-underscore separates field, nested block, and filter type. Multiple filters joined with `&`.

**Content negotiation:**
- Format specified as URL extension: `.json`, `.xml`, `.sdf`
- Alternatively via `Accept` header
- Default is XML if unspecified (legacy; all new bioinformatics APIs default to JSON)

**Versioning:** Current stable is v2. The URL path does not embed the version (EBI's model), but the API documentation has a version field in the discovery endpoint.

---

### WikiPathways (2024 architecture)

WikiPathways deprecated its SOAP webservices and moved to static JSON flat files + SPARQL as the canonical access method:

**Pathway data URL pattern:**
```
https://www.wikipathways.org/wikipathways-assets/pathways/{WPID}/{WPID}.json
https://www.wikipathways.org/json/
```

**Bulk download pattern (monthly releases):**
```
https://data.wikipathways.org/20240110/gpml/wikipathways-20240110-gpml-Homo_sapiens.zip
```

**Key design decision:** WikiPathways moved away from per-resource REST endpoints to bulk-download flat files + SPARQL for filtering. The SPARQL endpoint (`https://sparql.wikipathways.org/sparql`) is the primary API for dynamic queries.

**R client (rWikiPathways) and Python client (pywikipathways)** are maintained as thin wrappers around these patterns.

**Lesson for this project:** Providing a full pre-computed downloadable CSV/JSON dump alongside the paginated API is critical — bioinformaticians will prefer the bulk download for any analysis work. Individual endpoint pagination is for interactive exploration only.

---

### Reactome (Spring MVC ContentService, OpenAPI-documented)

**Base URL:** `https://reactome.org/ContentService/`

**URL structure:**
```
GET /data/database/version
GET /data/query/{id}/displayName
GET /data/event/{id}/participatingPhysicalEntities
GET /data/schema/{className}/count?species=9606
```

**Pagination:**
```
?pageSize=20&page=1
```
- Uses `page` (1-indexed) and `pageSize` parameters.
- Returns full result set if pagination parameters omitted (dangerous for large schemas, used for small sets).
- Maximum 25 entries per page for schema class queries.

**Versioning:** Versioning is via the database version (e.g., v88), not URL path. The `/data/database/version` endpoint returns the current version. Breaking API changes are handled via a full deprecation cycle (the old RESTful API was deprecated in v68 and replaced with ContentService).

**Content-type:** JSON by default. `Accept: application/json` explicit. Swagger/OpenAPI documentation available at the base URL.

---

### AOP-Wiki API (VHP4Safety deployment)

**Base URL:** `https://aopwiki-api.cloud.vhp4safety.nl/`

**Pattern:** Standard REST with Swagger UI. Endpoints documented interactively. JSON responses. GET-based, compatible with R `httr` and Python `requests`.

**Key detail:** The AOP-Wiki API is separate from the SPARQL endpoint this project already uses. The REST API provides structured JSON access to AOP/KE/KER data without requiring SPARQL.

---

## Recommended REST API Architecture for This Project

### Blueprint Structure (Adding v1 API to Existing App)

The key insight from PITFALLS.md (#1): the existing `api_bp` Blueprint has no `url_prefix` — routes like `/suggest_pathways/<ke_id>` are at root level. These are UI-internal endpoints and should stay at their current paths. A **new, separate Blueprint** provides the stable public REST API.

```python
# In app.py — register NEW blueprint alongside existing ones:
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)          # Existing — UI-internal, no change
app.register_blueprint(admin_bp)
app.register_blueprint(v1_api_bp)       # NEW — /api/v1/* stable public API
```

```python
# src/blueprints/v1_api.py
v1_api_bp = Blueprint("v1_api", __name__, url_prefix="/api/v1")

@v1_api_bp.route("/mappings", methods=["GET"])   # Public, no auth required
def get_mappings():
    ...

@v1_api_bp.route("/mappings/<int:mapping_id>", methods=["GET"])
def get_mapping(mapping_id):
    ...
```

**Critical design rule:** All endpoints under `/api/v1/` must be public (no authentication for GET). Write operations (POST) require auth. See PITFALLS.md #12 — GitHub OAuth must not gate read-only API access.

---

### URL Endpoint Design

Following ChEMBL conventions adapted to this project's domain:

```
# Mapping collections (paginated, filterable)
GET /api/v1/mappings                     KE-WP mappings (approved)
GET /api/v1/mappings/<id>                Single KE-WP mapping by ID
GET /api/v1/go-mappings                  KE-GO mappings (approved)
GET /api/v1/go-mappings/<id>             Single KE-GO mapping by ID

# Filtered sub-collections
GET /api/v1/mappings?ke_id=KE%2055       Filter by KE
GET /api/v1/mappings?wp_id=WP4           Filter by pathway
GET /api/v1/mappings?confidence=high     Filter by confidence level
GET /api/v1/mappings?connection_type=upstream  Filter by connection type
GET /api/v1/mappings?aop_id=AOP%201     Filter by AOP (requires JOIN to SPARQL data)

# Metadata lookups
GET /api/v1/ke/<ke_id>                   KE metadata (from ke_metadata.json)
GET /api/v1/pathway/<wp_id>              Pathway metadata (from pathway_metadata.json)

# Discovery and versioning
GET /api/v1/                             API discovery: version, schema, available resources
GET /api/v1/schema                       Response schema definitions
GET /health                              Health check (already exists, keep at root)

# Exports (already exist — preserve these paths, add schema version headers)
GET /export/json                         Full dataset JSON (existing)
GET /export/csv                          Full dataset CSV (existing)
GET /export/rdf                          Full dataset RDF/Turtle (existing)
GET /export/parquet                      Full dataset Parquet (existing)
```

**Do not expose** suggestion endpoints (`/suggest_pathways/*`, `/suggest_go_terms/*`) under `/api/v1/`. These are computationally expensive UI-internal endpoints. Bulk suggestion consumers should download the pre-computed export instead.

---

### Pagination Convention

Follow ChEMBL's offset/limit model — appropriate for this dataset (stable, append-only approved mappings):

**Request:**
```
GET /api/v1/mappings?limit=100&offset=0
GET /api/v1/mappings?limit=100&offset=100
```

**Response envelope:**
```json
{
  "mappings": [
    {
      "id": 42,
      "ke_id": "KE 55",
      "ke_title": "Inhibition of AChE",
      "wp_id": "WP4685",
      "wp_title": "Acetylcholine Synthesis",
      "connection_type": "upstream",
      "confidence_level": "high",
      "created_by": "github_username",
      "created_at": "2025-11-12T14:23:00Z",
      "updated_at": "2025-11-12T14:23:00Z"
    }
  ],
  "page_meta": {
    "limit": 100,
    "offset": 0,
    "total_count": 347,
    "next": "/api/v1/mappings?limit=100&offset=100",
    "previous": null
  },
  "schema_version": "1.0"
}
```

**Rationale for offset vs cursor:**
- Offset pagination is what httr2's `iterate_with_offset()` and Python's simple loop patterns handle natively — no custom pagination logic needed by consumers.
- The dataset is small (hundreds of mappings, not millions) and append-mostly — the data consistency advantages of cursor pagination are not worth the added complexity for this use case.
- Cursor pagination would be appropriate if the dataset were millions of records or if deletions were common.

**Parameters:**
- `limit`: 1–1000, default 100. For this dataset, returning all records in one call (`limit=1000`) is acceptable.
- `offset`: 0-indexed, default 0.
- `order_by`: field name, prefix with `-` for descending. E.g., `order_by=-created_at`.

---

### Filtering Convention

Simple query parameter filtering, following the domain-appropriate subset of ChEMBL's model:

```
GET /api/v1/mappings?ke_id=KE+55
GET /api/v1/mappings?wp_id=WP4685
GET /api/v1/mappings?confidence_level=high
GET /api/v1/mappings?connection_type=upstream
GET /api/v1/mappings?created_by=username
GET /api/v1/go-mappings?ke_id=KE+55
GET /api/v1/go-mappings?go_id=GO:0006955
GET /api/v1/go-mappings?confidence_level=medium,high   (comma-separated multi-value)
```

**Avoided complexity:** ChEMBL's `__lte`, `__contains` filter syntax is appropriate for a general-purpose chemistry database. For this dataset (4 filterable dimensions with known enum values), simple equality filters are sufficient. Do not add Django-style double-underscore syntax unless a concrete consumer need arises.

---

### Content Negotiation

Bioinformatics APIs (EMBL-EBI style) support multiple formats via:
1. `Accept` header (preferred)
2. URL extension (`.json`, `.csv`) as fallback
3. `format=json` query parameter as last resort

For this project, implement all three for the `/api/v1/mappings` and `/api/v1/go-mappings` endpoints:

```
Accept: application/json           → JSON (default)
Accept: text/csv                   → CSV
Accept: text/turtle                → Turtle RDF
Accept: application/rdf+xml        → RDF/XML
Accept: application/vnd.ms-excel   → (not supported in v1)
```

**Implementation pattern in Flask:**
```python
from flask import request, jsonify

@v1_api_bp.route("/mappings", methods=["GET"])
def get_mappings():
    accept = request.headers.get("Accept", "application/json")

    mappings = get_paginated_mappings(request.args)

    if "text/csv" in accept:
        return generate_csv_response(mappings)
    elif "text/turtle" in accept:
        return generate_turtle_response(mappings)
    elif "application/rdf+xml" in accept:
        return generate_rdf_response(mappings)
    else:
        return jsonify(build_envelope(mappings))
```

**Note:** The existing `/export/<format>` routes in `main_bp` serve the full dataset as downloads. The v1 API content negotiation serves paginated/filtered subsets. These are complementary, not redundant.

---

### Stable Response Schema

Following PITFALLS.md #6 (stable identifiers) and #10 (export schema stability):

**Contract rules:**
1. Field names in `/api/v1/` responses are permanently fixed once published. Never rename. Add new fields as additive changes.
2. Always return both stable identifier (`ke_id`, `wp_id`, `go_id`) and display string (`ke_title`, `wp_title`, `go_name`).
3. Include `schema_version: "1.0"` in every response envelope.
4. Timestamps are always UTC ISO 8601: `"2025-11-12T14:23:00Z"`.
5. `go_id` is normalized to colon format: `"GO:0006955"` (not `"GO_0006955"`).
6. `ke_id` uses AOP-Wiki format: `"KE 55"` (with space, as stored in DB).

**Discovery endpoint response:**
```json
{
  "api_version": "1.0",
  "schema_version": "1.0",
  "database_version": "v1.0.0",
  "base_url": "https://yourapp.org/api/v1",
  "resources": {
    "mappings": "/api/v1/mappings",
    "go_mappings": "/api/v1/go-mappings"
  },
  "documentation": "/documentation/api",
  "timestamp": "2026-02-19T10:00:00Z"
}
```

---

### Rate Limiting and Consumer Guidance

From PITFALLS.md #9: rate limit responses must include `Retry-After` headers and meaningful error messages. The `/api/v1/` blueprint should have a more generous rate limit than the UI endpoints (which are SPARQL-backed and expensive), because v1 API endpoints only read from SQLite.

```python
# Different rate limits for different endpoint classes
@v1_api_bp.route("/mappings")
@v1_general_rate_limit    # 1000 req/hour — SQLite reads only
def get_mappings():
    ...

# vs. existing UI endpoints
@api_bp.route("/suggest_pathways/<ke_id>")
@sparql_rate_limit         # 500 req/hour — SPARQL-backed
def suggest_pathways(ke_id):
    ...
```

On 429 responses:
```python
response.headers["Retry-After"] = str(reset_seconds)
response.headers["X-RateLimit-Limit"] = str(limit)
response.headers["X-RateLimit-Remaining"] = str(remaining)
```

---

## Recommended Project Structure (REST API Addition)

The REST API layer fits into the existing blueprint architecture with minimal disruption:

```
src/
├── blueprints/
│   ├── api.py              # Existing — UI-internal API (no change)
│   ├── main.py             # Existing — page routes + bulk exports (no change)
│   ├── admin.py            # Existing (no change)
│   ├── auth.py             # Existing (no change)
│   └── v1_api.py           # NEW — stable public REST API (/api/v1/*)
├── core/
│   ├── models.py           # Add paginated query methods to MappingModel/GoMappingModel
│   ├── schemas.py          # Add v1 API response schemas (marshmallow or explicit dicts)
│   └── config.py           # (no change)
├── services/
│   └── container.py        # (no change — v1_api_bp reads same container)
└── exporters/
    ├── json_exporter.py    # Add schema_version to output (minor change)
    ├── rdf_exporter.py     # (no change)
    ├── excel_exporter.py   # (no change)
    └── parquet_exporter.py # (no change)
```

### Structure Rationale

- **`v1_api.py` as a separate file:** Keeps the stable public contract isolated from the internal UI API (`api.py`). When breaking changes are needed, `v2_api.py` can be added without touching `api.py` or `v1_api.py`.
- **Models get paginated methods:** `MappingModel.get_mappings_paginated(filters, limit, offset)` and `GoMappingModel.get_go_mappings_paginated(filters, limit, offset)` — these are data access methods, not HTTP-layer concerns.
- **Schemas frozen separately:** The marshmallow (or dict-based) response schemas for v1 must be explicitly versioned. Do not reuse the same schema objects as the UI API — they will diverge.

---

## Architectural Patterns

### Pattern 1: Dual-Blueprint Split (Internal UI API vs. Stable Public API)

**What:** Two Flask Blueprints serving different contracts: `api_bp` for UI-internal endpoints that can change freely, `v1_api_bp` for the public REST API that is frozen at v1.

**When to use:** When an app already has internal API endpoints that power its own UI and you need to expose a stable subset to external consumers without constraining the internal API's evolution.

**Trade-offs:**
- Pro: Zero risk of breaking internal UI by adding versioning constraints on a subset
- Pro: Clear contract boundary — developers know `api_bp` can change freely, `v1_api_bp` cannot
- Con: Some code duplication (both blueprints may query the same data)
- Con: Must explicitly maintain the stable contract — no automatic protection

**Example:**
```python
# app.py
app.register_blueprint(api_bp)           # url_prefix=None — UI-internal
app.register_blueprint(v1_api_bp)        # url_prefix="/api/v1" — public stable

# v1_api.py
v1_api_bp = Blueprint("v1_api", __name__, url_prefix="/api/v1")

@v1_api_bp.route("/mappings", methods=["GET"])
def list_mappings():
    """Stable public endpoint — field names are a contract."""
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    filters = extract_filters(request.args)

    data, total = mapping_model.get_mappings_paginated(filters, limit, offset)
    return jsonify(build_envelope("mappings", data, total, limit, offset))
```

---

### Pattern 2: ChEMBL-style Pagination Envelope

**What:** Every list response wraps items in a named key (the resource name) plus a `page_meta` block with `total_count`, `limit`, `offset`, `next`, `previous`.

**When to use:** Always, for any collection endpoint. Never return a bare array at the top level.

**Trade-offs:**
- Pro: Clients know total size without making an additional request
- Pro: `next`/`previous` URLs mean clients do not need to construct pagination URLs
- Pro: httr2's `iterate_with_next_url()` and `iterate_with_offset()` both work natively
- Con: Slightly more verbose response; irrelevant for this dataset size

**Example:**
```python
def build_envelope(resource_name, items, total_count, limit, offset, base_url):
    has_next = (offset + limit) < total_count
    has_prev = offset > 0
    return {
        resource_name: items,
        "page_meta": {
            "limit": limit,
            "offset": offset,
            "total_count": total_count,
            "next": f"{base_url}?limit={limit}&offset={offset + limit}" if has_next else None,
            "previous": f"{base_url}?limit={limit}&offset={max(0, offset - limit)}" if has_prev else None,
        },
        "schema_version": "1.0"
    }
```

---

### Pattern 3: Content Negotiation via Accept Header (with Format Fallback)

**What:** The same endpoint URL returns JSON, CSV, or RDF depending on the `Accept` header. URL extension (`.json`, `.csv`) and `?format=` parameter serve as fallbacks for clients that cannot set headers.

**When to use:** For `/api/v1/mappings` and `/api/v1/go-mappings`. Not needed for single-resource endpoints.

**Trade-offs:**
- Pro: Canonical URL (one URL, one resource) — correct REST semantics
- Pro: R `httr2::req_headers(Accept = "text/csv")` and Python `requests.get(..., headers={"Accept": "text/csv"})` work with no extra parameters
- Con: More complex view function
- Con: URL extension fallback requires route-level handling

**Priority order for Accept header matching:**
1. `text/csv` → CSV response (tabular; most common for R/Python workflows)
2. `text/turtle` → Turtle RDF (semantic web consumers)
3. `application/rdf+xml` → RDF/XML
4. `application/json` or `*/*` → JSON (default)

---

### Pattern 4: Bulk Download as Primary Distribution Channel

**What:** Pre-computed static files (CSV, JSON, RDF) are provided as direct downloads. The paginated API is for selective access; the bulk download is for full-dataset analysis.

**When to use:** Always, for any bioinformatics dataset. WikiPathways is the reference: their canonical distribution is flat files, not per-record API calls.

**Trade-offs:**
- Pro: Eliminates rate limiting concerns for researchers who need all data
- Pro: Cacheable by CDN; no server load
- Pro: Citable — a DOI can point to a specific version of the download file
- Con: Static files go stale; need a generation/versioning strategy
- Con: Cannot be filtered — researchers get everything

**How it fits this project:** The `/export/<format>` endpoints in `main_bp` already exist. The work is:
1. Add `schema_version` metadata to all export files (PITFALLS.md #10)
2. Add a `Last-Modified` header to export responses
3. Link to bulk downloads prominently from the API discovery endpoint
4. Make exports publicly accessible without GitHub OAuth (PITFALLS.md #12)

---

## Data Flow

### REST API Request Flow (v1 API Blueprint)

```
GET /api/v1/mappings?ke_id=KE+55&confidence_level=high&limit=50
    |
    v
v1_api_bp route handler
    |
    ├── Parse + validate query parameters
    |   (limit, offset, filters — all from request.args)
    |
    ├── mapping_model.get_mappings_paginated(filters, limit, offset)
    |       |
    |       └── SQLite SELECT with WHERE clause + LIMIT/OFFSET
    |           (no SPARQL, no embedding service — reads only from DB)
    |
    ├── Determine Accept header format
    |
    ├── if JSON → jsonify(build_envelope(...))
    |   if CSV  → StreamingResponse with csv.writer
    |   if RDF  → RDFExporter.export_filtered(mappings)
    |
    └── Return response with:
        - Content-Type header
        - X-RateLimit-* headers
        - schema_version in body
```

### Content Negotiation Flow

```
Request with Accept: text/csv
    |
    v
Flask route handler checks request.headers.get("Accept")
    |
    ├── "text/csv" matched?
    |       └── Build CSV with stable column order:
    |           id, ke_id, ke_title, wp_id, wp_title,
    |           connection_type, confidence_level,
    |           created_by, created_at, updated_at, schema_version
    |
    ├── "text/turtle" matched?
    |       └── RDFExporter.export_turtle(filtered_mappings)
    |
    └── default → JSON envelope
```

### Existing Export Flow (Unchanged)

```
GET /export/json  (full dataset, no filters, direct download)
    |
    v
main_bp.export_data()
    |
    └── mapping_model.get_all_mappings() + go_mapping_model.get_all_mappings()
    |
    └── JSONExporter → streaming response
        (add schema_version field to output — minor change)
```

### Key Data Flow Rules

1. **v1 API reads only from SQLite** — no SPARQL calls, no embedding service. This keeps latency predictable and rate limits generous.
2. **Suggestion endpoints remain in `api_bp`** — they are UI-internal, SPARQL-backed, and computationally expensive. They are explicitly not part of the stable public API.
3. **All v1 responses include `schema_version`** — enables consumers to detect breaking changes.
4. **Auth is only required for write operations** — GET on `/api/v1/*` is public.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-500 curators / small research community | Current SQLite setup is sufficient. Offset pagination at `limit=1000` returns all records in one call. No infrastructure changes needed. |
| 500-5000 API consumers (post-publication) | Enable SQLite WAL mode (PITFALLS.md #3). Add HTTP caching headers (`Cache-Control: public, max-age=300`) on GET endpoints. Consider serving export files from a CDN. |
| 5000+ consumers | SQLite becomes the bottleneck for concurrent reads. Migrate database to PostgreSQL. The Blueprint/service architecture supports this without API changes. |

### Scaling Priorities

1. **First bottleneck:** SQLite read concurrency under multi-worker Gunicorn. Fix: WAL mode + `--preload-app` (PITFALLS.md #2, #3). No API changes required.
2. **Second bottleneck:** Suggestion endpoints under research script load. Fix: bulk download CSV/JSON eliminates the need to call suggestion endpoints programmatically.

---

## Anti-Patterns

### Anti-Pattern 1: Exposing Suggestion Endpoints in the Public REST API

**What people do:** Add `/api/v1/suggestions/ke/<ke_id>` to the stable public API to make the ML-powered suggestion feature accessible to R/Python consumers.

**Why it's wrong:** Suggestion endpoints call SPARQL (external, latency-variable), run BioBERT inference (CPU-bound, ~200ms), and return non-deterministic results (scores change when embeddings are regenerated — PITFALLS.md #7). They cannot satisfy the stability contract of a v1 API. A research script calling `GET /api/v1/suggestions/ke/KE+55` on Monday and Tuesday may get different ranked results after embedding regeneration.

**Do this instead:** Provide the pre-computed suggestion scores as a downloadable CSV generated at each dataset release. If programmatic access is needed, expose a clearly labeled "experimental" endpoint outside the `/api/v1/` namespace with documented caveats about score stability.

---

### Anti-Pattern 2: Bare Array Top-Level Response

**What people do:** Return `[{"ke_id": "KE 55", ...}, ...]` directly as the response body (no envelope).

**Why it's wrong:** R `httr2` and Python `requests.json()` will return a list, not a dict. The consumer has no way to know total count, whether there are more pages, or what schema version the data conforms to. Adding an envelope later is a breaking change.

**Do this instead:** Always wrap in `{"mappings": [...], "page_meta": {...}, "schema_version": "1.0"}` from day one, even for endpoints that currently return all records. The wrapper costs nothing and prevents a painful breaking change.

---

### Anti-Pattern 3: Adding Auth to Read-Only Public Endpoints

**What people do:** Apply `@login_required` to all endpoints, including read-only `GET /api/v1/mappings`, because the existing UI API does it and it's the safe default.

**Why it's wrong:** The dataset is a curated scientific resource intended for the research community. Requiring GitHub OAuth to read published mappings excludes R/Python scripts without interactive OAuth flows, reviewers verifying the paper's supplementary data, and bioinformaticians who do not have GitHub accounts. See PITFALLS.md #12.

**Do this instead:** Apply `@login_required` only to write operations (`POST /submit`, `POST /propose`). All `GET` endpoints on `/api/v1/` are publicly accessible without authentication. Rate limit public endpoints separately (more permissive limits) from authenticated endpoints.

---

### Anti-Pattern 4: Mixing Stable Public API with UI-Internal Endpoints

**What people do:** Add the public API endpoints to the existing `api_bp` Blueprint (the one that already has `/suggest_pathways/`, `/check`, `/submit`, etc.) with a `/api/v1/` prefix on individual route decorators.

**Why it's wrong:** The existing `api_bp` Blueprint has `url_prefix=None`. Adding per-route version prefixes means the routes are scattered and inconsistently versioned. The contract between "stable public API" and "internal UI API" becomes invisible. When a developer adds a new internal endpoint, they might not notice it's in the same blueprint as the public API.

**Do this instead:** Create `v1_api_bp` as a completely separate Blueprint registered with `url_prefix="/api/v1"`. The separation makes the contract boundary explicit in the code structure itself.

---

### Anti-Pattern 5: Offset Pagination Without `total_count`

**What people do:** Return `{"data": [...], "next": "/api/v1/mappings?offset=100"}` without `total_count`.

**Why it's wrong:** R and Python consumers cannot build a progress bar, cannot pre-allocate a data frame, and cannot know when to stop paginating except by detecting an empty page. httr2's `iterate_with_offset()` helper works correctly only if it can detect the final page, which requires either an empty `data` array or a `total_count` field.

**Do this instead:** Always include `total_count` in `page_meta`. For this dataset, the query cost of `SELECT COUNT(*)` is negligible.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| AOP-Wiki SPARQL | Cached SPARQL queries via existing `CacheModel` | v1 API does NOT call SPARQL — pre-computed ke_metadata.json used instead |
| WikiPathways SPARQL | Same as above | v1 API returns stored pathway data only |
| GitHub OAuth | Session-based; `@login_required` decorator | Write endpoints on v1 API require session auth |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `v1_api_bp` → `MappingModel` | Direct method call via module-level globals (existing pattern in `api_bp`) | Same `set_models()` injection pattern; use ServiceContainer |
| `v1_api_bp` → `GoMappingModel` | Same as above | |
| `v1_api_bp` → `RDFExporter` | Direct instantiation or via a shared helper | For content-negotiated RDF responses |
| `v1_api_bp` → `api_bp` | No direct dependency | The two blueprints are independent; both read from the same models |

---

## Suggested Build Order

Phases are ordered by dependency. Each phase must be complete before the next is started.

```
Phase 1: Data model foundation (no API yet)
  ├── Add paginated query methods to MappingModel and GoMappingModel
  │       MappingModel.get_mappings_paginated(filters, limit, offset) → (List[Dict], int)
  │       GoMappingModel.get_go_mappings_paginated(filters, limit, offset) → (List[Dict], int)
  ├── Normalize go_id format on insert (colon: "GO:0006955")
  └── Add schema_version metadata to existing /export/* responses

Phase 2: v1 Blueprint skeleton + discovery endpoint
  ├── Create src/blueprints/v1_api.py with url_prefix="/api/v1"
  ├── Register v1_api_bp in app.py
  ├── Implement GET /api/v1/ (discovery endpoint — returns schema info)
  └── Implement GET /api/v1/schema (field definitions)
      DEPENDENCY: Phase 1 (paginated queries must exist)

Phase 3: Collection endpoints (JSON only)
  ├── GET /api/v1/mappings (paginated, filterable, JSON envelope)
  ├── GET /api/v1/mappings/<id> (single resource)
  ├── GET /api/v1/go-mappings (paginated, filterable)
  ├── GET /api/v1/go-mappings/<id>
  └── Rate limit headers on all responses
      DEPENDENCY: Phase 2 (blueprint registered)

Phase 4: Content negotiation (CSV and RDF formats)
  ├── Add Accept header dispatch to collection endpoints
  ├── CSV format (text/csv) → stable column order
  └── Turtle RDF (text/turtle) → reuse existing RDFExporter
      DEPENDENCY: Phase 3 (JSON endpoints must work first)

Phase 5: Public access + rate limit tuning
  ├── Remove auth requirement from all v1 GET endpoints
  ├── Add Retry-After header to 429 responses
  └── Set generous rate limits for public read-only endpoints
      DEPENDENCY: Phase 3

Phase 6: API documentation
  ├── Add OpenAPI spec (flasgger or flask-restx)
  ├── Link from /documentation/api page
  └── Include consumer code examples (R httr2, Python requests)
      DEPENDENCY: Phase 3 (endpoints must exist before docs are written)
```

**Build order rationale:**
- Paginated DB queries (Phase 1) are the foundation — all subsequent phases depend on them
- The discovery endpoint (Phase 2) lets consumers self-orient before individual endpoints exist
- JSON only first (Phase 3) — validate the contract before adding format complexity
- Content negotiation (Phase 4) is independent of auth (Phase 5) — can parallelize after Phase 3
- Documentation last (Phase 6) — API must be stable before investing in docs

---

## Sources

- [ChEMBL Data Web Services documentation](https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services)
- [Using the New ChEMBL Web Services](https://chembl.github.io/using-new-chembl-web-services/)
- [WikiPathways JSON API](https://www.wikipathways.org/json/)
- [WikiPathways 2024: next generation pathway database (NAR)](https://academic.oup.com/nar/article/52/D1/D679/7369835)
- [Reactome Content Service](https://reactome.org/dev/content-service)
- [AOP-Wiki API Tutorial (VHP4Safety)](https://docs.vhp4safety.nl/en/latest/tutorials/aopwikiapi/aopwikiapi.html)
- [Eleven quick tips to build a usable REST API for life sciences — Tarkowska et al., PLOS Computational Biology 2018](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1006542)
- [httr2 pagination helpers: iterate_with_offset, iterate_with_cursor](https://httr2.r-lib.org/reference/iterate_with_offset.html)
- [Flask blueprint versioning pattern](https://www.codingeasypeasy.com/blog/versioning-flask-apis-a-comprehensive-guide-with-best-practices-and-examples)
- [Offset vs Cursor-Based Pagination: choosing the right approach](https://medium.com/@maryam-bit/offset-vs-cursor-based-pagination-choosing-the-best-approach-2e93702a118b)
- `.planning/research/STACK.md` — existing stack research (same project)
- `.planning/research/PITFALLS.md` — existing pitfalls research (same project)
- `.claude/architecture.md` — existing system architecture documentation

---
*Architecture research for: Bioinformatics curation database REST API (KE-WP/KE-GO mapping tool)*
*Researched: 2026-02-19*
