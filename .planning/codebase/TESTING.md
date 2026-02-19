# Testing Patterns

**Analysis Date:** 2026-02-19

## Test Framework

**Runner:**
- pytest 7.x+
- Config: `pytest.ini` at project root
- Entry point: `tests/` directory (all test files auto-discovered)

**Assertion Library:**
- Python standard `assert` statements (no separate assertion library)

**Run Commands:**
```bash
make test              # Run all tests with coverage
pytest                 # Run all tests (verbose by verbose mode from pytest.ini)
pytest tests/          # Run specific test directory
pytest tests/test_models.py::TestMappingModel::test_create_mapping  # Run specific test
pytest --lf           # Run last failed tests
pytest --cov=src      # Generate coverage report (also default with make test)
```

**Coverage Configuration (pytest.ini):**
```ini
--cov=src                    # Only measure coverage for src/ directory
--cov-report=term-missing    # Terminal output with missing line numbers
--cov-report=html:htmlcov    # Generate HTML coverage report
--cov-fail-under=80          # Fail if coverage drops below 80%
```

**Test Output Options (pytest.ini):**
```ini
--verbose                    # Show each test name
--tb=short                   # Short traceback format (no full context)
```

**Warning Filters (pytest.ini):**
```ini
ignore::DeprecationWarning
ignore::PendingDeprecationWarning
```

## Test File Organization

**Location:**
- Tests are co-located in `tests/` directory mirroring source structure
- Test files are separate from source files (not in `src/` directory)

**Naming:**
- Test files: `test_*.py` prefix (e.g., `test_models.py`, `test_app.py`)
- Test classes: `Test*` prefix (e.g., `TestMappingModel`, `TestRoutes`)
- Test methods: `test_*` prefix (e.g., `test_create_mapping`, `test_rate_limiter_blocks_excessive_requests`)

**Structure:**
```
tests/
├── conftest.py              # Global pytest fixtures and configuration
├── test_models.py           # Tests for database models (MappingModel, ProposalModel, etc.)
├── test_app.py              # Tests for Flask routes (API, pages, auth)
├── test_rate_limiter.py     # Tests for rate limiting service
└── [future test files]
```

## Test Structure

**Suite Organization (from conftest.py and test_app.py):**

```python
import pytest
from unittest.mock import MagicMock, patch

class TestMappingAPI:
    """Grouped tests for API endpoint - uses class to organize related tests"""

    def test_check_entry_missing_params(self, client):
        """Test single failure case - docstring describes the scenario"""
        response = client.post("/check", data={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
```

**Setup Patterns:**
- Fixtures in `conftest.py` provide test client, database, and authenticated sessions
- Fixture scope: Function-level (fresh state per test, default `@pytest.fixture`)
- Database fixture creates temp SQLite DB, initializes tables, cleans up after test

**Teardown Pattern:**
- Automatic via fixture context managers (`with app.test_client()` blocks)
- Manual cleanup: `os.close(db_fd)`, `os.unlink(db_path)` in fixture teardown

**Assertion Pattern:**
- Simple `assert` statements for boolean checks
- Membership: `assert "key" in dict` or `assert value in list`
- Status codes: `assert response.status_code == 200`
- Data parsing: `data = json.loads(response.data)` then assert on parsed data

## Mocking

**Framework:** `unittest.mock` from standard library

**Patterns (from test_app.py):**

```python
from unittest.mock import MagicMock, patch

@patch("src.blueprints.api.ke_metadata", [
    {
        "KEtitle": "Test KE Title",
        "KElabel": "KE:1",
        "KEpage": "http://example.com",
    }
])
def test_get_ke_options_success(self, client):
    """Patch module-level global variable"""
    response = client.get("/get_ke_options")
    assert response.status_code == 200

@patch("requests.post")
def test_sparql_timeout(self, mock_post, client):
    """Patch external library call"""
    mock_post.side_effect = Exception("Timeout")
    response = client.get("/get_ke_options")
    assert response.status_code in [200, 500]

@patch("src.blueprints.api.cache_model")
@patch("src.blueprints.api.mapping_model")
@patch("requests.post")
def test_ke_context_returns_json_structure(self, mock_post, mock_mapping, mock_cache, client):
    """Stack multiple patches - parameters ordered from innermost to outermost decorator"""
    mock_cache.get_cached_response.return_value = None
    mock_mapping.get_mappings_by_ke.return_value = [
        {"wp_id": "WP100", "wp_title": "Test Pathway", "confidence_level": "high"}
    ]

    response = client.get("/api/ke_context/KE%2055")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "ke_id" in data
```

**What to Mock:**
- External API calls: `requests.post`, `requests.get` for SPARQL endpoints, GitHub OAuth
- Database models in blueprint-level tests: `@patch("src.blueprints.api.mapping_model")` to isolate API logic
- Global module-level variables: Pre-computed metadata arrays to avoid file I/O in tests
- Time-dependent operations: Use `time.sleep()` for window expiry tests (see `test_rate_limiter.py`)

**What NOT to Mock:**
- Database operations in model unit tests: `test_models.py` creates real temp database and tests actual SQL
- Flask test client: Use real Flask app with test config, not mocked
- Error classes and exceptions: Let real errors be raised for error handling tests

