# Phase 3: Stable Public REST API - Research

**Researched:** 2026-02-20
**Domain:** Flask blueprint extension, REST API pagination, content negotiation, CORS
**Confidence:** HIGH

## Summary

Phase 3 adds a new Flask Blueprint (`v1_api_bp`) registered at `/api/v1/` — entirely separate from the existing `api_bp` which powers the internal UI. The codebase already has all prerequisite data: Phase 2 added `uuid`, `approved_by_curator`, `approved_at_curator`, `confidence_level`, and `suggestion_score` columns to both `mappings` and `ke_go_mappings`. Both models also expose `get_mapping_by_uuid()` and `get_go_mapping_by_uuid()` methods that return complete provenance-bearing rows. The new blueprint needs no schema changes — it only needs query methods on the existing models that support pagination and filtering.

The one gap is AOP-based filtering (`?aop_id=...` on `/api/v1/mappings`). AOP membership is not stored in the mapping database; the live `get_aop_kes()` endpoint in `api_bp` retrieves KE lists for an AOP from AOP-Wiki SPARQL with 24-hour caching. The public API must replicate that lookup, then filter mappings by the returned KE IDs. The existing `CacheModel` and SPARQL call pattern in `api.py` can be reused without modification.

The primary content negotiation requirement (API-04 — `Accept: text/csv` returns tabular CSV) is straightforwardly handled via Flask's `request.accept_mimetypes` and Python's built-in `csv` module. No additional library is needed. The `go_namespace` field requested in the CONTEXT decision does NOT exist in `go_bp_metadata.json` (confirmed by inspection: keys are `name`, `definition`, `is_a`, `part_of`, `synonyms`). The file covers only Biological Process terms since it is `go_bp_metadata.json`, so namespace can be hardcoded to `"biological_process"` for all GO mapping responses, or the phase must accept that the field is always `"biological_process"`.

**Primary recommendation:** Create `src/blueprints/v1_api.py` with a single `Blueprint("v1_api", __name__, url_prefix="/api/v1")`, add `get_mappings_paginated()` and `get_go_mappings_paginated()` query methods to `MappingModel` and `GoMappingModel`, apply CORS via a per-blueprint `after_request` hook (no new dependency), and use the existing rate-limiter decorator on all routes.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Response shape:**
- Full provenance on every mapping object: UUID, confidence_level at top level; suggestion_score, approved_by (curator GitHub username), approved_at nested under a `provenance` key
- Example structure:
  ```json
  {
    "uuid": "abc-123",
    "ke_id": 42,
    "ke_name": "Inhibition of Na+/I- symporter (NIS)",
    "pathway_id": "WP123",
    "pathway_title": "Thyroid hormone biosynthesis",
    "confidence_level": "High",
    "provenance": {
      "suggestion_score": 0.87,
      "approved_by": "marvin",
      "approved_at": "2026-01-15T10:00:00Z"
    }
  }
  ```
- KE-GO mapping objects additionally include `go_term_name` and `go_namespace` (Biological Process / Molecular Function / Cellular Component) alongside `go_term_id`
- All collection endpoints return `{"data": [...], "pagination": {...}}`; single-resource endpoints return `{"data": {...}}`

**Pagination:**
- Query params: `?page=1&per_page=50`
- Default: 50 per page; maximum: 200 per page
- Pagination envelope includes: `page`, `per_page`, `total`, `total_pages`, `next` (URL or null), `prev` (URL or null)

**Filtering scope:**
- `/api/v1/mappings` filters: `ke_id`, `aop_id`, `pathway_id`, `confidence_level` (all optional)
- `/api/v1/go-mappings` filters: `ke_id`, `go_term_id`, `confidence_level` (all optional)
- Single-resource lookup included: `GET /api/v1/mappings/<uuid>` and `GET /api/v1/go-mappings/<uuid>`
- No date-range filters (approved_after / approved_before) — out of scope

