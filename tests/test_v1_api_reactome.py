"""
Tests for the public REST API v1 Reactome surface (/api/v1/reactome-mappings).

Phase 26-05: Mirrors test_v1_api.py for the Reactome read endpoints.
"""
import csv
import io
import json
import os
import tempfile
from unittest.mock import patch

import pytest

from app import app as flask_app
import src.blueprints.v1_api as v1_mod
from src.core.models import (
    CacheModel,
    Database,
    GoMappingModel,
    MappingModel,
    ReactomeMappingModel,
)


# ---------------------------------------------------------------------------
# Per-test DB fixture — re-wires v1_api module-level models each test
# ---------------------------------------------------------------------------

@pytest.fixture
def v1r_client():
    """Test client that wires v1_api blueprint to a fresh temp-file DB
    with the Reactome model + metadata + gene counts present.
    """
    fd, db_path = tempfile.mkstemp()

    db = Database(db_path)
    mm = MappingModel(db)
    gm = GoMappingModel(db)
    cm = CacheModel(db)
    rm = ReactomeMappingModel(db)

    # Save originals so we can restore after test
    orig = {
        "mm": v1_mod.mapping_model,
        "gm": v1_mod.go_mapping_model,
        "cm": v1_mod.cache_model,
        "rm": getattr(v1_mod, "reactome_mapping_model", None),
        "rmeta": getattr(v1_mod, "reactome_metadata", None),
        "rgc": getattr(v1_mod, "reactome_gene_counts", None),
    }

    # Inject fresh models with Reactome wiring
    v1_mod.set_models(
        mm, gm, cm,
        reactome_mapping=rm,
        reactome_meta={"R-HSA-100": {"description": "p53 sig description"}},
        reactome_counts={"R-HSA-100": 25, "R-HSA-200": 17},
    )

    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.test_client() as test_client:
        with flask_app.app_context():
            yield test_client, rm

    # Restore
    v1_mod.set_models(
        orig["mm"], orig["gm"], orig["cm"],
        reactome_mapping=orig["rm"],
        reactome_meta=orig["rmeta"],
        reactome_counts=orig["rgc"],
    )

    os.close(fd)
    os.unlink(db_path)


def _seed_reactome(rm, rows):
    """Insert a list of approved KE-Reactome mappings via direct SQL."""
    conn = rm.db.get_connection()
    try:
        for r in rows:
            cols = ",".join(r.keys())
            placeholders = ",".join(["?"] * len(r))
            conn.execute(
                f"INSERT INTO ke_reactome_mappings ({cols}) VALUES ({placeholders})",
                list(r.values()),
            )
        conn.commit()
    finally:
        conn.close()


def _default_rows():
    """3 seed rows: KE 1+R-HSA-100 (High), KE 1+R-HSA-200 (Medium), KE 5+R-HSA-100 (Low)."""
    return [
        {
            "uuid": "u1", "ke_id": "KE 1", "ke_title": "Apoptosis",
            "reactome_id": "R-HSA-100", "pathway_name": "p53 signaling",
            "species": "Homo sapiens", "confidence_level": "High",
            "approved_by_curator": "github:alice",
            "approved_at_curator": "2026-01-01T00:00:00",
            "suggestion_score": 0.9, "proposed_by": "github:alice",
            "created_by": "github:alice",
        },
        {
            "uuid": "u2", "ke_id": "KE 1", "ke_title": "Apoptosis",
            "reactome_id": "R-HSA-200", "pathway_name": "DNA repair",
            "species": "Homo sapiens", "confidence_level": "Medium",
            "approved_by_curator": "github:alice",
            "approved_at_curator": "2026-01-02T00:00:00",
            "suggestion_score": 0.7, "proposed_by": "github:alice",
            "created_by": "github:alice",
        },
        {
            "uuid": "u3", "ke_id": "KE 5", "ke_title": "Cell prolif",
            "reactome_id": "R-HSA-100", "pathway_name": "p53 signaling",
            "species": "Homo sapiens", "confidence_level": "Low",
            "approved_by_curator": "github:bob",
            "approved_at_curator": "2026-01-03T00:00:00",
            "suggestion_score": 0.5, "proposed_by": "github:bob",
            "created_by": "github:bob",
        },
    ]


# ---------------------------------------------------------------------------
# Serializer / constants smoke tests (Task 1)
# ---------------------------------------------------------------------------

