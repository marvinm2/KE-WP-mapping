# Technology Stack

**Analysis Date:** 2026-02-19

## Languages

**Primary:**
- Python 3.12 - Application core, API endpoints, data processing
- HTML/Jinja2 - Server-side templating for Flask views
- JavaScript - Client-side interactivity (minimal, mostly HTML)

**Secondary:**
- Bash - Development scripts and Makefile commands
- YAML - Configuration (scoring_config.yaml)

## Runtime

**Environment:**
- Python 3.12 (slim-bookworm in Docker)
- WSGI Server: Gunicorn 22.0.0 (production) / Flask dev server (development)

**Package Manager:**
- pip (Python package manager)
- Lockfile: No requirements.lock file - requirements.txt and requirements-dev.txt pinned versions

## Frameworks

**Core:**
- Flask 3.1.2 - Web framework, blueprints for modular routing
- Flask-WTF 1.2.1 - CSRF protection
- Authlib 1.6.7 - OAuth 2.0 integration (GitHub OAuth)

**Testing:**
- pytest 8.3.4 - Test runner
- pytest-cov 6.0.0 - Coverage reporting
- pytest-flask 1.3.0 - Flask-specific fixtures
- pytest-mock 3.12.0 - Mocking utilities
- pytest-xdist 3.5.0 - Parallel test execution
- pytest-benchmark 4.0.0 - Performance benchmarking

**Build/Dev:**
- Black 23.12.1 - Code formatting
- isort 5.12.0 - Import sorting
- Flake8 6.0.0 - Linting
- mypy 1.5.1 - Type checking
- Pylint 2.17.7 - Code analysis
- pre-commit 3.4.0 - Git hooks framework

**Development Tools:**
- Bandit 1.7.5 - Security vulnerability scanner
- Safety 3.0.1 - Dependency vulnerability checker
- pip-audit 2.10.0 - Package audit tool
- Radon 6.0.1 - Code complexity metrics
- Xenon 0.9.1 - Complexity thresholds

## Key Dependencies

**Critical (Application Logic):**
- `transformers==4.48.3` - HuggingFace transformer models for BioBERT
- `sentence-transformers==3.4.1` - Semantic similarity with BioBERT embeddings
- `torch==2.6.0+cpu` - PyTorch (CPU variant for embedding computations)
- `numpy==1.26.4` - Numerical operations, embedding processing
- `pandas==2.2.3` - Data manipulation and analysis

**Framework & Web:**
- `requests==2.32.5` - HTTP client for SPARQL queries and external APIs
- `marshmallow==3.26.2` - Request/response validation and serialization
- `python-dotenv==1.2.1` - Environment variable loading

**Infrastructure:**
- `gunicorn==22.0.0` - Production WSGI application server
- `tqdm==4.67.3` - Progress bars for batch operations
- SQLite3 - Built-in, file-based relational database (via Python sqlite3)

## Configuration

**Environment:**
- Configuration classes in `src/core/config.py`: `DevelopmentConfig`, `ProductionConfig`, `TestingConfig`
- Environment variables loaded from `.env` file via `python-dotenv`
- Key configurations:
  - `FLASK_SECRET_KEY` - Session/CSRF secret
  - `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` - OAuth credentials
  - `DATABASE_PATH` - SQLite database location
  - `ADMIN_USERS` - Comma-separated GitHub usernames with admin access
  - `RATELIMIT_STORAGE_URL` - Rate limit storage (default: memory://)
  - `FLASK_ENV` - Environment mode (development/production/testing)

**Build:**
- Dockerfile: Multi-stage build (builder stage with dependencies, runtime stage)
- docker-compose.yml: Service orchestration configuration
- .dockerignore: Docker build exclusions
- pyproject.toml: Black, isort configuration
- Makefile: Common development commands (install, test, run, docker-build, etc.)

## Platform Requirements

**Development:**
- Python 3.12
- pip for dependency management
- SQLite3 support
- ~2GB disk for pre-computed embeddings (data/*.npy files)
- Optional: CUDA-capable GPU (auto-falls back to CPU)

**Production:**
- Python 3.12
- Gunicorn WSGI server
- Docker (for containerized deployment)
- SQLite3 database (file-based storage)
- 80/443 for HTTP/HTTPS
- Minimum 4GB RAM for embedding service initialization
- Storage for SQLite database file and pre-computed embeddings (~230MB)

**Pre-computed Data (in `data/`):**
- `ke_embeddings.npy` (4.8 MB) - 1561 Key Events
- `pathway_title_embeddings.npy` (3.1 MB) - 1012 pathways
- `go_bp_embeddings.npy` (75.8 MB) - ~30K Gene Ontology terms
- `go_bp_name_embeddings.npy` (75.9 MB) - GO BP name-only vectors
- `go_bp_metadata.json` (16.5 MB) - GO term definitions, synonyms
- `go_bp_gene_annotations.json` (2.0 MB) - GO-to-gene mappings
- `ke_metadata.json` (1.8 MB) - Key Event dropdown data (avoids SPARQL)
- `pathway_metadata.json` (2.1 MB) - Pathway dropdown data (avoids SPARQL)

---

*Stack analysis: 2026-02-19*
