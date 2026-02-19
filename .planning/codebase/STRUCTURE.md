# Codebase Structure

**Analysis Date:** 2026-02-19

## Directory Layout

```
KE-WP-mapping/
├── app.py                      # Entry point — app factory, Flask initialization
├── .planning/                  # GSD planning documents
├── src/
│   ├── __init__.py            # Package init, PROJECT_ROOT defined
│   ├── core/                  # Models, config, schemas, error handling
│   │   ├── models.py          # Database classes (Database, MappingModel, ProposalModel, GoMappingModel, etc.)
│   │   ├── config.py          # Config classes (DevelopmentConfig, ProductionConfig, TestingConfig)
│   │   ├── config_loader.py   # YAML scoring config loader
│   │   ├── schemas.py         # Marshmallow validation schemas
│   │   ├── error_handlers.py  # Centralized error handling, ApplicationError classes
│   │   └── __init__.py
│   ├── services/              # Business logic, dependencies
│   │   ├── container.py       # ServiceContainer — dependency injection
│   │   ├── embedding.py       # BiologicalEmbeddingService — vector similarity
│   │   ├── monitoring.py      # MetricsCollector — performance tracking
│   │   ├── rate_limiter.py    # RateLimiter — request rate limiting
│   │   └── __init__.py
│   ├── suggestions/           # Multi-signal suggestion engines
│   │   ├── pathway.py         # PathwaySuggestionService — KE-WP suggestions
│   │   ├── go.py              # GoSuggestionService — KE-GO suggestions
│   │   ├── ke_genes.py        # get_genes_from_ke() — extract gene symbols from KE
│   │   ├── scoring.py         # combine_scored_items() — hybrid score merging
│   │   └── __init__.py
│   ├── blueprints/            # Flask blueprints — HTTP routing
│   │   ├── main.py            # Page routes (index, explore, download, detail views)
│   │   ├── api.py             # REST endpoints (check, submit, suggestions, exports)
│   │   ├── auth.py            # OAuth and guest login flows
│   │   ├── admin.py           # Admin dashboard, proposal management
│   │   └── __init__.py
│   ├── exporters/             # Data export formats
│   │   ├── json_exporter.py   # JSON export
│   │   ├── excel_exporter.py  # Excel (.xlsx) export
│   │   ├── parquet_exporter.py # Parquet export
│   │   ├── rdf_exporter.py    # RDF/Turtle export
│   │   └── __init__.py
│   ├── utils/                 # Shared utilities
│   │   ├── text.py            # Text normalization, directionality removal
│   │   ├── timezone.py        # Timestamp formatting (admin, export)
│   │   └── __init__.py
│   └── __init__.py
├── data/                      # Pre-computed embeddings & metadata
│   ├── ke_embeddings.npy      # KE embeddings (1561 entries)
│   ├── pathway_title_embeddings.npy # Pathway embeddings (1012 entries)
│   ├── go_bp_embeddings.npy   # GO BP full embeddings (~30K terms)
│   ├── go_bp_name_embeddings.npy # GO BP name-only embeddings
│   ├── go_bp_metadata.json    # GO term ID, name, definition
│   ├── go_bp_gene_annotations.json # GO BP → gene mappings
│   ├── ke_metadata.json       # KE dropdown data (replaces live SPARQL)
│   └── pathway_metadata.json  # Pathway dropdown data (replaces live SPARQL)
├── templates/                 # Jinja2 templates
│   ├── index.html            # Main landing page
│   ├── explore.html          # Dataset exploration page
│   ├── base.html             # Base template (shared layout)
│   ├── error.html            # Error pages
│   ├── guest_login.html      # Guest access code login
│   ├── components/           # Reusable template components
│   └── docs/                 # Documentation pages
│       ├── api.html
│       ├── overview.html
│       └── user-guide.html
├── static/                    # Static assets
│   ├── css/                  # Stylesheets
│   ├── js/                   # Client-side JavaScript
│   └── images/               # Images (assessment screenshots)
├── scripts/                   # Data pre-computation scripts
│   ├── precompute_ke_embeddings.py # Generate KE embeddings → data/
│   ├── precompute_pathway_title_embeddings.py # Generate pathway embeddings → data/
│   ├── precompute_go_embeddings.py # Generate GO BP embeddings → data/
│   └── download_go_annotations.py # Download GO-gene annotations → data/
├── tests/                     # Pytest test suite
│   └── *.py                   # Test files (mirroring src/ structure)
├── docs/                      # Documentation
│   ├── SCORING_CONFIG.md      # Scoring parameter documentation
│   ├── archive/               # Historical docs and old versions
│   └── *.md                   # Architecture, guides, changelogs
├── ke_wp_mapping.db           # SQLite database (auto-created)
├── scoring_config.yaml        # Scoring parameters (65+ settings)
├── .env.example              # Environment variables template
├── Makefile                  # Development commands (make help, make test)
├── requirements.txt          # Python dependencies
└── CLAUDE.md                 # Instructions for Claude Code
```