## Fixtures and Factories

**Test Data (from conftest.py):**

```python
@pytest.fixture
def client():
    """Create a test client"""
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()

    # Set up environment variables for testing
    os.environ["FLASK_SECRET_KEY"] = "test-secret-key"
    os.environ["DATABASE_PATH"] = db_path

    # Configure app for testing
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

    with app.test_client() as client:
        with app.app_context():
            # Initialize test database
            test_db = Database(db_path)
            test_db.init_db()
            yield client

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def auth_client(client):
    """Create an authenticated test client"""
    with client.session_transaction() as sess:
        sess["user"] = {"username": "testuser", "email": "test@example.com"}
    return client

@pytest.fixture
def guest_client(client):
    """Create a guest-authenticated test client"""
    with client.session_transaction() as sess:
        sess["user"] = {
            "username": "guest-test-participant",
            "email": "workshop-guest",
            "is_guest": True,
        }
    return client
```

**Location:**
- Global fixtures in `tests/conftest.py`
- Shared model fixtures (e.g., `mapping_model`, `proposal_model`, `test_db`) in `conftest.py`
- Test-class-specific fixtures defined at class level or in same test file

**Naming:**
- Fixture names match the entity: `client`, `auth_client`, `guest_client`, `test_db`, `mapping_model`
- Parameter name in test function matches fixture name: `def test_something(self, client):`

## Coverage

**Requirements:** 80% minimum enforced by `--cov-fail-under=80` in pytest.ini

**View Coverage:**
```bash
# Terminal output with missing lines
pytest --cov=src --cov-report=term-missing

# Generate HTML report (view in htmlcov/index.html)
pytest --cov=src --cov-report=html:htmlcov
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Coverage Target Areas:**
- Model layer: All database operations in `src/core/models.py` (CRUD, queries)
- Service layer: Core business logic in `src/services/` and `src/suggestions/`
- Blueprint routes: All API endpoints and main page routes
- Error handling: Both success and error paths in route handlers
- Utilities: Text processing, logging utilities, config loading

## Test Types

**Unit Tests:**
- Scope: Individual functions, methods, classes in isolation
- Files: `test_models.py` (database models), `test_rate_limiter.py` (rate limiter service)
- Approach: Create minimal test fixtures (temp DB for models), mock external deps, assert on return values
- Example: `TestMappingModel::test_create_mapping` creates model, calls create, asserts ID returned

**Integration Tests:**
- Scope: Multiple components working together (route → service → model → database)
- Files: `test_app.py` (Flask routes with real/mocked services)
- Approach: Use Flask test client, real app config, optionally mock external APIs (SPARQL, GitHub)
- Example: `TestRoutes::test_index_route` calls GET / with test client, asserts 200 + content

**E2E Tests:**
- Status: Not implemented currently
- Framework that would be used: Selenium or Playwright for browser automation (if added)
- Would test: Full user workflows (login → map → submit → admin review)

## Common Patterns

**Async Testing:**
Not applicable - Flask is synchronous. All tests use synchronous Flask test client.

**Error Testing (from test_app.py):**

```python
def test_submit_missing_params(self, auth_client):
    """Test that missing parameters return 400 with error key"""
    response = auth_client.post("/submit", data={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data

def test_login_required_submit(self, client):
    """Test that unauthenticated request returns 401"""
    response = client.post("/submit", data={"ke_id": "KE:1"})
    assert response.status_code == 401

def test_guest_cannot_access_admin(self, guest_client):
    """Test that guest users cannot access admin routes"""
    response = guest_client.get("/admin/proposals")
    assert response.status_code == 403
```

**Conditional Response Assertion (from test_app.py):**

```python
def test_sparql_timeout(self, mock_post, client):
    """When SPARQL fails, endpoint may return cached or error response"""
    mock_post.side_effect = Exception("Timeout")
    response = client.get("/get_ke_options")
    # Could be 200 (cached), 500 (error), or 503 (service unavailable)
    assert response.status_code in [200, 500, 503]
```

**Session/Authentication Setup (from conftest.py):**

```python
with client.session_transaction() as sess:
    sess["user"] = {"username": "testuser", "email": "test@example.com"}
    # Set other session variables as needed
```

**Mocking Flask Models (from test_app.py):**

```python
@patch("src.blueprints.api.cache_model")
@patch("src.blueprints.api.mapping_model")
def test_something(self, mock_mapping, mock_cache, client):
    """Mock the global model instances in the blueprint"""
    mock_cache.get_cached_response.return_value = None
    mock_mapping.get_mappings_by_ke.return_value = []
```

## Test Running in CI/Development

**Quick Local Run:**
```bash
pytest -v                    # Verbose output, test names
pytest -v --tb=short         # Short traceback for failures
pytest tests/test_models.py  # Single test file
```

**With Coverage:**
```bash
make test                    # Full test + coverage (configured in Makefile)
pytest --cov=src --cov-report=term-missing  # Manual coverage
```

**Parallel Testing (if needed):**
```bash
pip install pytest-xdist
pytest -n auto               # Run tests in parallel (not currently used in Makefile)
```

---

*Testing analysis: 2026-02-19*