class TestSerializer:
    def test_csv_fields_constant(self):
        from src.blueprints.v1_api import _REACTOME_MAPPING_CSV_FIELDS

        assert _REACTOME_MAPPING_CSV_FIELDS[0] == "uuid"
        assert "reactome_id" in _REACTOME_MAPPING_CSV_FIELDS
        assert "pathway_name" in _REACTOME_MAPPING_CSV_FIELDS
        assert "pathway_description" in _REACTOME_MAPPING_CSV_FIELDS
        assert "reactome_gene_count" in _REACTOME_MAPPING_CSV_FIELDS
        assert "ke_aop_context" in _REACTOME_MAPPING_CSV_FIELDS
        # No GO-specific fields leak in
        for forbidden in ("go_term_id", "go_term_name", "go_namespace",
                          "go_direction", "go_definition", "go_ic", "go_depth",
                          "connection_type", "assessment_version",
                          "connection_score", "specificity_score", "evidence_score"):
            assert forbidden not in _REACTOME_MAPPING_CSV_FIELDS, (
                f"Forbidden field present: {forbidden}"
            )

    def test_serialize_basic_shape(self):
        from src.blueprints.v1_api import _serialize_reactome_mapping

        row = {
            "uuid": "u1", "ke_id": "KE 1", "ke_title": "Apoptosis",
            "reactome_id": "R-HSA-100", "pathway_name": "p53 signaling",
            "species": "Homo sapiens", "confidence_level": "High",
            "suggestion_score": 0.9,
            "approved_by_curator": "github:alice",
            "approved_at_curator": "2026-01-01",
            "proposed_by": "github:alice",
        }
        out = _serialize_reactome_mapping(row)

        assert out["uuid"] == "u1"
        assert out["ke_id"] == "KE 1"
        assert out["ke_name"] == "Apoptosis"
        assert out["reactome_id"] == "R-HSA-100"
        assert out["pathway_name"] == "p53 signaling"
        assert out["species"] == "Homo sapiens"
        assert out["confidence_level"] == "High"
        assert out["provenance"]["suggestion_score"] == 0.9
        assert out["provenance"]["approved_by"] == "github:alice"
        assert out["provenance"]["approved_at"] == "2026-01-01"
        assert out["provenance"]["proposed_by"] == "github:alice"

        # GO-specific keys must not leak in
        for forbidden in ("go_term_id", "go_term_name", "go_namespace",
                          "go_direction", "go_definition", "go_ic", "go_depth",
                          "connection_type", "assessment_version",
                          "connection_score", "specificity_score", "evidence_score"):
            assert forbidden not in out, f"Forbidden key in output: {forbidden}"

    def test_serialize_enrichment_fallback(self):
        """When metadata/counts globals are unset/None, serializer must not raise."""
        from src.blueprints.v1_api import _serialize_reactome_mapping
        import src.blueprints.v1_api as v1

        original_meta = v1.reactome_metadata
        original_counts = v1.reactome_gene_counts
        v1.reactome_metadata = None
        v1.reactome_gene_counts = None
        try:
            row = {
                "uuid": "u1", "ke_id": "KE 1", "ke_title": "Apoptosis",
                "reactome_id": "R-HSA-NEW", "pathway_name": "Unknown",
                "species": "Homo sapiens", "confidence_level": "High",
            }
            out = _serialize_reactome_mapping(row)
            assert out["pathway_description"] is None
            assert out["reactome_gene_count"] == 0
        finally:
            v1.reactome_metadata = original_meta
            v1.reactome_gene_counts = original_counts


# ---------------------------------------------------------------------------
# List endpoint tests (Task 2)
# ---------------------------------------------------------------------------

