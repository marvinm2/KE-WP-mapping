"""
Tests for the public REST API v1 blueprint (/api/v1/).
"""
import csv
import io
import json
import os
import tempfile
from unittest.mock import patch

import pytest

# Import app for test client construction (same pattern as conftest.py)
from app import app as flask_app
import src.blueprints.v1_api as v1_mod
from src.core.models import CacheModel, Database, GoMappingModel, MappingModel


# ---------------------------------------------------------------------------
# Per-test DB fixture — re-wires v1_api module-level models each test
# ---------------------------------------------------------------------------

@pytest.fixture
def v1_client():
    """
    Test client that re-wires the v1_api blueprint to a fresh temp-file DB.

    Each invocation:
    - Creates a new SQLite temp file DB with fully-migrated schema
    - Calls v1_mod.set_models() to replace the module-level singletons
    - Yields (test_client, mapping_model, go_mapping_model) so tests can seed data
    - Restores original module-level models after the test
    """
    fd, db_path = tempfile.mkstemp()

    db = Database(db_path)
    mm = MappingModel(db)
    gm = GoMappingModel(db)
    cm = CacheModel(db)

    # Save originals so we can restore after test
    orig_mm = v1_mod.mapping_model
    orig_gm = v1_mod.go_mapping_model
    orig_cm = v1_mod.cache_model

    # Inject fresh models
    v1_mod.set_models(mm, gm, cm)

    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.test_client() as test_client:
        with flask_app.app_context():
            yield test_client, mm, gm

    # Restore originals
    v1_mod.set_models(orig_mm, orig_gm, orig_cm)

    os.close(fd)
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# Seed helpers — operate on a given MappingModel / GoMappingModel instance
# ---------------------------------------------------------------------------

