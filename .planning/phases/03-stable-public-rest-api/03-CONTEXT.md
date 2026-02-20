# Phase 3: Stable Public REST API - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose curated KE-WP and KE-GO mappings via a versioned `/api/v1/` prefix — no authentication required, read-only, stable contract before external researchers depend on it. Internal UI endpoints (`api_bp`) are untouched. Write access, webhooks, and auth-gated endpoints are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Response shape

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

### Pagination

- Query params: `?page=1&per_page=50`
- Default: 50 per page; maximum: 200 per page
- Pagination envelope includes: `page`, `per_page`, `total`, `total_pages`, `next` (URL or null), `prev` (URL or null)

### Filtering scope

- `/api/v1/mappings` filters: `ke_id`, `aop_id`, `pathway_id`, `confidence_level` (all optional)
- `/api/v1/go-mappings` filters: `ke_id`, `go_term_id`, `confidence_level` (all optional)
- Multi-value approach: Claude's discretion (comma-separated or repeated params — pick the most idiomatic for Python `requests` and R `httr2`)
- Single-resource lookup included: `GET /api/v1/mappings/<uuid>` and `GET /api/v1/go-mappings/<uuid>`
- No date-range filters (approved_after / approved_before) — out of scope

### Error contract

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

</decisions>

<specifics>
## Specific Ideas

- The existing `/mappings/<uuid>` route added in Phase 2 (internal, login-required) is a starting point — the Phase 3 route is a public, unauthenticated counterpart at `/api/v1/mappings/<uuid>`
- Target consumers: `requests.get(...)` in Python and `httr2::req_perform(...)` in R — keep the envelope consistent so both libraries can unwrap `data` the same way

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-stable-public-rest-api*
*Context gathered: 2026-02-20*