**Error contract:**
- All errors use simple flat body: `{"error": "<human-readable message>"}`
- Standard HTTP status codes: 400 for bad params, 404 for missing resource, 422 for validation failure, 429 for rate limit
- Rate limiting: basic 429 Too Many Requests — no `Retry-After` header (to be documented in Phase 6)
- Open CORS: `Access-Control-Allow-Origin: *` on all `/api/v1/` endpoints so R Shiny apps and Jupyter notebooks can call the API directly

### Claude's Discretion

- Multi-value filter encoding (comma-separated vs repeated params)
- Exact numeric rate limit threshold
- 404 response body for missing UUID (echo UUID or generic message)
- URL scheme for `next`/`prev` links (absolute vs relative)
- Whether to apply CORS via a Flask `after_request` hook or flask-cors

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| API-01 | Versioned `/api/v1/` blueprint, entirely separate from existing internal suggestion endpoints | New `Blueprint("v1_api", __name__, url_prefix="/api/v1")` in `src/blueprints/v1_api.py`; registered in `app.py` alongside existing `api_bp` |
| API-02 | `GET /api/v1/mappings` — paginated KE-WP mapping list, filterable by KE ID, AOP ID, and pathway ID | New `get_mappings_paginated()` method on `MappingModel`; AOP filter requires SPARQL lookup + KE ID intersection using existing `CacheModel` |
| API-03 | `GET /api/v1/go-mappings` — paginated KE-GO mapping list, filterable by KE ID and GO term ID | New `get_go_mappings_paginated()` method on `GoMappingModel`; `go_namespace` hardcoded to `"biological_process"` since all go_bp_metadata is BP-only |
| API-04 | Content negotiation on collection endpoints — `Accept: text/csv` returns tabular data for R/Python scripts | Use `request.accept_mimetypes.best_match(["application/json", "text/csv"])` in Flask; generate CSV with `csv.DictWriter` into `io.StringIO`; no new dependency |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask `Blueprint` | 3.1.2 (already installed) | Route grouping under `/api/v1` prefix | Already in project; `url_prefix` param handles versioning |
| Python `csv` + `io.StringIO` | stdlib | CSV content negotiation response | Zero new dependencies; pattern already used in `main.py` `/download` route |
| Python `math.ceil` | stdlib | `total_pages` calculation | Standard for pagination |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `flask.request.url_root` | Flask 3.1.2 | Build absolute `next`/`prev` URLs | Use for `next`/`prev` pagination links |
| Existing `RateLimiter` / `general_rate_limit` | In-project | Rate limit public endpoints | Apply same decorator already used on internal endpoints |
| Existing `CacheModel` | In-project | Cache AOP-KE SPARQL lookup | Reuse 24h cache bucket for AOP membership data |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `after_request` hook for CORS | `flask-cors` library | flask-cors adds a pip dependency; `after_request` is 5 lines and has no maintenance risk. Use `after_request`. |
| Custom pagination class | None (inline dict) | A helper `_make_pagination()` function in the blueprint is cleaner and avoids over-engineering for two endpoints |
| Comma-separated multi-values | Repeated params (`?ke_id=X&ke_id=Y`) | Comma-separated (`?ke_id=KE+1,KE+2`) is idiomatic in both `requests` (single param) and R httr2 (`req_url_query(.multi="comma")`). Use comma-separated. |
| Absolute `next`/`prev` URLs | Relative paths | Absolute URLs (using `request.url_root`) are required by httr2's `req_perform_iteratively()` — R clients need a full URL to follow pagination. Use absolute. |

**Installation:** No new packages required. All tools are in the standard library or already in `requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── blueprints/
│   ├── __init__.py          # Add v1_api_bp to exports
│   ├── v1_api.py            # NEW: Public REST API blueprint
│   ├── api.py               # Unchanged: internal UI endpoints
│   └── ...
└── core/
    └── models.py            # Add get_mappings_paginated(), get_go_mappings_paginated()
app.py                       # Register v1_api_bp; CSRF-exempt it
```

### Pattern 1: Blueprint Registration with CSRF Exemption