def _seed_mapping(mm, ke_id="KE 1", wp_id="WP123", confidence="High"):
    """Insert one approved KE-WP mapping.  Returns the row uuid."""
    mapping_id = mm.create_mapping(
        ke_id=ke_id,
        ke_title=f"Test KE {ke_id}",
        wp_id=wp_id,
        wp_title=f"Test Pathway {wp_id}",
        confidence_level=confidence,
        created_by="test_curator",
    )
    if mapping_id is None:
        return None

    conn = mm.db.get_connection()
    try:
        conn.execute(
            "UPDATE mappings SET approved_by_curator=?, approved_at_curator=? WHERE id=?",
            ("test_curator", "2026-01-01T00:00:00", mapping_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT uuid FROM mappings WHERE id=?", (mapping_id,)
        ).fetchone()
        return row["uuid"] if row else None
    finally:
        conn.close()


def _seed_go_mapping(gm, ke_id="KE 1", go_id="GO:0001234", go_name="test process",
                     confidence="High"):
    """Insert one approved KE-GO mapping.  Returns the row uuid."""
    mapping_id = gm.create_mapping(
        ke_id=ke_id,
        ke_title=f"Test KE {ke_id}",
        go_id=go_id,
        go_name=go_name,
        confidence_level=confidence,
        created_by="test_curator",
    )
    if mapping_id is None:
        return None

    conn = gm.db.get_connection()
    try:
        conn.execute(
            "UPDATE ke_go_mappings SET approved_by_curator=?, approved_at_curator=? WHERE id=?",
            ("test_curator", "2026-01-01T00:00:00", mapping_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT uuid FROM ke_go_mappings WHERE id=?", (mapping_id,)
        ).fetchone()
        return row["uuid"] if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestListMappings:
    def test_list_mappings_empty(self, v1_client):
        """GET /api/v1/mappings on empty DB returns 200, data=[], pagination.total=0."""
        client, mm, gm = v1_client

        response = client.get("/api/v1/mappings")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"] == []
        assert data["pagination"]["total"] == 0

    def test_list_mappings_returns_json_envelope(self, v1_client):
        """Seed 1 mapping; GET returns 200 with correct envelope keys on each item."""
        client, mm, gm = v1_client
        _seed_mapping(mm, ke_id="KE T2", wp_id="WP_T2")

        response = client.get("/api/v1/mappings")
        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        item = data["data"][0]
        for key in ("uuid", "ke_id", "ke_name", "pathway_id", "pathway_title",
                    "confidence_level", "provenance"):
            assert key in item, f"Missing key: {key}"

    def test_list_mappings_pagination_envelope(self, v1_client):
        """Pagination dict contains all required fields; single-page set has next/prev=None."""
        client, mm, gm = v1_client
        _seed_mapping(mm, ke_id="KE T3", wp_id="WP_T3")

        response = client.get("/api/v1/mappings")
        assert response.status_code == 200
        data = response.get_json()
        pagination = data["pagination"]
        for key in ("page", "per_page", "total", "total_pages", "next", "prev"):
            assert key in pagination, f"Missing pagination key: {key}"
        assert pagination["page"] == 1
        assert pagination["prev"] is None
        assert pagination["next"] is None

    def test_list_mappings_csv(self, v1_client):
        """Accept: text/csv returns 200 with text/csv content-type and 'uuid' in header."""
        client, mm, gm = v1_client
        _seed_mapping(mm, ke_id="KE T4", wp_id="WP_T4")

        response = client.get("/api/v1/mappings", headers={"Accept": "text/csv"})
        assert response.status_code == 200
        assert "text/csv" in response.content_type
        body = response.data.decode("utf-8")
        first_line = body.splitlines()[0]
        assert "uuid" in first_line

    def test_list_mappings_filter_ke_id(self, v1_client):
        """?ke_id=X returns only the mapping with ke_id=X, not others."""
        client, mm, gm = v1_client
        _seed_mapping(mm, ke_id="KE Filter5A", wp_id="WP_F5A")
        _seed_mapping(mm, ke_id="KE Filter5B", wp_id="WP_F5B")

        response = client.get("/api/v1/mappings?ke_id=KE Filter5A")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["data"]) == 1
        assert data["data"][0]["ke_id"] == "KE Filter5A"

    def test_list_mappings_filter_pathway_id(self, v1_client):
        """?pathway_id=WP_F6_P1 returns only WP_F6_P1 mapping."""
        client, mm, gm = v1_client
        _seed_mapping(mm, ke_id="KE Filter6A", wp_id="WP_F6_P1")
        _seed_mapping(mm, ke_id="KE Filter6B", wp_id="WP_F6_P2")

        response = client.get("/api/v1/mappings?pathway_id=WP_F6_P1")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["data"]) == 1
        assert data["data"][0]["pathway_id"] == "WP_F6_P1"

    def test_list_mappings_filter_confidence_level(self, v1_client):
        """?confidence_level=High returns only High confidence mappings."""
        client, mm, gm = v1_client
        _seed_mapping(mm, ke_id="KE Filter7A", wp_id="WP_F7A", confidence="High")
        _seed_mapping(mm, ke_id="KE Filter7B", wp_id="WP_F7B", confidence="Low")

        response = client.get("/api/v1/mappings?confidence_level=High")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["data"]) == 1
        assert data["data"][0]["confidence_level"].lower() == "high"

    def test_list_mappings_unknown_uuid(self, v1_client):
        """GET /api/v1/mappings/nonexistent-uuid returns 404 with 'error' key."""
        client, mm, gm = v1_client

        response = client.get("/api/v1/mappings/nonexistent-uuid-000000")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    def test_get_mapping_by_uuid(self, v1_client):
        """Seed 1 mapping; GET /api/v1/mappings/<uuid> returns 200 with matching uuid."""
        client, mm, gm = v1_client
        mapping_uuid = _seed_mapping(mm, ke_id="KE T9", wp_id="WP_T9")
        assert mapping_uuid is not None

        response = client.get(f"/api/v1/mappings/{mapping_uuid}")
        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert data["data"]["uuid"] == mapping_uuid


