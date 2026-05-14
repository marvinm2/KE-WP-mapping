"""Source-data versioning Phase B — schema-migration tests.

Mirrors the Phase 34 assessment-migration test pattern: each test spins up a
fresh Database() against a tmp_path SQLite file and inspects PRAGMA
table_info to assert presence of the new upstream source-version columns
on mappings / ke_go_mappings / ke_reactome_mappings. Idempotency is
verified by reinitialising the Database() against the same file and
re-checking the column set.
"""
import sqlite3

import pytest

from src.core.models import Database


def _columns(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def _row_count(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


@pytest.fixture
def fresh_db(tmp_path):
    path = tmp_path / "ke_wp_mapping.db"
    Database(str(path))  # init triggers all migrations
    return str(path)


# ---------- Column presence ----------

def test_mappings_gains_wp_release_and_aopwiki_snapshot(fresh_db):
    cols = _columns(fresh_db, "mappings")
    assert "wp_release_date" in cols
    assert "aopwiki_snapshot_date" in cols


def test_ke_go_mappings_gains_go_release_and_aopwiki_snapshot(fresh_db):
    cols = _columns(fresh_db, "ke_go_mappings")
    assert "go_release_date" in cols
    assert "aopwiki_snapshot_date" in cols


def test_ke_reactome_mappings_gains_version_release_and_snapshot(fresh_db):
    cols = _columns(fresh_db, "ke_reactome_mappings")
    assert "reactome_release_version" in cols
    assert "reactome_release_date" in cols
    assert "aopwiki_snapshot_date" in cols


# ---------- Nullability — new rows can omit the columns ----------

@pytest.mark.parametrize(
    "table,insert_sql,values",
    [
        (
            "mappings",
            "INSERT INTO mappings (ke_id, ke_title, wp_id, wp_title, "
            "connection_type, confidence_level, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("KE 1", "Test KE", "WP1", "Test pathway", "causative", "high", "test"),
        ),
        (
            "ke_go_mappings",
            "INSERT INTO ke_go_mappings (ke_id, ke_title, go_id, go_name, "
            "connection_type, confidence_level, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("KE 2", "Test KE 2", "GO:0001234", "test GO term", "causative", "high", "test"),
        ),
        (
            "ke_reactome_mappings",
            "INSERT INTO ke_reactome_mappings (ke_id, ke_title, reactome_id, "
            "pathway_name, confidence_level, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("KE 3", "Test KE 3", "R-HSA-1234", "Test reactome", "high", "test"),
        ),
    ],
)
def test_new_columns_are_nullable(fresh_db, table, insert_sql, values):
    """A fresh row that doesn't supply any of the new columns must still insert."""
    conn = sqlite3.connect(fresh_db)
    try:
        conn.execute(insert_sql, values)
        conn.commit()
        row = conn.execute(
            f"SELECT wp_release_date, aopwiki_snapshot_date FROM {table} LIMIT 1"
        ).fetchone() if table == "mappings" else conn.execute(
            f"SELECT * FROM {table} LIMIT 1"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


# ---------- Idempotency ----------

def test_reinitialising_database_does_not_duplicate_columns(fresh_db):
    cols_first = _columns(fresh_db, "mappings")
    Database(fresh_db)  # second init must be a no-op for our migrations
    cols_second = _columns(fresh_db, "mappings")
    assert cols_first == cols_second


def test_reinitialising_database_preserves_row_count(fresh_db):
    conn = sqlite3.connect(fresh_db)
    try:
        conn.execute(
            "INSERT INTO mappings (ke_id, ke_title, wp_id, wp_title, "
            "connection_type, confidence_level, created_by) "
            "VALUES ('KE 99', 'persist test', 'WP99', 'persist', 'causative', 'low', 'test')"
        )
        conn.commit()
    finally:
        conn.close()
    before = _row_count(fresh_db, "mappings")
    Database(fresh_db)
    after = _row_count(fresh_db, "mappings")
    assert before == after == 1


# ---------- Round-trip — values written into the new columns are readable ----------

def test_round_trip_wp_release_date(fresh_db):
    conn = sqlite3.connect(fresh_db)
    try:
        conn.execute(
            "INSERT INTO mappings (ke_id, ke_title, wp_id, wp_title, "
            "connection_type, confidence_level, created_by, "
            "wp_release_date, aopwiki_snapshot_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("KE 4", "rt", "WP4", "rt", "causative", "high", "test",
             "2026-05-10", "2026-05-06"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT wp_release_date, aopwiki_snapshot_date FROM mappings "
            "WHERE ke_id = 'KE 4'"
        ).fetchone()
        assert row == ("2026-05-10", "2026-05-06")
    finally:
        conn.close()


def test_round_trip_reactome_version_and_release(fresh_db):
    conn = sqlite3.connect(fresh_db)
    try:
        conn.execute(
            "INSERT INTO ke_reactome_mappings (ke_id, ke_title, reactome_id, "
            "pathway_name, confidence_level, created_by, "
            "reactome_release_version, reactome_release_date, "
            "aopwiki_snapshot_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("KE 5", "rt", "R-HSA-5", "rt", "high", "test",
             "96", "2026-03-25", "2026-05-06"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT reactome_release_version, reactome_release_date, "
            "aopwiki_snapshot_date FROM ke_reactome_mappings "
            "WHERE ke_id = 'KE 5'"
        ).fetchone()
        assert row == ("96", "2026-03-25", "2026-05-06")
    finally:
        conn.close()
