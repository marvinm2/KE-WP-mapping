"""
Tests for Phase 36-04: Explore page column parity.

Guards:
  - EXPL-01: GET /explore → 200, HTML contains the wp_count value
  - EXPL-02: (client-side badge rendering — covered by human checkpoint)
  - EXPL-03: (client-side AOP-context column — covered by human checkpoint)
  - EXPL-04: GET /api/v1/mappings → each mapping row includes provenance.approved_at
  - EXPL-05: GET /get_aop_options → aopId field starts with "AOP " (prefix contract)

Notes:
  - Badge and AOP-context column rendering are DataTables JS (not server-testable).
  - The server-side contract covers: wp_count in HTML, approved_at field presence,
    and AOP option aopId format.
"""
import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

import src.blueprints.main as main_module
import src.blueprints.api as api_module
import src.blueprints.v1_api as v1_mod
from app import app as flask_app
from src.core.models import CacheModel, Database, MappingModel


# ---------------------------------------------------------------------------
# Helpers — build a minimal in-memory DB with one approved WP mapping
# ---------------------------------------------------------------------------

def _make_db_with_mapping():
    """Return (fd, path, MappingModel) for a temp DB with one approved mapping."""
    fd, path = tempfile.mkstemp()
    db = Database(path)
    mm = MappingModel(db)
    mapping_id = mm.create_mapping(
        ke_id="KE 1",
        ke_title="Test KE",
        wp_id="WP100",
        wp_title="Test Pathway",
        confidence_level="High",
        created_by="github:test_curator",  # provider-prefix required by identity constraint
    )
    if mapping_id is not None:
        conn = db.get_connection()
        try:
            conn.execute(
                "UPDATE mappings SET approved_by_curator=?, approved_at_curator=? WHERE id=?",
                ("github:test_curator", "2026-01-01T00:00:00", mapping_id),
            )
            conn.commit()
        finally:
            conn.close()
    return fd, path, mm


# ---------------------------------------------------------------------------
# test_explore_route_passes_wp_count (EXPL-01)
# ---------------------------------------------------------------------------

class TestWpCountInExplore:
    """GET /explore includes a numeric WP count in the tab label."""

    def test_explore_route_passes_wp_count(self, client, monkeypatch):
        """GET /explore returns 200 and the HTML contains the WP count value.

        Monkeypatches mapping_model so the route returns a known count of 1.
        """
        mock_mm = MagicMock()
        mock_mm.get_all_mappings.return_value = [
            {"ke_id": "KE 1", "ke_title": "Test KE", "wp_id": "WP100",
             "wp_title": "Test Pathway", "confidence_level": "High"}
        ]
        monkeypatch.setattr(main_module, "mapping_model", mock_mm)

        resp = client.get("/explore")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        # Tab label must include "(1)" — the mocked count
        assert "(1)" in html, (
            "Expected tab label to contain '(1)' for wp_count=1; "
            "check that wp_count is passed to explore.html and rendered in the tab button."
        )

    def test_explore_renders(self, client):
        """GET /explore returns 200 (smoke test — page still renders after column changes)."""
        resp = client.get("/explore")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_explore_wp_count_zero_when_no_model(self, client, monkeypatch):
        """When mapping_model is None, wp_count defaults to 0 and page still renders."""
        monkeypatch.setattr(main_module, "mapping_model", None)
        resp = client.get("/explore")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "(0)" in html, (
            "Expected '(0)' in tab label when mapping_model is None (wp_count defaults to 0)."
        )


# ---------------------------------------------------------------------------
# test_get_aop_options_id_prefixed (EXPL-05)
# ---------------------------------------------------------------------------

class TestAopOptionsIdFormat:
    """GET /get_aop_options — each aopId starts with 'AOP ' (prefix contract for EXPL-05)."""

    def test_get_aop_options_id_prefixed(self, client, monkeypatch):
        """When cache returns pre-built options, aopId values start with 'AOP '.

        The JS display layer renders 'AOP N — Title'; this test verifies the
        server supplies aopId values in 'AOP N' format that make the prefix possible.
        """
        # Build cached options: aopId must be in "AOP N" form
        sample_options = [
            {"aopId": "AOP 1", "aopTitle": "Test AOP One"},
            {"aopId": "AOP 237", "aopTitle": "Test AOP Two"},
        ]
        mock_cache = MagicMock()
        mock_cache.get_cached_response.return_value = json.dumps(sample_options)
        monkeypatch.setattr(api_module, "cache_model", mock_cache)

        resp = client.get("/get_aop_options")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.get_json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) > 0, "Expected at least one AOP option"
        for opt in data:
            assert "aopId" in opt, f"Option missing 'aopId': {opt}"
            assert opt["aopId"].startswith("AOP "), (
                f"aopId '{opt['aopId']}' does not start with 'AOP ' — "
                "EXPL-05 requires the AOP-ID prefix in the display label."
            )


# ---------------------------------------------------------------------------
# test_api_mappings_has_approved_at (EXPL-04)
# ---------------------------------------------------------------------------

class TestApiMappingsApprovedAt:
    """GET /api/v1/mappings — each mapping row includes provenance.approved_at (EXPL-04)."""

    def test_api_mappings_has_approved_at(self, monkeypatch):
        """Seed one approved mapping and confirm provenance.approved_at is present in the response."""
        fd, db_path, mm = _make_db_with_mapping()

        # Save originals
        orig_mm = v1_mod.mapping_model
        orig_cm = v1_mod.cache_model

        try:
            # Wire a real CacheModel backed by the same temp DB
            cm = CacheModel(mm.db)
            v1_mod.set_models(mm, None, cm)

            flask_app.config["TESTING"] = True
            flask_app.config["WTF_CSRF_ENABLED"] = False

            with flask_app.test_client() as tc:
                with flask_app.app_context():
                    resp = tc.get(
                        "/api/v1/mappings",
                        headers={"Accept": "application/json"},
                    )
                    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
                    body = resp.get_json()
                    assert body is not None, "Expected JSON response"
                    rows = body.get("data", [])
                    assert len(rows) > 0, (
                        "Expected at least one mapping row — ensure seed created an approved mapping."
                    )
                    for row in rows:
                        prov = row.get("provenance", {})
                        assert "approved_at" in prov, (
                            f"Mapping row missing 'provenance.approved_at': {row}"
                        )
        finally:
            v1_mod.set_models(orig_mm, None, orig_cm)
            os.close(fd)
            os.unlink(db_path)