**What:** The new public API blueprint must be exempt from Flask-WTF CSRF protection (which applies to POST requests globally). Since Phase 3 is read-only (GET only), CSRF exemption is not strictly necessary, but the blueprint should still be explicitly exempt to avoid future confusion.

**When to use:** Every public endpoint that is not session-based.

**Example:**
```python
# app.py
from src.blueprints.v1_api import v1_api_bp

# In create_app():
csrf.exempt(v1_api_bp)  # Public API is stateless/read-only
app.register_blueprint(v1_api_bp)
```

### Pattern 2: Blueprint-Scoped CORS via after_request Hook

**What:** An `after_request` hook on the blueprint adds `Access-Control-Allow-Origin: *` to every response served by `v1_api_bp`.

**When to use:** When you want CORS scoped to one blueprint only, not the entire app.

**Example:**
```python
# src/blueprints/v1_api.py
v1_api_bp = Blueprint("v1_api", __name__, url_prefix="/api/v1")

@v1_api_bp.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept"
    return response
```

### Pattern 3: Content Negotiation in a Route

**What:** Check `Accept` header; return JSON or CSV based on best match. Reuse the `csv.DictWriter` + `io.StringIO` pattern already present in `main.py`.

**Example:**
```python
from flask import request, jsonify, make_response
import csv
import io

def _respond(data, pagination, csv_fieldnames):
    best = request.accept_mimetypes.best_match(["application/json", "text/csv"])
    if best == "text/csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=csv_fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv"
        return response
    return jsonify({"data": data, "pagination": pagination})
```

### Pattern 4: Paginated Query Method in Model

**What:** A SQL query method that accepts `page`, `per_page`, and optional filter kwargs. Returns `(rows, total_count)`.

**Example:**
```python
# src/core/models.py — MappingModel
def get_mappings_paginated(
    self,
    page: int = 1,
    per_page: int = 50,
    ke_id: str = None,
    pathway_id: str = None,
    confidence_level: str = None,
    ke_ids: list = None,   # Used for AOP filter pre-expansion
) -> tuple:
    """Returns (List[Dict], total_count)"""
    conditions = []
    params = []

    if ke_id:
        conditions.append("ke_id = ?")
        params.append(ke_id)
    if pathway_id:
        conditions.append("wp_id = ?")
        params.append(pathway_id)
    if confidence_level:
        conditions.append("LOWER(confidence_level) = LOWER(?)")
        params.append(confidence_level)
    if ke_ids is not None:  # AOP filter resolved to KE list
        if not ke_ids:
            return [], 0  # AOP exists but has no KEs in DB
        placeholders = ",".join("?" * len(ke_ids))
        conditions.append(f"ke_id IN ({placeholders})")
        params.extend(ke_ids)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * per_page

    conn = self.db.get_connection()
    try:
        count_row = conn.execute(
            f"SELECT COUNT(*) FROM mappings {where}", params
        ).fetchone()
        total = count_row[0]
        rows = conn.execute(
            f"""SELECT uuid, ke_id, ke_title, wp_id, wp_title, confidence_level,
                       approved_by_curator, approved_at_curator, suggestion_score
                FROM mappings {where}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()
        return [dict(r) for r in rows], total
    finally:
        conn.close()
```

### Pattern 5: AOP Filter via SPARQL + Cache

**What:** When `?aop_id=` is passed, resolve it to a list of `ke_id` values using the existing SPARQL + CacheModel pattern from `api.py:get_aop_kes()`. Then pass those `ke_id` values to `get_mappings_paginated(ke_ids=...)`.

**Key insight:** AOP membership is not stored in the database. The KE IDs for an AOP must be fetched from AOP-Wiki SPARQL (already cached 24h in `sparql_cache` table). The `v1_api_bp` needs access to `cache_model` for this.