## Directory Purposes

**src/core/:**
- Purpose: Application configuration, data models, error handling
- Contains: Database schema, ORM-like model classes, validation schemas, environment config
- Key files: `models.py` (all database operations), `config.py` (environment management), `error_handlers.py` (global exception handling)

**src/services/:**
- Purpose: Shared business logic and infrastructure
- Contains: Dependency injection container, embedding service, metrics, rate limiting
- Key files: `container.py` (singleton management), `embedding.py` (BioBERT similarity)

**src/suggestions/:**
- Purpose: Multi-signal recommendation engines
- Contains: KE-WP and KE-GO suggestion logic, gene extraction, score combining
- Key files: `pathway.py` (4 signals: gene, embedding, text, ontology), `go.py` (2 signals: gene annotation, embedding)

**src/blueprints/:**
- Purpose: HTTP routing and request handling
- Contains: All endpoints for pages, API, auth, admin
- Key files: `api.py` (53KB, largest file — all REST endpoints), `main.py` (page routes), `admin.py` (admin dashboard)

**src/exporters/:**
- Purpose: Data export in multiple formats
- Contains: JSON, Excel, Parquet, RDF exporters
- Usage: Called from `main.py` `/download` route and API download endpoints

**src/utils/:**
- Purpose: Shared utilities
- Contains: Text processing (remove directionality), timezone formatting
- Key files: `text.py` (normalization logic), `timezone.py` (UTC ↔ local conversion)

**data/:**
- Purpose: Pre-computed embeddings, metadata, and annotations
- Contains: NumPy files (.npy), JSON files with metadata
- Generated by: `scripts/` during setup (see CLAUDE.md "Embedding Management")
- Not committed: Embeddings are too large; downloaded at setup time

**templates/:**
- Purpose: Jinja2 HTML templates
- Contains: Page templates, error page, documentation pages
- Pattern: `base.html` for shared layout, components in `components/` subdirectory

**static/:**
- Purpose: Client-side assets
- Contains: CSS, JavaScript, images
- Structure: `css/`, `js/`, `images/assessment/` (for assessment UI screenshots)

**scripts/:**
- Purpose: One-time data generation and setup
- Contains: Embedding pre-computation, GO annotation downloads
- Usage: Run manually via `python scripts/precompute_*.py` (see CLAUDE.md)

**tests/:**
- Purpose: Pytest test suite
- Pattern: Mirrors src/ structure (e.g., `tests/test_models.py` for `src/core/models.py`)
- Run: `make test` or `pytest tests/`

**docs/:**
- Purpose: Project documentation
- Contains: Configuration reference, architecture guides, changelog
- Key files: `SCORING_CONFIG.md` (scoring parameters), `archive/` (old versions)

## Key File Locations

**Entry Points:**
- `app.py`: Main Flask app creation and initialization
- `src/blueprints/__init__.py`: Blueprint import and export
- `src/blueprints/main.py:54`: `GET /` — index route
- `src/blueprints/api.py:81`: `POST /check` — first API endpoint

**Configuration:**
- `.env`: Runtime environment (secrets, credentials)
- `.env.example`: Environment template with required vars
- `src/core/config.py`: Config class definitions
- `scoring_config.yaml`: Scoring algorithm parameters (65+ tunable values)
- `src/core/config_loader.py`: YAML parser for scoring config

**Core Logic:**
- `src/core/models.py`: All database operations (1120 lines)
- `src/services/container.py`: Dependency injection (351 lines)
- `src/suggestions/pathway.py`: KE-WP suggestions (400+ lines)
- `src/suggestions/go.py`: KE-GO suggestions (300+ lines)
- `src/suggestions/scoring.py`: Multi-signal score merging

**Database:**
- `ke_wp_mapping.db`: SQLite database (auto-created on first run)
- Schema: Tables for `mappings`, `proposals`, `ke_go_mappings`, `ke_go_proposals`, `sparql_cache`, `guest_codes`
- Migrations: Auto-applied via `Database._migrate_*` methods

**REST API:**
- `src/blueprints/api.py`: All endpoints (check, submit, suggestions, exports, SPARQL proxy)
- `src/core/schemas.py`: Request validation schemas

**Templates:**
- `templates/base.html`: Shared layout
- `templates/index.html`: Landing page
- `templates/explore.html`: Dataset explorer
- `templates/error.html`: Error display

**Testing:**
- `tests/test_*.py`: Unit tests
- `tests/conftest.py`: Pytest fixtures (if present)

## Naming Conventions

**Files:**
- Snake_case: `pathway.py`, `embedding.py`, `config_loader.py`
- Modules: Descriptive, match class names where possible (e.g., `pathway.py` exports `PathwaySuggestionService`)

