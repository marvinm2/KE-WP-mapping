"""Phase 34 (ASMT-01/02/03) — schema-migration idempotency and column-presence tests.

Mirrors Phase 19's KE-GO dimension-scores migration tests in structure. Each test
spins up a fresh Database() against a tmp_path SQLite file and inspects PRAGMA
table_info to assert the four new `proposed_*` columns plus (on mapping tables)
`assessment_version TEXT NOT NULL DEFAULT 'v1'`.
"""
import sqlite3

import pytest

from src.core.models import Database

PROPOSED_COLS = (
    "proposed_relationship",
    "proposed_basis",
    "proposed_specificity",
    "proposed_coverage",
)


def _columns(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def test_migrations_are_idempotent(tmp_path):
    """init_db is called on every container restart — must tolerate re-runs."""
    db_path = str(tmp_path / "test.db")
    Database(db_path)   # First init: ALTER TABLE fires for new columns
    Database(db_path)   # Second init on the same file: PRAGMA guard, no-ops
    # If we got here without raising, the guard works.


def test_proposals_columns(tmp_path):
    """proposals table gains four proposed_* columns; no assessment_version."""
    db_path = str(tmp_path / "test.db")
    Database(db_path)
    cols = _columns(db_path, "proposals")
    for col in PROPOSED_COLS:
        assert col in cols, f"proposals missing {col}"
    assert "assessment_version" not in cols, (
        "proposals must NOT carry assessment_version (CONTEXT.md decision — "
        "version is decided at approval)"
    )


def test_mappings_columns_and_legacy_v1(tmp_path):
    """mappings table gains four proposed_* columns + assessment_version; legacy rows default to v1."""
    db_path = str(tmp_path / "test.db")
    Database(db_path)
    cols = _columns(db_path, "mappings")
    for col in (*PROPOSED_COLS, "assessment_version"):
        assert col in cols, f"mappings missing {col}"
    # Prove the column DEFAULT backfills legacy rows.
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            "INSERT INTO mappings (ke_id, ke_title, wp_id, wp_title) "
            "VALUES ('KE:1', 'Test KE', 'WP1', 'Test Pathway')"
        )
        conn.commit()
        row = conn.execute(
            "SELECT assessment_version FROM mappings WHERE ke_id='KE:1'"
        ).fetchone()
        assert row["assessment_version"] == "v1"
    finally:
        conn.close()


def test_reactome_proposals_columns(tmp_path):
    """ke_reactome_proposals table gains four proposed_* columns; no assessment_version."""
    db_path = str(tmp_path / "test.db")
    Database(db_path)
    cols = _columns(db_path, "ke_reactome_proposals")
    for col in PROPOSED_COLS:
        assert col in cols, f"ke_reactome_proposals missing {col}"
    assert "assessment_version" not in cols, (
        "ke_reactome_proposals must NOT carry assessment_version (CONTEXT.md decision — "
        "version is decided at approval)"
    )


def test_reactome_mappings_columns_and_legacy_v1(tmp_path):
    """ke_reactome_mappings table gains four proposed_* + assessment_version; legacy rows default to v1."""
    db_path = str(tmp_path / "test.db")
    Database(db_path)
    cols = _columns(db_path, "ke_reactome_mappings")
    for col in (*PROPOSED_COLS, "assessment_version"):
        assert col in cols, f"ke_reactome_mappings missing {col}"
    # Prove the column DEFAULT backfills legacy rows.
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            "INSERT INTO ke_reactome_mappings "
            "(ke_id, ke_title, reactome_id, pathway_name) "
            "VALUES ('KE:1', 'Test KE', 'R-HSA-123', 'Test Pathway')"
        )
        conn.commit()
        row = conn.execute(
            "SELECT assessment_version FROM ke_reactome_mappings "
            "WHERE ke_id='KE:1'"
        ).fetchone()
        assert row["assessment_version"] == "v1"
    finally:
        conn.close()