**Example:**
```python
def _resolve_aop_ke_ids(aop_id: str, cache_model, requests_lib) -> list:
    """Return list of ke_id strings for the given AOP ID. Returns [] if AOP unknown."""
    aop_label = f"AOP {aop_id}" if aop_id.isdigit() else aop_id
    cache_key = f"aop_kes_{aop_label}"
    query_hash = hashlib.md5(cache_key.encode()).hexdigest()
    endpoint = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql"

    cached = cache_model.get_cached_response(endpoint, query_hash)
    if cached:
        return [item["KElabel"] for item in json.loads(cached)]

    # ... SPARQL query identical to get_aop_kes() in api.py ...
    # cache the result, return list of KElabel strings
```

### Pattern 6: Pagination Envelope Construction

**What:** Build the `pagination` dict with absolute `next`/`prev` URL strings. Use `request.url_root` + reconstruct the path with updated `page=` param.

**Example:**
```python
import math
from urllib.parse import urlencode, urlparse, parse_qs, urlunsplit

def _make_pagination(page, per_page, total, base_url, extra_params):
    total_pages = math.ceil(total / per_page) if per_page else 1

    def page_url(p):
        params = {**extra_params, "page": p, "per_page": per_page}
        return f"{base_url}?{urlencode(params)}"

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "next": page_url(page + 1) if page < total_pages else None,
        "prev": page_url(page - 1) if page > 1 else None,
    }
```

### Anti-Patterns to Avoid

- **Sharing module-level globals with `api_bp`:** `v1_api_bp` needs `mapping_model`, `go_mapping_model`, and `cache_model`. Create a separate `set_models()` function in `v1_api.py` — do not reuse `api_bp`'s globals.
- **Importing `api_bp`'s set_models from `v1_api.py`:** This creates a coupling that breaks the "entirely separate blueprint" design constraint.
- **Registering `v1_api_bp` before exempting from CSRF:** Call `csrf.exempt(v1_api_bp)` before `app.register_blueprint(v1_api_bp)`.
- **Applying CORS at `@app.after_request`:** This would add CORS to all existing internal endpoints. Scope it to `@v1_api_bp.after_request`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CORS header management | Custom middleware class | `@v1_api_bp.after_request` hook (5 lines) | No state needed; blueprint-scoped hooks are Flask's intended mechanism |
| Pagination library | Class with next/prev methods | Inline `_make_pagination()` helper function | Two endpoints don't justify a class; stdlib `math.ceil` is sufficient |
| CSV serialization | Manual string concatenation | `csv.DictWriter` + `io.StringIO` | Already used in `main.py:/download`; handles quoting and encoding correctly |
| Query builder | ORM or dynamic SQL generator | Parameterized SQL with `conditions.append()` pattern | Already used throughout `models.py`; safe against injection |

**Key insight:** The codebase is intentionally thin — no ORM, no serialization library, no HTTP client abstraction. Phase 3 should follow the same pattern: direct SQL, direct Flask, direct `csv` stdlib.

---

## Common Pitfalls

### Pitfall 1: CSRF Token Rejection on GET requests
**What goes wrong:** Flask-WTF's `CSRFProtect` by default validates tokens only on POST/PUT/PATCH/DELETE — GET requests are not affected. However, future POST additions to `v1_api_bp` would fail without exemption. Additionally, calling `csrf.exempt(v1_api_bp)` is the established pattern in this codebase.
**Why it happens:** `CSRFProtect` is applied globally in `create_app()`; without explicit exemption, any future write endpoint on the public API would require a CSRF token.
**How to avoid:** Call `csrf.exempt(v1_api_bp)` immediately after `CSRFProtect(app)` and before `app.register_blueprint(v1_api_bp)`.
**Warning signs:** 400 errors with "CSRF token missing or invalid" on POST requests to `/api/v1/`.

