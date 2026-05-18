"""#158 follow-up — legacy datetime normalisation.

SQLite's CURRENT_TIMESTAMP defaults produce "YYYY-MM-DD HH:MM:SS" (space, no
'T'), which is valid SQL but rejected by rdflib when emitted as an
XSD.dateTime literal during Turtle export. This file pins:

1. The startup migration normalises legacy rows on mappings /
   ke_go_mappings / ke_reactome_mappings across created_at, updated_at,
   approved_at_curator. Idempotent on a second init.
2. The defensive coercion in rdf_exporter._to_iso8601_datetime hardens
   any stragglers — so Turtle output always carries a well-formed
   xsd:dateTime literal, no rdflib WARNING.
"""
import logging
import sqlite3
import uuid

import pytest
from rdflib import Graph
from rdflib.namespace import XSD

from src.core.models import Database
from src.exporters.rdf_exporter import (
    _to_iso8601_datetime,
    generate_ke_go_turtle,
    generate_ke_reactome_turtle,
    generate_ke_wp_turtle,
)


# ---------- _to_iso8601_datetime helper ----------

@pytest.mark.parametrize(
    "value,expected",
    [
        ("2025-08-13 05:42:58", "2025-08-13T05:42:58"),
        ("2025-08-13 05:42:58.123", "2025-08-13T05:42:58.123"),
        ("2025-08-13T05:42:58", "2025-08-13T05:42:58"),   # already ISO
        ("2025-08-13T05:42:58+00:00", "2025-08-13T05:42:58+00:00"),
        (None, None),
        ("", ""),
        ("short", "short"),
        (12345, 12345),                                    # non-string passthrough
    ],
)
def test_to_iso8601_datetime(value, expected):
    assert _to_iso8601_datetime(value) == expected


# ---------- Migration: legacy rows get normalised ----------

def _raw_insert_legacy_row(db_path):
    """Insert one row per mapping table with space-separated timestamps.

    We bypass the application's insert paths so the legacy SQLite default
    shape is preserved verbatim (mirrors what production has on disk).
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO mappings (uuid, ke_id, ke_title, wp_id, wp_title,
                connection_type, confidence_level, created_by, created_at,
                updated_at, approved_at_curator, approved_by_curator)
            VALUES (?, 'KE 1', 'Test KE', 'WP1', 'Test pathway', 'causative',
                'high', 'github:test', '2025-08-13 05:42:58', '2025-08-13 05:42:58',
                '2025-08-13 05:42:58', 'curator1')
            """,
            (str(uuid.uuid4()),),
        )
        conn.execute(
            """
            INSERT INTO ke_go_mappings (uuid, ke_id, ke_title, go_id, go_name,
                connection_type, confidence_level, created_by, created_at,
                updated_at, approved_at_curator, approved_by_curator)
            VALUES (?, 'KE 2', 'Test KE 2', 'GO:0001234', 'test go term',
                'causative', 'high', 'github:test', '2025-08-13 05:42:58',
                '2025-08-13 05:42:58', '2025-08-13 05:42:58', 'curator1')
            """,
            (str(uuid.uuid4()),),
        )
        conn.execute(
            """
            INSERT INTO ke_reactome_mappings (uuid, ke_id, ke_title,
                reactome_id, pathway_name, species, confidence_level,
                created_by, created_at, updated_at, approved_at_curator,
                approved_by_curator)
            VALUES (?, 'KE 3', 'Test KE 3', 'R-HSA-1', 'test reactome pathway',
                'Homo sapiens', 'high', 'github:test', '2025-08-13 05:42:58',
                '2025-08-13 05:42:58', '2025-08-13 05:42:58', 'curator1')
            """,
            (str(uuid.uuid4()),),
        )
        conn.commit()
    finally:
        conn.close()


def _select_datetime_cols(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            f"SELECT created_at, updated_at, approved_at_curator FROM {table}"
        ).fetchone()
        return row
    finally:
        conn.close()