**Directories:**
- Lowercase, plural for collections: `services/`, `suggestions/`, `blueprints/`, `exporters/`
- Singular for specific modules: `core/`, `utils/`

**Classes:**
- PascalCase: `PathwaySuggestionService`, `BiologicalEmbeddingService`, `MappingModel`
- Suffix by responsibility: `*Service` for business logic, `*Model` for data access

**Functions:**
- snake_case: `get_pathway_suggestions()`, `validate_code()`, `sanitize_log()`
- Prefixed with intent: `get_*` (retrieve), `create_*` (insert), `update_*` (modify), `check_*` (validate)

**Variables:**
- snake_case: `ke_id`, `wp_title`, `connection_type`
- Acronyms preserved as-is: `ke_id`, `wp_id`, `go_id` (not `key_event_id`)

**Types:**
- PascalCase: `MappingSchema`, `ApplicationError`, `ValidationError`
- Suffix with intent: `*Schema` for Marshmallow, `*Error` for exceptions

**Routes:**
- Lowercase, kebab-case paths: `/api/suggestions`, `/admin/proposals`, `/go-suggestions`
- HTTP verbs: GET (retrieve), POST (create/submit), PUT (update), DELETE (remove)

## Where to Add New Code

**New Feature (mapping type):**
- Primary code: `src/blueprints/api.py` (new POST endpoint) + `src/core/models.py` (new Model class)
- Tests: `tests/test_api.py` + `tests/test_models.py`
- Schema: Add to `src/core/schemas.py`
- Example: KE-GO mapping added here (see `GoMappingModel` in models.py)

**New Suggestion Signal:**
- Implementation: Add method to `src/suggestions/pathway.py` or `src/suggestions/go.py`
- Scoring: Update `combine_scored_items()` call with new weight in `src/suggestions/scoring.py`
- Config: Add tunable parameters to `scoring_config.yaml`
- Example: Ontology signal added via `_compute_ontology_tag_scores()` method

**New Service:**
- Implementation: `src/services/new_service.py`
- Registration: Add property to `ServiceContainer` in `src/services/container.py`
- Usage: Blueprint receives via `set_models()` or direct `app.service_container.new_service` access

**New Blueprint/Route:**
- Implementation: Create `src/blueprints/new_bp.py` with blueprint and `set_models()` function
- Registration: Import in `app.py`, call `set_models()`, register with `app.register_blueprint()`
- Example: `admin.py` blueprint added this way

**Utilities:**
- Shared text logic: `src/utils/text.py`
- Shared formatting: `src/utils/timezone.py`
- New utility module: Create `src/utils/new_util.py`, import as `from src.utils.new_util import ...`

**Database Changes:**
- New table: Add CREATE TABLE in `Database.init_db()` in `src/core/models.py`
- Schema migration: Add `_migrate_*()` method and call from `init_db()`
- New model: Create class in `src/core/models.py` inheriting from nothing (stateless), storing `self.db: Database`

## Special Directories

**data/:**
- Purpose: Pre-computed embeddings and metadata
- Generated: Yes — run scripts in `scripts/` to generate
- Committed: No — files are large (embeddings .npy files), downloaded at setup
- Size: ~100MB+ (embeddings for 1561 KEs, 1012 pathways, 30K GO terms)
- Regeneration: `python scripts/precompute_*.py` (see CLAUDE.md)

**logs/:**
- Purpose: Application logs
- Generated: Yes — Flask logs to `logs/` if configured
- Committed: No — .gitignore excludes
- Rotation: Not configured; depends on deployment setup

**htmlcov/:**
- Purpose: Test coverage reports
- Generated: Yes — `pytest --cov=src --cov-report=html`
- Committed: No — .gitignore excludes

**ssl/:**
- Purpose: SSL certificates for HTTPS
- Generated: No — must be created manually or provided by deployment
- Committed: No — security risk

**.planning/codebase/:**
- Purpose: GSD mapping documents (this directory)
- Generated: Yes — by Claude Code mapper
- Committed: Yes — part of codebase documentation

**venv/:**
- Purpose: Python virtual environment
- Generated: Yes — `python -m venv venv`
- Committed: No — .gitignore excludes
- Do not edit manually

## Import Patterns & Path Organization

**Absolute imports (preferred):**
```python
from src.core.models import MappingModel, Database
from src.services.container import ServiceContainer
from src.suggestions.pathway import PathwaySuggestionService
```

**Why absolute:** Avoids relative path confusion, works from any file location, compatible with package installs.

**No relative imports in codebase:** Consistency, avoids `from ..core.models` style.

**Circular dependencies avoided:**
- Blueprints depend on models/services, not vice versa
- Models depend on database, not blueprints
- Services depend on models/config, not blueprints

**Lazy imports for heavy modules:**
- Embedding service loaded only if enabled in config (see `ServiceContainer.embedding_service` property)
- SPARQL endpoints imported only when needed (requests module in service classes)