class TestListReactomeMappings:
    def test_list_reactome_mappings_paginated(self, v1r_client):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())

        resp = client.get("/api/v1/reactome-mappings")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["pagination"]["total"] == 3
        assert len(body["data"]) == 3

    def test_list_reactome_mappings_filter_ke_id(self, v1r_client):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())

        resp = client.get("/api/v1/reactome-mappings?ke_id=KE+1")
        body = resp.get_json()
        assert body["pagination"]["total"] == 2
        assert {r["ke_id"] for r in body["data"]} == {"KE 1"}

    def test_list_reactome_mappings_filter_reactome_id(self, v1r_client):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())

        resp = client.get("/api/v1/reactome-mappings?reactome_id=R-HSA-100")
        body = resp.get_json()
        assert body["pagination"]["total"] == 2
        for r in body["data"]:
            assert r["reactome_id"] == "R-HSA-100"

    def test_list_reactome_mappings_filter_confidence(self, v1r_client):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())

        resp = client.get("/api/v1/reactome-mappings?confidence_level=High")
        body = resp.get_json()
        assert body["pagination"]["total"] == 1
        assert body["data"][0]["confidence_level"] == "High"

    def test_list_reactome_mappings_csv(self, v1r_client):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())

        resp = client.get("/api/v1/reactome-mappings?format=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type
        first_line = resp.get_data(as_text=True).splitlines()[0]
        for field in (
            "uuid", "ke_id", "ke_name", "reactome_id", "pathway_name",
            "species", "confidence_level", "suggestion_score",
            "approved_by", "approved_at", "proposed_by",
            "ke_aop_context", "ke_bio_level", "pathway_description",
            "reactome_gene_count",
        ):
            assert field in first_line, f"CSV header missing field: {field}"

    def test_list_reactome_mappings_aop_filter(self, v1r_client, monkeypatch):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())
        monkeypatch.setattr(v1_mod, "_resolve_aop_ke_ids", lambda aid: ["KE 1"])

        resp = client.get("/api/v1/reactome-mappings?aop_id=42")
        body = resp.get_json()
        assert body["pagination"]["total"] == 2
        assert {r["ke_id"] for r in body["data"]} == {"KE 1"}

    def test_list_reactome_mappings_aop_invalid(self, v1r_client, monkeypatch):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())

        def _raise(_):
            raise ValueError("nope")

        monkeypatch.setattr(v1_mod, "_resolve_aop_ke_ids", _raise)

        resp = client.get("/api/v1/reactome-mappings?aop_id=99999")
        assert resp.status_code == 400
        assert "AOP ID not found" in resp.get_json()["error"]

    def test_response_shape(self, v1r_client):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())

        resp = client.get("/api/v1/reactome-mappings")
        item = resp.get_json()["data"][0]
        expected = {
            "uuid", "ke_id", "ke_name", "reactome_id", "pathway_name",
            "species", "confidence_level", "pathway_description",
            "reactome_gene_count", "ke_aop_context", "ke_bio_level",
            "provenance",
        }
        assert expected <= set(item.keys()), (
            f"Missing keys: {expected - set(item.keys())}"
        )
        assert {"suggestion_score", "approved_by", "approved_at", "proposed_by"} <= set(
            item["provenance"].keys()
        )

    def test_pagination_preserves_aop_id(self, v1r_client, monkeypatch):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())
        monkeypatch.setattr(
            v1_mod, "_resolve_aop_ke_ids", lambda aid: ["KE 1", "KE 5"]
        )

        resp = client.get(
            "/api/v1/reactome-mappings?aop_id=42&per_page=1&page=1"
        )
        body = resp.get_json()
        nxt = body["pagination"].get("next")
        assert nxt is not None and "aop_id=42" in nxt

    def test_cors_header_present(self, v1r_client):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())

        resp = client.get("/api/v1/reactome-mappings")
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"

    def test_enrichment_fields_present_when_known(self, v1r_client):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())

        resp = client.get("/api/v1/reactome-mappings?reactome_id=R-HSA-100")
        body = resp.get_json()
        assert body["data"]
        item = body["data"][0]
        assert item["pathway_description"] == "p53 sig description"
        assert item["reactome_gene_count"] == 25


# ---------------------------------------------------------------------------
# Single-uuid endpoint tests (Task 2)
# ---------------------------------------------------------------------------

class TestGetReactomeMapping:
    def test_get_reactome_mapping_found(self, v1r_client):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())

        resp = client.get("/api/v1/reactome-mappings/u1")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["uuid"] == "u1"
        assert data["reactome_id"] == "R-HSA-100"
        assert data["pathway_name"] == "p53 signaling"

    def test_get_reactome_mapping_not_found(self, v1r_client):
        client, rm = v1r_client
        _seed_reactome(rm, _default_rows())

        resp = client.get("/api/v1/reactome-mappings/nonexistent")
        assert resp.status_code == 404
        assert "Reactome mapping not found" in resp.get_json()["error"]
