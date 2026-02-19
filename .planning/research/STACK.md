# Stack Research: KE Mapping Tool — v1.0 Maturation

**Domain:** Bioinformatics curation tool / biological pathway annotation database
**Milestone context:** Subsequent — maturing existing Flask/SQLite/BioBERT prototype

## Summary

The existing Python/Flask stack is well-suited for this domain. Bioinformatics database APIs (ChEMBL, WikiPathways, Reactome) consistently use Flask or FastAPI for REST APIs with JSON as primary format, RDF/Turtle for semantic web consumers, and tabular formats (CSV/TSV) for R/Python script consumers. No stack migration is needed — the gaps are in API structure, documentation, and export layer.

## Recommended Stack (Additions/Upgrades)

### REST API Layer

| Component | Recommendation | Confidence | Rationale |
|-----------|---------------|------------|-----------|
| API framework | Flask (existing) with new `/api/v1/` blueprint | High | No migration cost; blueprints handle versioning cleanly |
| API documentation | Flask-RESTX or flasgger (OpenAPI/Swagger) | High | OpenAPI is table stakes for scientific APIs; R `httr2` and Python `requests` users expect discoverable docs |
| Response serialization | marshmallow (existing) + flask.jsonify | High | Already in project; extend schemas |
| Pagination | Cursor-based pagination (not offset) | Medium | Offset pagination has consistency issues with live data; cursor is what ChEMBL uses |

### Export Formats

| Format | Priority | Library | Consumer |
|--------|----------|---------|----------|
| JSON | Must | stdlib json | Python, JavaScript |
| CSV/TSV | Must | pandas (existing) | R workflows, Excel |
| RDF/Turtle | Should | rdflib 7.x | Semantic web, AOP-Wiki integration |
| Parquet | Nice | pandas (existing) | Large dataset consumers |

**Note:** rdflib is NOT currently in requirements.txt — needs adding for RDF export.

### Curation UI

| Component | Recommendation | Confidence |
|-----------|---------------|------------|
| Frontend framework | Vanilla JS + HTMX (progressive enhancement) | High |
| CSS | Existing Bootstrap or Tailwind CDN | Medium |
| Bulk operations | Server-rendered with HTMX for inline updates | High |

**Why not React/Vue:** The existing app is server-rendered Jinja2. Adding a JS framework for incremental UX improvements has high cost/benefit ratio. HTMX provides modern UX with minimal JS.

### Production Deployment

| Component | Recommendation | Confidence |
|-----------|---------------|------------|
| WSGI | Gunicorn (already in requirements) | High |
| Process manager | Docker Compose (already configured) | High |
| Reverse proxy | Nginx in Docker Compose | High |
| SQLite WAL mode | Enable WAL for concurrent reads | High |
| Health checks | `/health` endpoint (already exists) | High |

### What NOT to Use

- **PostgreSQL migration for v1:** SQLite with WAL mode handles the expected load (small curator team). Migration is a v2 concern.
- **Celery/Redis for async tasks:** Suggestion generation is fast enough synchronously (<1s). Async queue adds operational complexity not justified at this scale.
- **React/Vue/Next.js:** Server-rendered Jinja2 with HTMX is sufficient and avoids a full frontend rewrite.
- **FastAPI migration:** Flask 3.1 with async support is adequate; migrating would be disruptive.

## Existing Dependencies (No Change Needed)

- Flask 3.1.2, Flask-WTF, Authlib — keep as-is
- sentence-transformers, torch, numpy — keep as-is (BioBERT)
- pandas — already covers CSV/Parquet exports
- marshmallow — extend for API response schemas

## Dependencies to Add

```
rdflib>=7.0.0          # RDF/Turtle export
flask-restx>=1.3.0     # OR flasgger>=0.9.7 for OpenAPI docs
```

---
*Research synthesized from domain knowledge + existing codebase analysis, 2026-02-19*