def test_backfill_normalises_legacy_rows_on_init(tmp_path):
    path = str(tmp_path / "ke_wp_mapping.db")

    # First init creates the schema. Insert legacy-shape rows directly,
    # then re-init to trigger the backfill migration.
    Database(path)
    _raw_insert_legacy_row(path)

    Database(path)  # re-init runs migrations against existing data

    for table in ("mappings", "ke_go_mappings", "ke_reactome_mappings"):
        created_at, updated_at, approved_at = _select_datetime_cols(path, table)
        assert created_at == "2025-08-13T05:42:58", f"{table}.created_at"
        assert updated_at == "2025-08-13T05:42:58", f"{table}.updated_at"
        assert approved_at == "2025-08-13T05:42:58", f"{table}.approved_at_curator"


def test_backfill_leaves_iso_rows_untouched(tmp_path):
    path = str(tmp_path / "ke_wp_mapping.db")
    Database(path)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            INSERT INTO mappings (uuid, ke_id, ke_title, wp_id, wp_title,
                connection_type, confidence_level, created_by, created_at,
                approved_at_curator, approved_by_curator)
            VALUES (?, 'KE A', 'KE A', 'WP-A', 'A', 'causative', 'high',
                'github:test', '2025-08-13T05:42:58', '2025-08-13T05:42:58',
                'curator1')
            """,
            (str(uuid.uuid4()),),
        )
        conn.commit()
    finally:
        conn.close()

    Database(path)  # re-init triggers backfill

    conn = sqlite3.connect(path)
    try:
        created_at, approved_at = conn.execute(
            "SELECT created_at, approved_at_curator FROM mappings WHERE ke_id='KE A'"
        ).fetchone()
    finally:
        conn.close()
    assert created_at == "2025-08-13T05:42:58"
    assert approved_at == "2025-08-13T05:42:58"


def test_backfill_is_idempotent(tmp_path):
    """A second init after the first one has normalised must update 0 rows."""
    path = str(tmp_path / "ke_wp_mapping.db")
    Database(path)
    _raw_insert_legacy_row(path)
    Database(path)   # first backfill normalises

    # Snapshot post-first-backfill, run again, assert nothing changes.
    before = {
        t: _select_datetime_cols(path, t)
        for t in ("mappings", "ke_go_mappings", "ke_reactome_mappings")
    }
    Database(path)
    after = {
        t: _select_datetime_cols(path, t)
        for t in ("mappings", "ke_go_mappings", "ke_reactome_mappings")
    }
    assert before == after


# ---------- RDF exporter: no warning + valid xsd:dateTime ----------

def _mappings_row(table_kind, approved_at):
    base = {
        "uuid": str(uuid.uuid4()),
        "ke_id": "KE 1",
        "ke_title": "Test KE",
        "confidence_level": "high",
        "approved_by_curator": "curator1",
        "approved_at_curator": approved_at,
        "suggestion_score": 0.9,
    }
    if table_kind == "wp":
        base.update({"wp_id": "WP1", "wp_title": "Test pathway"})
    elif table_kind == "go":
        base.update({"go_id": "GO:0001234", "go_name": "Test GO term"})
    elif table_kind == "reactome":
        base.update({"reactome_id": "R-HSA-1", "pathway_name": "Test reactome pathway"})
    return base


@pytest.mark.parametrize(
    "kind,generator",
    [
        ("wp", generate_ke_wp_turtle),
        ("go", generate_ke_go_turtle),
        ("reactome", generate_ke_reactome_turtle),
    ],
)
def test_exporter_normalises_space_datetime_without_warning(kind, generator, caplog):
    rows = [_mappings_row(kind, "2025-08-13 05:42:58")]
    with caplog.at_level(logging.WARNING, logger="rdflib"):
        ttl = generator(rows)

    # No "ISO 8601 time designator 'T' missing" warning should be emitted.
    assert not any(
        "8601" in rec.getMessage() or "designator" in rec.getMessage()
        for rec in caplog.records
    ), [r.getMessage() for r in caplog.records]

    # Turtle must round-trip and contain a literal with T-separated value
    # typed as xsd:dateTime.
    g = Graph()
    g.parse(data=ttl, format="turtle")
    found_iso = any(
        getattr(o, "datatype", None) == XSD.dateTime and "T" in str(o)
        for _, _, o in g
    )
    assert found_iso, ttl