### Pitfall 2: `suggestion_score` Missing from Existing Rows
**What goes wrong:** The `suggestion_score` column was added by Phase 2 migration but is nullable. Many existing rows have `NULL` for `suggestion_score` (only proposals submitted after Phase 2 capture the score). The `provenance` block will have `"suggestion_score": null` for pre-Phase-2 mappings.
**Why it happens:** Backfill was explicitly deferred — Phase 2 PLAN decisions note that only new submissions capture suggestion_score.
**How to avoid:** Serialize `None` as JSON `null` (Python's `jsonify` handles this automatically). Document in the API that `null` means "score not available for historically-approved mappings."
**Warning signs:** Consumer code crashing on `null` suggestion_score — document this in Phase 6.

### Pitfall 3: AOP Filter Returns No Results When AOP Has KEs Not in DB
**What goes wrong:** A valid AOP ID resolves to a list of KE IDs, but none of those KEs have approved mappings. The API returns `{"data": [], "pagination": {"total": 0, ...}}` which is correct but looks like an error.
**Why it happens:** AOP membership and mapping existence are independent. An AOP can reference KEs that haven't been mapped yet.
**How to avoid:** Return 200 with empty `data: []` (not 404). 404 should only be used for missing UUIDs, not for valid filters that happen to match zero rows.
**Warning signs:** Clients treating empty results as errors; document the distinction in Phase 6.

### Pitfall 4: `go_namespace` Field Does Not Exist in Metadata
**What goes wrong:** The CONTEXT decision specifies `go_namespace` in GO mapping responses ("Biological Process / Molecular Function / Cellular Component"). The `go_bp_metadata.json` file contains only Biological Process terms (`go_bp` = GO Biological Process) and has no `namespace` key.
**Why it happens:** The metadata was pre-computed specifically for the BP namespace from GO.
**How to avoid:** Hardcode `"go_namespace": "biological_process"` in the serializer for all GO mapping responses. This is accurate since `ke_go_mappings` only stores GO BP terms. If the data model later expands to MF/CC, the field will need to become dynamic.
**Warning signs:** Attempting to look up namespace from metadata and getting `KeyError` or `None`.

### Pitfall 5: Blueprint `set_models()` Not Called Before First Request
**What goes wrong:** `v1_api_bp`'s module-level model variables are `None` if `set_models()` is not called in `create_app()`. Routes will throw `AttributeError` on `None.get_mappings_paginated()`.
**Why it happens:** The blueprint pattern in this codebase defers model injection to `create_app()`.
**How to avoid:** Add `set_v1_api_models(services.mapping_model, services.go_mapping_model, services.cache_model)` in `create_app()` alongside the existing `set_api_models(...)` call.
**Warning signs:** `NoneType has no attribute 'get_mappings_paginated'` errors on first API request.

### Pitfall 6: Rate Limiter Uses App DATABASE_PATH
**What goes wrong:** The existing `general_rate_limit` / `rate_limit()` decorator reads `current_app.config.get("DATABASE_PATH", "ke_wp_mapping.db")` — this was fixed in the most recent commit (`4f8f88d`). Applying the existing decorator to `v1_api_bp` routes will work correctly.
**Why it happens:** Historical bug already resolved.
**How to avoid:** Use the existing `@general_rate_limit` decorator as-is. Do not copy-paste the `RateLimiter` class.
**Warning signs:** None — already fixed.

---

## Code Examples

Verified patterns from the existing codebase:

### Serializing a Mapping Row to the v1 Response Shape

```python
# Source: Derived from models.py get_mapping_by_uuid() return value
def _serialize_mapping(row: dict) -> dict:
    """Convert a DB row dict to the v1 API mapping object shape."""
    return {
        "uuid": row["uuid"],
        "ke_id": row["ke_id"],
        "ke_name": row["ke_title"],       # note: DB field is ke_title
        "pathway_id": row["wp_id"],
        "pathway_title": row["wp_title"],
        "confidence_level": row["confidence_level"],
        "provenance": {
            "suggestion_score": row.get("suggestion_score"),   # may be None
            "approved_by": row.get("approved_by_curator"),     # may be None
            "approved_at": row.get("approved_at_curator"),     # may be None
        },
    }

def _serialize_go_mapping(row: dict) -> dict:
    """Convert a DB row dict to the v1 API GO mapping object shape."""
    return {
        "uuid": row["uuid"],
        "ke_id": row["ke_id"],
        "ke_name": row["ke_title"],
        "go_term_id": row["go_id"],
        "go_term_name": row["go_name"],
        "go_namespace": "biological_process",   # hardcoded: all go_bp data is BP
        "confidence_level": row["confidence_level"],
        "provenance": {
            "suggestion_score": row.get("suggestion_score"),
            "approved_by": row.get("approved_by_curator"),
            "approved_at": row.get("approved_at_curator"),
        },
    }
```

### CSV Response for Content Negotiation

```python
# Source: Pattern from main.py:/download — adapted for API collection
import csv
import io
from flask import make_response

def _csv_response(rows: list, fieldnames: list) -> "Response":
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response

# CSV fieldnames for /api/v1/mappings
MAPPING_CSV_FIELDS = [
    "uuid", "ke_id", "ke_name", "pathway_id", "pathway_title",
    "confidence_level", "suggestion_score", "approved_by", "approved_at"
]
# Note: provenance is flattened for CSV (nested dicts don't serialize to CSV)
```

### Pagination Parameter Validation

```python
# Source: Pattern from api.py suggest_pathways() — adapted for public API
from flask import request

def _parse_pagination_params():
    """
    Parse and clamp pagination params from request.args.

    Returns:
        (page, per_page) tuple — always valid integers
    """
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = int(request.args.get("per_page", 50))
        per_page = max(1, min(per_page, 200))   # clamp to [1, 200]
    except (ValueError, TypeError):
        per_page = 50
    return page, per_page
```

### Blueprint Registration in app.py

```python
# Source: Existing pattern in app.py — add v1_api_bp analogously
from src.blueprints.v1_api import v1_api_bp
from src.blueprints.v1_api import set_models as set_v1_api_models

# In create_app(), after CSRFProtect(app):
csrf.exempt(v1_api_bp)

# After existing set_api_models() call:
set_v1_api_models(
    mapping=services.mapping_model,
    go_mapping=services.go_mapping_model,
    cache=services.cache_model,
)

# In blueprint registration block:
app.register_blueprint(v1_api_bp)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `allow_pickle=True` numpy loads | NPZ matrix format (Phase 1) | Phase 1 | Not relevant to Phase 3 |
| Internal-only API endpoints | Dual-blueprint split (API-01 decision) | Phase 3 | New blueprint entirely separate from `api_bp` |
| No stable IDs | UUID columns + backfill (Phase 2) | Phase 2 | Phase 3 can use UUID as the stable external key |

**Deprecated/outdated in this codebase:**
- The `suggestion_score` column is nullable for pre-Phase-2 rows — Phase 3 must tolerate `NULL` in provenance blocks.
- `approved_by_curator` maps to `approved_by` in the external API; the rename happens in the serializer, not the DB.

---

## Open Questions

1. **`go_namespace` field accuracy**
   - What we know: `go_bp_metadata.json` has no namespace field; all entries are GO Biological Process terms.
   - What's unclear: Will `ke_go_mappings` ever store MF or CC terms? The submission form (`submit_go_mapping`) only submits `go_id` and `go_name` — no namespace validation is performed.
   - Recommendation: Hardcode `"biological_process"` for Phase 3. If MF/CC terms are ever added (out of scope for this phase), the serializer will need a metadata lookup.

2. **Rate limit threshold for public API**
   - What we know: `general_rate_limit` is 1000/hour; `sparql_rate_limit` is 500/hour; `submission_rate_limit` is 20/hour.
   - What's unclear: Should the public API have a lower limit than internal UI endpoints to protect against scrapers?
   - Recommendation: Apply `general_rate_limit` (1000/hour) to all read endpoints in `v1_api_bp`. AOP-lookup endpoint may call SPARQL, so use `sparql_rate_limit` (500/hour) if the AOP-lookup path is a separate internal call, or just absorb it under the outer rate limit.

3. **Comma-separated multi-value params in Python `requests`**
   - What we know: `requests.get(url, params={"ke_id": "KE 1,KE 2"})` sends `?ke_id=KE+1%2CKE+2` — the server receives `ke_id=KE 1,KE 2` after URL decoding.
   - What's unclear: Whether bioinformaticians will use multi-value filters at all in Phase 3 (the common case is single-KE or single-pathway queries).
   - Recommendation: Support comma-separated values for all filter params. Split on `,` server-side. Document the pattern in Phase 6. This is more `requests`-idiomatic than repeated `?ke_id=X&ke_id=Y` params.

4. **AOP filter — what to return when AOP ID is not found in SPARQL**
   - What we know: `get_aop_kes()` in `api.py` returns `{"error": "Failed to fetch KEs for AOP"}` on SPARQL error. For the public API, this should be a 400 or 404, not a 500.
   - Recommendation: If SPARQL times out or returns empty, return `{"error": "AOP ID not found or SPARQL unavailable"}` with status 400. An empty-but-valid AOP returns `{"data": [], "pagination": {"total": 0, ...}}` with 200.

---

## Sources

### Primary (HIGH confidence)
- `src/blueprints/api.py` — Existing blueprint pattern, rate limiter usage, SPARQL + cache pattern
- `src/blueprints/main.py` — CSV generation pattern (lines 86-223), `mapping_detail` route as Phase 3 starting point (line 457)
- `src/core/models.py` — `get_mapping_by_uuid()`, `get_go_mapping_by_uuid()`, column names confirmed by `PRAGMA table_info()` output
- `app.py` — Blueprint registration pattern, `csrf.exempt()` usage, `set_models()` wiring
- `data/go_bp_metadata.json` — Confirmed: no `namespace` field; keys are `name`, `definition`, `is_a`, `part_of`, `synonyms`
- Live DB schema — Confirmed via `PRAGMA table_info()`: `suggestion_score` not yet in `mappings` table; it is in `proposals` table (added by Phase 2 migration to `_migrate_mappings_uuid_and_provenance`)

**Note on `suggestion_score` in mappings table:** Confirmed by DB inspection that `mappings` columns are: `id, ke_id, ke_title, wp_id, wp_title, connection_type, confidence_level, created_by, created_at, updated_at, updated_by, uuid, approved_by_curator, approved_at_curator`. The `suggestion_score` column does NOT exist on the `mappings` table itself — it exists on the `proposals` table. The Phase 2 migration adds it to `proposals` but not to `mappings`. The approved mapping's provenance captures the curator and timestamp, but `suggestion_score` must be carried over from the proposal to the mapping row at approval time, OR the API must query the last approved proposal for that mapping to get the score.

**This is a critical finding:** The v1 API's `provenance.suggestion_score` field requires either:
  (a) The admin approval flow writes `suggestion_score` from the proposal to the mapping row (requires a column to be added to `mappings`), or
  (b) A JOIN between `mappings` and `proposals` at query time to pull the score from the approved proposal.

This must be resolved in the planning phase. Option (a) — adding `suggestion_score` to `mappings` via a new migration — is cleaner and consistent with Phase 2's provenance approach. Option (b) adds join complexity to every paginated query.

### Secondary (MEDIUM confidence)
- Flask docs (from training): `Blueprint.after_request` is a well-documented Flask feature for blueprint-scoped hooks; confirmed in Flask 3.x docs
- Python stdlib `csv.DictWriter` with `extrasaction="ignore"`: Confirmed via codebase usage pattern in `main.py`

### Tertiary (LOW confidence)
- R `httr2::req_url_query(.multi="comma")` behavior: From training data; should be validated when Phase 6 writes consumer examples

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools are already in the project; no new dependencies needed
- Architecture: HIGH — blueprint pattern is well-established in this codebase; patterns verified against existing code
- Pitfalls: HIGH — `suggestion_score` gap discovered by direct DB inspection; `go_namespace` confirmed by file inspection; other pitfalls from code review
- `suggestion_score` in mappings: HIGH confidence that column does NOT exist — confirmed by live `PRAGMA table_info()` output

**Research date:** 2026-02-20
**Valid until:** 2026-04-20 (stable codebase; no external API changes expected)
