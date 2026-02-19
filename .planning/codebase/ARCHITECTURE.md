# Architecture

**Analysis Date:** 2026-02-19

## Pattern Overview

**Overall:** Flask Blueprint Architecture with Dependency Injection Container

**Key Characteristics:**
- App factory pattern (`create_app()`) with modular blueprint registration
- Service container (ServiceContainer) manages all dependencies as singletons
- Layered architecture: blueprints (routing) → services (business logic) → models (data access)
- Multi-signal suggestion engine combining gene-based, embedding-based, text-based, and ontology-based matching
- Centralized error handling with custom ApplicationError hierarchy
- Request validation using Marshmallow schemas

## Layers

**Presentation Layer (Blueprints):**
- Purpose: HTTP routing, request handling, user interaction
- Location: `src/blueprints/`
- Contains:
  - `main.py` - Page routes (index, explore, download, KE/WP detail views)
  - `api.py` - REST endpoints (check, submit, suggestions, SPARQL proxies, exports)
  - `auth.py` - OAuth login/logout, guest code validation
  - `admin.py` - Proposal review, approval/rejection workflows
- Depends on: Models, Services, Schemas
- Used by: HTTP clients, browsers, frontend JavaScript

**Service Layer:**
- Purpose: Business logic, external service integration, data processing
- Location: `src/services/` and `src/suggestions/`
- Contains:
  - `ServiceContainer` (`src/services/container.py`) - Dependency injection, singleton management
  - `BiologicalEmbeddingService` (`src/services/embedding.py`) - Vector similarity matching
  - `PathwaySuggestionService` (`src/suggestions/pathway.py`) - KE-WP suggestions (gene, embedding, text, ontology signals)
  - `GoSuggestionService` (`src/suggestions/go.py`) - KE-GO suggestions (gene annotation, embedding signals)
  - `MetricsCollector` (`src/services/monitoring.py`) - Performance tracking
  - `RateLimiter` (`src/services/rate_limiter.py`) - Request rate limiting
- Depends on: Models, Config, External APIs (WikiPathways, AOP-Wiki SPARQL endpoints)
- Used by: Blueprints, other services

**Data Access Layer (Models):**
- Purpose: Database operations, persistence
- Location: `src/core/models.py`
- Contains:
  - `Database` - Connection management, schema initialization, migrations
  - `MappingModel` - KE-WP mapping CRUD
  - `ProposalModel` - KE-WP proposal CRUD
  - `GoMappingModel` - KE-GO mapping CRUD
  - `GoProposalModel` - KE-GO proposal CRUD
  - `CacheModel` - SPARQL response caching
  - `GuestCodeModel` - Guest access code management
- Depends on: SQLite database (`ke_wp_mapping.db`)
- Used by: Services, Blueprints

**Configuration & Cross-Cutting Concerns:**
- Purpose: Configuration management, validation, error handling, utilities
- Location: `src/core/`, `src/utils/`
- Contains:
  - `config.py` - Environment-based config (development, production, testing)
  - `schemas.py` - Marshmallow validation schemas
  - `error_handlers.py` - Global error handling, ApplicationError hierarchy
  - `config_loader.py` - Scoring configuration from YAML
  - `text.py` - Text normalization, directionality removal
  - `timezone.py` - Timestamp formatting

## Data Flow

**KE-WP Suggestion Request:**

1. Browser → `GET /api/suggestions?ke_id=KE+123&ke_title=...`
2. API Blueprint (`api.py`) validates request, calls PathwaySuggestionService
3. PathwaySuggestionService spawns four parallel signals:
   - **Gene signal**: Calls `get_genes_from_ke()`, queries WikiPathways SPARQL for pathway genes
   - **Embedding signal**: Uses BiologicalEmbeddingService to compute KE ↔ pathway title similarity
   - **Text signal**: Direct string similarity matching on KE title ↔ pathway title
   - **Ontology signal**: Pathway ontology tags matched against KE keywords
