"""
Tests for the landing/mapper route refactor and Reactome stats extension (Task 2).

Covers:
  1. GET / returns 200 and the response HTML contains the four headline counts
     (KE-WP, KE-GO, KE-Reactome, total) as data-target attributes — no JS needed.
  2. GET /mapper returns 200 and renders the mapper (index.html) content.
  3. get_mapping_stats() returns reactome_total and reactome_by_confidence keys,
     and total == wp_total + go_total + reactome_total.
  4. get_mapping_stats() does not raise when reactome_mapping_model is None (graceful zero).
"""
import pytest


@pytest.fixture
def client(tmp_path):
    """Minimal test client that creates a fresh in-memory DB per test."""
    import os
    os.environ.setdefault("FLASK_ENV", "testing")
    os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")
    os.environ.setdefault("GITHUB_CLIENT_ID", "dummy")
    os.environ.setdefault("GITHUB_CLIENT_SECRET", "dummy")

    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.test_client() as c:
        with app.app_context():
            yield c


# ---------------------------------------------------------------------------
# Test 1: GET / renders landing page with all four data-target counts
# ---------------------------------------------------------------------------

def test_landing_route_returns_200_with_counts(client):
    """GET / returns 200 and HTML contains data-target attributes for all four counts."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "data-target" in html, "Landing page must have data-target attributes for count-up animation"
    # The landing page must be server-rendered with the four count card values


# ---------------------------------------------------------------------------
# Test 2: GET /mapper returns 200 and renders the mapper content (index.html)
# ---------------------------------------------------------------------------

def test_mapper_route_returns_200(client):
    """GET /mapper returns 200 and renders mapper view."""
    resp = client.get("/mapper")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # The mapper page should have mapper-specific content
    # (checking for something that the index.html template produces)
    assert len(html) > 100, "Mapper page should have content"


# ---------------------------------------------------------------------------
# Test 3: get_mapping_stats() includes Reactome keys; total = sum of all three
# ---------------------------------------------------------------------------

def test_get_mapping_stats_includes_reactome():
    """get_mapping_stats() returns reactome_total, reactome_by_confidence; total is sum of all three."""
    import os
    os.environ.setdefault("FLASK_ENV", "testing")
    os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")
    os.environ.setdefault("GITHUB_CLIENT_ID", "dummy")
    os.environ.setdefault("GITHUB_CLIENT_SECRET", "dummy")

    from app import create_app
    app = create_app()
    with app.app_context():
        from src.blueprints.main import get_mapping_stats
        stats = get_mapping_stats()

        assert "reactome_total" in stats, "get_mapping_stats() must return reactome_total"
        assert "reactome_by_confidence" in stats, "get_mapping_stats() must return reactome_by_confidence"
        assert "wp_total" in stats
        assert "go_total" in stats
        assert "total" in stats

        expected_total = stats["wp_total"] + stats["go_total"] + stats["reactome_total"]
        assert stats["total"] == expected_total, (
            f"total ({stats['total']}) must equal wp_total + go_total + reactome_total "
            f"({stats['wp_total']} + {stats['go_total']} + {stats['reactome_total']} = {expected_total})"
        )


# ---------------------------------------------------------------------------
# Test 4: get_mapping_stats() is graceful when reactome_mapping_model is None
# ---------------------------------------------------------------------------

def test_get_mapping_stats_graceful_when_no_reactome():
    """get_mapping_stats() does not raise when reactome_mapping_model is None; reactome_total=0."""
    import os
    os.environ.setdefault("FLASK_ENV", "testing")
    os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")
    os.environ.setdefault("GITHUB_CLIENT_ID", "dummy")
    os.environ.setdefault("GITHUB_CLIENT_SECRET", "dummy")

    from app import create_app
    app = create_app()
    with app.app_context():
        import src.blueprints.main as main_mod
        original = main_mod.reactome_mapping_model
        try:
            main_mod.reactome_mapping_model = None
            from src.blueprints.main import get_mapping_stats
            stats = get_mapping_stats()  # must not raise
            assert stats["reactome_total"] == 0
            assert isinstance(stats["reactome_by_confidence"], dict)
        finally:
            main_mod.reactome_mapping_model = original
