"""Tests for ReactomeMappingModel paginated read methods (Phase 26-02, D-09).

Covers get_reactome_mappings_paginated and get_reactome_mapping_by_uuid added
to ReactomeMappingModel as the data-layer surface for the Phase 26 public API
routes /api/v1/reactome-mappings and /api/v1/reactome-mappings/<uuid>.

Behaviour anchors (mirror plan 26-02 <behavior> block):
  - no filters returns all approved rows, page 1, per_page 50, created_at DESC
  - ke_id, reactome_id, confidence_level (case-insensitive) each filter rows
  - ke_ids=[] short-circuits to ([], 0) without SQL
  - ke_ids=[ids...] applies parametrised IN clause
  - ke_id + ke_ids combine via AND (narrows further)
  - returned dicts contain every column required by _serialize_reactome_mapping
  - get_reactome_mapping_by_uuid returns a dict on hit, None on miss
"""
import os
import tempfile

import pytest

from src.core.models import Database, ReactomeMappingModel


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database with all tables initialized."""
    fd, path = tempfile.mkstemp(suffix=".db")
    db = Database(path)
    db.init_db()
    yield db
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def reactome_mapping_model(temp_db):
    return ReactomeMappingModel(temp_db)


@pytest.fixture
def seeded_reactome_model(reactome_mapping_model):
    """Insert 3 approved mappings spanning 2 KEs and 2 distinct pathways.

    Layout (anchors all the filter assertions below):
      u1 -> KE 1, R-HSA-100, High
      u2 -> KE 1, R-HSA-200, Medium
      u3 -> KE 5, R-HSA-100, Low
    """
    rows = [
        {
            "uuid": "u1",
            "ke_id": "KE 1",
            "ke_title": "T1",
            "reactome_id": "R-HSA-100",
            "pathway_name": "P1",
            "species": "Homo sapiens",
            "confidence_level": "High",
            "approved_by_curator": "github:alice",
            "approved_at_curator": "2026-01-01T00:00:00",
            "suggestion_score": 0.9,
            "proposed_by": "github:alice",
        },
        {
            "uuid": "u2",
            "ke_id": "KE 1",
            "ke_title": "T1",
            "reactome_id": "R-HSA-200",
            "pathway_name": "P2",
            "species": "Homo sapiens",
            "confidence_level": "Medium",
            "approved_by_curator": "github:alice",
            "approved_at_curator": "2026-01-02T00:00:00",
            "suggestion_score": 0.7,
            "proposed_by": "github:alice",
        },
        {
            "uuid": "u3",
            "ke_id": "KE 5",
            "ke_title": "T5",
            "reactome_id": "R-HSA-100",
            "pathway_name": "P1",
            "species": "Homo sapiens",
            "confidence_level": "Low",
            "approved_by_curator": "github:bob",
            "approved_at_curator": "2026-01-03T00:00:00",
            "suggestion_score": 0.5,
            "proposed_by": "github:bob",
        },
    ]
    conn = reactome_mapping_model.db.get_connection()
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
    return reactome_mapping_model


class TestGetReactomeMappingsPaginated:
    def test_paginated_no_filters(self, seeded_reactome_model):
        rows, total = seeded_reactome_model.get_reactome_mappings_paginated()
        assert total == 3
        assert len(rows) == 3

    def test_paginated_filter_by_ke_id(self, seeded_reactome_model):
        rows, total = seeded_reactome_model.get_reactome_mappings_paginated(ke_id="KE 1")
        assert total == 2
        assert {r["ke_id"] for r in rows} == {"KE 1"}

    def test_paginated_filter_by_reactome_id(self, seeded_reactome_model):
        rows, total = seeded_reactome_model.get_reactome_mappings_paginated(
            reactome_id="R-HSA-100"
        )
        assert total == 2
        assert {r["reactome_id"] for r in rows} == {"R-HSA-100"}

    def test_paginated_confidence_case_insensitive(self, seeded_reactome_model):
        # stored "High" must match a lowercase query
        rows, total = seeded_reactome_model.get_reactome_mappings_paginated(
            confidence_level="high"
        )
        assert total == 1
        assert rows[0]["confidence_level"] == "High"

    def test_paginated_ke_ids_empty_short_circuits(self, seeded_reactome_model):
        # AOP resolved but no KEs found => empty result, no SQL.
        rows, total = seeded_reactome_model.get_reactome_mappings_paginated(ke_ids=[])
        assert (rows, total) == ([], 0)

    def test_paginated_ke_ids_in_clause(self, seeded_reactome_model):
        rows, total = seeded_reactome_model.get_reactome_mappings_paginated(
            ke_ids=["KE 1", "KE 5"]
        )
        assert total == 3
        assert {r["ke_id"] for r in rows} == {"KE 1", "KE 5"}

    def test_paginated_ke_id_and_ke_ids_combine(self, seeded_reactome_model):
        # Both filters AND together: ke_id="KE 1" narrows ke_ids=["KE 1","KE 5"] to KE 1.
        rows, total = seeded_reactome_model.get_reactome_mappings_paginated(
            ke_id="KE 1", ke_ids=["KE 1", "KE 5"]
        )
        assert total == 2
        assert {r["ke_id"] for r in rows} == {"KE 1"}

    def test_paginated_columns_complete(self, seeded_reactome_model):
        rows, _ = seeded_reactome_model.get_reactome_mappings_paginated()
        expected = {
            "uuid",
            "ke_id",
            "ke_title",
            "reactome_id",
            "pathway_name",
            "species",
            "confidence_level",
            "approved_by_curator",
            "approved_at_curator",
            "suggestion_score",
            "proposed_by",
        }
        assert expected <= set(rows[0].keys())


class TestGetReactomeMappingByUuid:
    def test_get_by_uuid_found(self, seeded_reactome_model):
        row = seeded_reactome_model.get_reactome_mapping_by_uuid("u1")
        assert row is not None
        assert row["uuid"] == "u1"
        assert row["ke_id"] == "KE 1"
        assert row["reactome_id"] == "R-HSA-100"
        assert row["pathway_name"] == "P1"
        assert row["confidence_level"] == "High"

    def test_get_by_uuid_not_found(self, seeded_reactome_model):
        assert seeded_reactome_model.get_reactome_mapping_by_uuid("nonexistent") is None