4. `scoring.py` combines all signals with configurable weights (gene=0.35, text=0.25, embedding=0.40)
5. Results with `hybrid_score`, `match_types`, `signal_scores` returned to browser
6. User submits mapping → `POST /api/submit` → MappingModel creates entry
7. Admin approves → `POST /admin/update-proposal` → ProposalModel updates status → MappingModel updated

**KE-GO Suggestion Request:**

1. Browser → `GET /api/go-suggestions?ke_id=KE+123&ke_title=...`
2. API Blueprint calls GoSuggestionService
3. GoSuggestionService loads pre-computed GO BP embeddings and gene annotations:
   - **Gene annotation signal**: Extracts KE genes, matches against GO term → gene mappings
   - **Embedding signal**: Computes similarity using pre-computed name embeddings
4. Combines signals, applies hybrid scoring, returns GO BP term suggestions

**Caching Layer:**

- SPARQL query responses cached in SQLite with 24-hour TTL
- Query hash computed from endpoint + query string
- Cache bypassed for precomputed embeddings (loaded at startup)

**State Management:**

- Session state: User info, OAuth tokens stored in Flask session (HTTP cookies)
- Database state: Mappings, proposals, guest codes in SQLite
- In-memory state: Service container holds singleton instances for lifetime of app
- Pre-computed embeddings: Loaded from `data/` directory at startup (1561 KEs, 1012 pathways, ~30K GO terms)

## Key Abstractions

**PathwaySuggestionService:**
- Purpose: Encapsulate multi-signal pathway recommendation logic
- Examples: `src/suggestions/pathway.py`
- Pattern: Stateful service with lazy-loading of embedding service and metadata. Uses composition over inheritance. Four private methods (`_get_genes_from_ke`, `_find_pathways_by_genes`, `_get_embedding_based_suggestions`, `_compute_ontology_tag_scores`) generate signal-specific results, then `_combine_multi_signal_suggestions` merges them.

**GoSuggestionService:**
- Purpose: Encapsulate multi-signal GO BP term recommendation logic
- Examples: `src/suggestions/go.py`
- Pattern: Loads and caches pre-computed embeddings/annotations in constructor. Two main signals (gene annotation, embedding) combined with shared `combine_scored_items` utility.

**ServiceContainer:**
- Purpose: Centralized dependency injection with lazy-loading singletons
- Examples: `src/services/container.py`
- Pattern: Properties backed by private `_` attributes. OAuth initialized explicitly via `init_oauth()`. Health status checks dependencies and returns dict with `database`, `oauth`, and nested `services` fields.

**Model Classes:**
- Purpose: Encapsulate database operations, enforce schema
- Examples: `MappingModel`, `ProposalModel`, `GoMappingModel`, `CacheModel`
- Pattern: Each takes `Database` instance in constructor. CRUD methods use parameterized queries to prevent SQL injection. Return `List[Dict]` or `Optional[Dict]` for flexible JSON serialization.

**Blueprint Model Setters:**
- Purpose: Decouple blueprint initialization from app factory
- Pattern: Each blueprint has `set_models()` function called by `create_app()`. Global module-level variables hold references. Allows blueprints to be imported early without circular dependencies.

**Marshmallow Schemas:**
- Purpose: Request validation and deserialization
- Examples: `src/core/schemas.py` (MappingSchema, GoMappingSchema, ProposalSchema)
- Pattern: Define field types, validators, custom validation methods. Used with `validate_request_data()` helper.

**CacheModel + SPARQL:**
- Purpose: Prevent redundant external API calls
- Pattern: Query hash (`hashlib.sha256`) maps to cached response. TTL enforced via `expires_at` timestamp. Cleanup happens on request (lazy deletion).

## Entry Points

**Application Entry Point:**
- Location: `app.py`
- Triggers: `python app.py` (development) or gunicorn/uwsgi (production)
- Responsibilities:
  - Load environment variables from `.env`
  - Call `create_app()` factory
  - Initialize Flask instance with blueprints, CSRF protection, error handlers
  - Register context processor for `is_admin` template variable
  - Expose `/health` and `/metrics` endpoints
  - Start development server on port 5000

