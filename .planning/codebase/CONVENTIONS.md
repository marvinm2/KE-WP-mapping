# Coding Conventions

**Analysis Date:** 2026-02-19

## Naming Patterns

**Files:**
- Modules: `snake_case` (e.g., `pathway.py`, `embedding.py`, `error_handlers.py`)
- Classes: `PascalCase` (e.g., `PathwaySuggestionService`, `BiologicalEmbeddingService`, `ApplicationError`)
- Test files: `test_*.py` prefix (e.g., `test_models.py`, `test_app.py`, `test_rate_limiter.py`)
- Blueprints: `snake_case` with `_bp` suffix (e.g., `api_bp`, `main_bp`, `auth_bp`)

**Functions:**
- All functions: `snake_case` (e.g., `get_pathway_suggestions`, `sanitize_log`, `combine_scored_items`)
- Private functions: `_leading_underscore` prefix (e.g., `_get_genes_from_ke`, `_find_pathways_by_genes`)
- Test functions: `test_` prefix (e.g., `test_create_mapping`, `test_rate_limiter_blocks_excessive_requests`)
- Decorators and wrapper functions: descriptive `snake_case` (e.g., `handle_errors`, `monitor_performance`)

**Variables:**
- Local variables and parameters: `snake_case` (e.g., `ke_id`, `wp_title`, `confidence_level`)
- Module-level cache/state: `_with_leading_underscore` (e.g., `_config_cache`, `_database`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_SCORE_TRANSFORM`, `EMBEDDINGS_AVAILABLE`)
- Model/database field names: `snake_case` matching database schema (e.g., `created_by`, `confidence_level`, `connection_type`)

**Types:**
- Class attributes and instance variables: `snake_case` (e.g., `self.cache_model`, `self.config`, `self.aop_wiki_endpoint`)
- Type hints use standard Python conventions with imports from `typing` module (e.g., `Dict[str, any]`, `List[Dict]`, `Optional[str]`)

## Code Style

**Formatting:**
- Formatter: Black (configured in `pyproject.toml`)
- Line length: 88 characters
- Target versions: Python 3.10, 3.11

**Linting:**
- Import sorting: isort (configured in `pyproject.toml`)
- isort profile: "black" for compatibility with Black formatter
- Multi-line output mode: 3 (Vertical Hanging Indent)
- Include trailing commas: enabled for multi-line
- Force grid wrap: disabled (force_grid_wrap = 0)

**Enforced via pyproject.toml:**
- `line-length = 88`
- `target-version = ['py310', 'py311']`
- `multi_line_output = 3`
- `include_trailing_comma = true`
- `use_parentheses = true`
- `ensure_newline_before_comments = true`

## Import Organization

**Order:**
1. Standard library imports (e.g., `os`, `logging`, `json`, `sqlite3`, `datetime`)
2. Third-party library imports (e.g., `flask`, `requests`, `werkzeug`, `sentence_transformers`)
3. Relative/application imports (e.g., `from src.core.models import`, `from src.services.container import`)

**Patterns:**
- Group related imports: Logical groupings by module/function purpose, not strict alphabetical (within Black/isort compliance)
- Use full module paths with isort known_first_party: `src` is declared as first-party in pyproject.toml
- Conditional imports for optional features: `try/except` for packages that may not be installed (e.g., `sentence_transformers`, `torch`)
- Type hints: Use `from typing import TYPE_CHECKING` with `if TYPE_CHECKING:` blocks for circular import avoidance

**Path Aliases:**
- No aliases configured. All imports use full paths from project root
- Blueprints imported directly: `from src.blueprints import admin_bp, api_bp, auth_bp, main_bp`
- Services imported by full path: `from src.services.container import ServiceContainer`

## Error Handling

**Patterns:**
- Custom exception hierarchy in `src/core/error_handlers.py`:
  - `ApplicationError` base class with `message`, `status_code`, `details` attributes
  - Subclasses: `ValidationError` (400), `AuthenticationError` (401), `AuthorizationError` (403), `NotFoundError` (404), `ServiceError` (503)
- Centralized error handler registration via `register_error_handlers(app)` in `src/core/error_handlers.py`
- Route decorator: `@handle_errors` wrapper in `src/core/error_handlers.py` for exception catching in individual routes
- Standardized error responses: JSON for API/admin routes, HTML templates for page routes
- Error logging: Always use `logger.error()`, `logger.warning()`, or `logger.exception()` with sanitized inputs via `sanitize_log()`

**Security note:** Use `sanitize_log()` utility from `src/utils/text.py` to prevent log injection attacks before logging user input or request data

## Logging

**Framework:** Python standard `logging` module

**Patterns:**
- Module-level logger: `logger = logging.getLogger(__name__)` at top of each file
- Log levels:
  - `logger.info()`: General application flow (service initialization, major operations)
  - `logger.debug()`: Detailed debugging information (singleton creation, configuration loading)
  - `logger.warning()`: Potential issues (authentication failures, invalid inputs, SPARQL timeouts)
  - `logger.error()`: Error conditions (application errors, external service failures)
  - `logger.exception()`: Exceptions caught with full traceback (for `except` blocks)
- Always sanitize user input before logging: `logger.info("Request: %s", sanitize_log(request.url))`
- Structured logging: Use `%s` placeholders for values, never f-strings in log calls (easier to search logs)
- Security: Log errors/auth failures at WARNING level, success at INFO level

## Comments

**When to Comment:**
- Class docstrings: Always include for public classes with purpose and responsibilities
- Function docstrings: Always include, especially for service methods with complex logic
- Complex algorithms: Comment non-obvious logic (e.g., score transformation calculation, multi-signal weighting)
- Gotchas: Comment surprising behavior or implementation details (e.g., "First writer wins" in `_signal_data` merging)

**JSDoc/TSDoc:**
- Use standard Python docstrings (triple-quoted) for all public modules, classes, and functions
- Format: Google-style docstrings with Args, Returns, Raises, Examples sections
- Module docstrings: Single-line purpose + blank line + multi-line description
- Function docstrings: Description → Args (type and description) → Returns (type and description) → Examples (if complex)

**Examples from codebase:**
```python
def sanitize_log(value: Any) -> str:
    """
    Sanitize input for safe logging to prevent log injection attacks.

    [detailed description...]

    Args:
        value: Input to sanitize (any type, will be stringified)

    Returns:
        str: Sanitized string safe for inclusion in log messages

    Security:
        [Security considerations...]

    Examples:
        >>> sanitize_log("user\\nFAKE: Admin access granted")
        'user\\\\nFAKE: Admin access granted'
    """
```

## Function Design

**Size:**
- Prefer functions under 50 lines
- Large functions (>100 lines) should be split into smaller private helper functions
- Examples: `get_pathway_suggestions()` delegates to `_find_pathways_by_genes()`, `_get_embedding_based_suggestions()`, `_compute_ontology_tag_scores()`

**Parameters:**
- Positional parameters: Required values first (e.g., `ke_id`, `wp_id`)
- Optional parameters: After required, with sensible defaults (e.g., `limit: int = 10`, `config=None`)
- Type hints: All parameters should have type hints
- Keyword-only for clarity: Complex functions may use `*` to enforce keyword arguments after certain point

**Return Values:**
- Type hints on all return values
- Consistent return types: Functions returning collections always return same type (e.g., always `List[Dict]` not sometimes list, sometimes None)
- Error handling: Raise exceptions rather than returning None/error codes
- Dictionary returns: Include meaningful keys with consistent naming (e.g., `ke_id`, `wp_title`, `hybrid_score`)

## Module Design

**Exports:**
- Services are instantiated through `ServiceContainer` (in `src/services/container.py`) using property pattern for singletons
- Blueprints are initialized with model instances via `set_models()` functions
- Models are initialized in app factory and injected into blueprints
- Configuration accessed via `get_config()` function (returns config class instance)

**Barrel Files:**
- `src/blueprints/__init__.py`: Exports all blueprint instances for import in `app.py`
- Pattern: `from src.blueprints import admin_bp, api_bp, auth_bp, main_bp`

**Service Pattern:**
- Services in `src/services/` are classes (e.g., `PathwaySuggestionService`, `RateLimiter`, `MetricsCollector`)
- Services accept dependencies in `__init__` for testability (e.g., `cache_model`, `embedding_service`, `config`)
- Singleton-like access via `ServiceContainer` properties with lazy initialization

---

*Convention analysis: 2026-02-19*