class TestListGoMappings:
    def test_list_go_mappings_empty(self, v1_client):
        """GET /api/v1/go-mappings on empty DB returns 200 with data=[]."""
        client, mm, gm = v1_client

        response = client.get("/api/v1/go-mappings")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"] == []

    def test_list_go_mappings_returns_json_envelope(self, v1_client):
        """Seed 1 GO mapping; response has go_term_id/go_term_name/go_namespace keys."""
        client, mm, gm = v1_client
        _seed_go_mapping(gm, ke_id="KE GO11", go_id="GO:0011111", go_name="test bp process")

        response = client.get("/api/v1/go-mappings")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["data"]) == 1
        item = data["data"][0]
        for key in ("go_term_id", "go_term_name", "go_namespace"):
            assert key in item, f"Missing key: {key}"
        assert item["go_namespace"] == "biological_process"

    def test_list_go_mappings_csv(self, v1_client):
        """Accept: text/csv returns 200 with text/csv content-type."""
        client, mm, gm = v1_client
        _seed_go_mapping(gm, ke_id="KE GO12", go_id="GO:0012121", go_name="csv test process")

        response = client.get("/api/v1/go-mappings", headers={"Accept": "text/csv"})
        assert response.status_code == 200
        assert "text/csv" in response.content_type
        body = response.data.decode("utf-8")
        first_line = body.splitlines()[0]
        assert "uuid" in first_line

    def test_get_go_mapping_by_uuid(self, v1_client):
        """Seed 1 GO mapping; GET /api/v1/go-mappings/<uuid> returns 200."""
        client, mm, gm = v1_client
        go_uuid = _seed_go_mapping(gm, ke_id="KE GO13", go_id="GO:0013131",
                                   go_name="test go 13")
        assert go_uuid is not None

        response = client.get(f"/api/v1/go-mappings/{go_uuid}")
        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert data["data"]["uuid"] == go_uuid

    def test_get_go_mapping_unknown_uuid(self, v1_client):
        """GET /api/v1/go-mappings/nonexistent returns 404 with 'error' key."""
        client, mm, gm = v1_client

        response = client.get("/api/v1/go-mappings/nonexistent-go-uuid-000")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data


class TestCors:
    def test_cors_header_present(self, v1_client):
        """GET /api/v1/mappings includes Access-Control-Allow-Origin: *."""
        client, mm, gm = v1_client

        response = client.get("/api/v1/mappings")
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "*"

    def test_cors_not_on_internal_routes(self, client):
        """GET /check (internal api_bp) does NOT carry Access-Control-Allow-Origin."""
        response = client.post("/check", data={"ke_id": "KE:0", "wp_id": "WP:0"})
        assert "Access-Control-Allow-Origin" not in response.headers


class TestPagination:
    def test_per_page_clamped_to_200(self, v1_client):
        """?per_page=999 results in per_page <= 200 in the pagination envelope."""
        client, mm, gm = v1_client

        response = client.get("/api/v1/mappings?per_page=999")
        assert response.status_code == 200
        data = response.get_json()
        assert data["pagination"]["per_page"] <= 200

    def test_page_defaults_to_1(self, v1_client):
        """?page=abc (non-integer) falls back to page=1."""
        client, mm, gm = v1_client

        response = client.get("/api/v1/mappings?page=abc")
        assert response.status_code == 200
        data = response.get_json()
        assert data["pagination"]["page"] == 1


class TestAopFilter:
    def test_aop_id_invalid_returns_400(self, v1_client, monkeypatch):
        """?aop_id= with _resolve_aop_ke_ids raising ValueError returns 400 with 'error'."""
        client, mm, gm = v1_client

        def _raise_value_error(aop_id):
            raise ValueError("test error")

        monkeypatch.setattr(v1_mod, "_resolve_aop_ke_ids", _raise_value_error)

        response = client.get("/api/v1/mappings?aop_id=INVALID_NONEXISTENT_AOP_99999")
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