**Blueprint Entry Points:**

**Main Blueprint:**
- `GET /` - Index page
- `GET /explore` - Dataset exploration with all KE-WP and KE-GO mappings
- `GET /download` - CSV/JSON/Parquet exports
- `GET /ke/<ke_id>` - KE detail page with related mappings
- `GET /pathway/<wp_id>` - Pathway detail page

**API Blueprint:**
- `POST /check` - Validate KE/WP pair existence
- `POST /submit` - Create new KE-WP mapping
- `GET /suggestions` - Get pathway suggestions for a KE
- `POST /go-check` - Validate KE/GO pair existence
- `POST /go-submit` - Create new KE-GO mapping
- `GET /go-suggestions` - Get GO suggestions for a KE
- `POST /proposal-submit` - Submit proposal to modify existing mapping
- `GET /download-mapping` - Export single mapping
- `GET /proxies/sparql` - Forward SPARQL queries with caching

**Auth Blueprint:**
- `GET /login` - Initiate GitHub OAuth
- `GET /callback` - OAuth callback (handles token exchange)
- `GET /logout` - Clear session
- `GET /guest-login` - Guest login form
- `POST /guest-login` - Validate guest code

**Admin Blueprint:**
- `GET /admin/proposals` - View pending proposals
- `POST /admin/update-proposal` - Approve/reject proposal with optional notes

## Error Handling

**Strategy:** Centralized error handler registration in `create_app()` using `register_error_handlers(app)`

**Patterns:**

**Custom ApplicationError Hierarchy:**
```python
ApplicationError (base, status_code: int, details: dict)
├── ValidationError (400)
├── AuthenticationError (401)
├── AuthorizationError (403)
├── NotFoundError (404)
└── ServiceError (503)
```

**HTTP Status Handling:**
- 400 Bad Request: Schema validation failures, malformed input
- 401 Unauthorized: Missing or invalid session
- 403 Forbidden: User lacks admin privileges
- 404 Not Found: Resource not found
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Unexpected exceptions
- 503 Service Unavailable: External API failures

**Response Format:**
- JSON for `/api/*` and `/admin/*` routes: `{"error": "...", "details": {...}, "status_code": 500}`
- HTML for page routes: `error.html` template with status code and message
- CSRF errors handled specially: Return 400 with security token message

## Cross-Cutting Concerns

**Logging:**
- Tool: Python `logging` module with structured format `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Level: INFO in production, DEBUG in development
- Pattern: Each module has `logger = logging.getLogger(__name__)` at top. Sanitize user input with `sanitize_log()` before logging.

**Validation:**
- Tool: Marshmallow schemas (`src/core/schemas.py`)
- Pattern: `validate_request_data()` helper extracts and validates request fields. Returns `(is_valid, validated_data, errors)` tuple. Schemas define field types, length, regex patterns.

**Authentication:**
- Tool: GitHub OAuth via Authlib, guest codes via database
- Pattern:
  - GitHub: User visits `/login` → OAuth authorize → GitHub callback → session["user"] set
  - Guest: Admin creates code via `/admin/guest-codes` → user submits code → `GuestCodeModel.validate_code()` increments use count
  - Session checked via `@login_required` decorator on blueprints

**Rate Limiting:**
- Tool: `RateLimiter` class with SQLite backing
- Pattern: Decorators `@general_rate_limit`, `@submission_rate_limit`, `@sparql_rate_limit` applied to routes. Stored as `(ip_address, endpoint)` tuples with `reset_time` in SQLite `rate_limits` table (implicit in implementation).

**Monitoring:**
- Tool: `MetricsCollector` in `src/services/monitoring.py`
- Pattern: Decorator `@monitor_performance` wraps routes. Records endpoint name, response time, status code. Accessible via `/metrics` and `/metrics/<endpoint_name>?hours=24` endpoints.

**CSRF Protection:**
- Tool: Flask-WTF with `CSRFProtect(app)`
- Pattern: All POST requests require CSRF token in form data. Token generated per session, expires after 1 hour. Custom error handler returns 400 with user-friendly message.
