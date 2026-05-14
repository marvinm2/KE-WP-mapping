"""Tests for scripts/backfill_source_versions.py (Phase D).

Each test spins up a fresh `Database(tmp_path)` (which runs the Phase B
migrations so the version columns exist), inserts a couple of legacy
rows with NULL version columns via raw sqlite3, then invokes the
backfill script's `main()` and asserts row counts + persisted values.
"""
import json
import sqlite3
from pathlib import Path

import pytest

from scripts import backfill_source_versions as bf
from src.core.models import Database

_OK_MANIFEST = {
    "captured_at": "2026-05-15T00:00:00Z",
    "sources": {
        "wikipathways": {"status": "ok", "release_date": "2026-05-10"},
        "gene_ontology": {"status": "ok", "release_date": "2026-01-23"},
        "reactome": {
            "status": "ok",
            "release_version": "96",
            "release_date": "2026-03-25",
        },
        "aopwiki": {"status": "ok", "snapshot_date": "2026-05-06"},
    },
}


# ---------- fixtures ----------

@pytest.fixture
def manifest_path(tmp_path: Path, request) -> Path:
    """Write the requested manifest to a tmp file. Defaults to _OK_MANIFEST."""
    manifest = getattr(request, "param", _OK_MANIFEST)
    p = tmp_path / "source_versions.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Fresh DB with Phase B migrations applied."""
    return Database(str(tmp_path / "k.db"))


def _seed_legacy_rows(db_path: str) -> None:
    """Insert one row per mapping table with NULL version columns."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO mappings (ke_id, ke_title, wp_id, wp_title, "
            "connection_type, confidence_level, created_by) "
            "VALUES ('KE 1', 't', 'WP1', 't', 'causative', 'high', 'u')"
        )
        conn.execute(
            "INSERT INTO ke_go_mappings (ke_id, ke_title, go_id, go_name, "
            "connection_type, confidence_level, created_by) "
            "VALUES ('KE 2', 't', 'GO:0000001', 't', 'causative', 'high', 'u')"
        )
        conn.execute(
            "INSERT INTO ke_reactome_mappings (ke_id, ke_title, reactome_id, "
            "pathway_name, confidence_level, created_by) "
            "VALUES ('KE 3', 't', 'R-HSA-1', 't', 'high', 'u')"
        )
        conn.commit()
    finally:
        conn.close()


def _read_version_cols(db_path: str) -> dict:
    """Pull the version columns from each mapping table's first row."""
    conn = sqlite3.connect(db_path)
    try:
        wp = conn.execute(
            "SELECT wp_release_date, aopwiki_snapshot_date FROM mappings LIMIT 1"
        ).fetchone()
        go = conn.execute(
            "SELECT go_release_date, aopwiki_snapshot_date FROM ke_go_mappings LIMIT 1"
        ).fetchone()
        rx = conn.execute(
            "SELECT reactome_release_version, reactome_release_date, "
            "aopwiki_snapshot_date FROM ke_reactome_mappings LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    return {"mappings": wp, "ke_go_mappings": go, "ke_reactome_mappings": rx}


# ---------- happy path ----------

def test_backfill_fills_all_three_tables(db: Database, manifest_path: Path) -> None:
    _seed_legacy_rows(db.db_path)
    rc = bf.main(["--manifest", str(manifest_path), "--db", db.db_path])
    assert rc == 0
    vals = _read_version_cols(db.db_path)
    assert vals["mappings"] == ("2026-05-10", "2026-05-06")
    assert vals["ke_go_mappings"] == ("2026-01-23", "2026-05-06")
    assert vals["ke_reactome_mappings"] == ("96", "2026-03-25", "2026-05-06")


def test_dry_run_does_not_write(db: Database, manifest_path: Path) -> None:
    _seed_legacy_rows(db.db_path)
    rc = bf.main(["--manifest", str(manifest_path), "--db", db.db_path, "--dry-run"])
    assert rc == 0
    vals = _read_version_cols(db.db_path)
    # All columns still NULL after dry-run.
    assert vals["mappings"] == (None, None)
    assert vals["ke_go_mappings"] == (None, None)
    assert vals["ke_reactome_mappings"] == (None, None, None)


def test_backfill_is_idempotent(db: Database, manifest_path: Path) -> None:
    _seed_legacy_rows(db.db_path)
    # First pass — updates 30 rows
    rc1 = bf.main(["--manifest", str(manifest_path), "--db", db.db_path])
    assert rc1 == 0
    # Second pass — 0 changes
    rc2 = bf.main(["--manifest", str(manifest_path), "--db", db.db_path])
    assert rc2 == 0
    # Values unchanged.
    vals = _read_version_cols(db.db_path)
    assert vals["mappings"] == ("2026-05-10", "2026-05-06")


def test_backfill_preserves_already_stamped_rows(db: Database, manifest_path: Path) -> None:
    """Rows that already have non-NULL version columns must not be overwritten."""
    conn = sqlite3.connect(db.db_path)
    try:
        # Row already has wp_release_date populated.
        conn.execute(
            "INSERT INTO mappings (ke_id, ke_title, wp_id, wp_title, "
            "connection_type, confidence_level, created_by, "
            "wp_release_date) "
            "VALUES ('KE 99', 't', 'WP99', 't', 'causative', 'high', 'u', "
            "'2025-12-15')"
        )
        # Another row fully populated.
        conn.execute(
            "INSERT INTO mappings (ke_id, ke_title, wp_id, wp_title, "
            "connection_type, confidence_level, created_by, "
            "wp_release_date, aopwiki_snapshot_date) "
            "VALUES ('KE 100', 't', 'WP100', 't', 'causative', 'high', 'u', "
            "'2025-12-15', '2025-12-20')"
        )
        conn.commit()
    finally:
        conn.close()

    bf.main(["--manifest", str(manifest_path), "--db", db.db_path])

    conn = sqlite3.connect(db.db_path)
    try:
        rows = conn.execute(
            "SELECT ke_id, wp_release_date, aopwiki_snapshot_date "
            "FROM mappings ORDER BY ke_id"
        ).fetchall()
    finally:
        conn.close()
    # KE 99 keeps its existing wp_release_date but gains the AOP-Wiki date
    # (which was previously NULL).
    assert ("KE 99", "2025-12-15", "2026-05-06") in rows
    # KE 100 untouched on both columns.
    assert ("KE 100", "2025-12-15", "2025-12-20") in rows


# ---------- manifest variants ----------

@pytest.mark.parametrize(
    "manifest_path",
    [
        {  # WP unknown — should backfill only the AOP-Wiki anchor on `mappings`.
            "sources": {
                "wikipathways": {"status": "unknown", "reason": "down"},
                "gene_ontology": {"status": "ok", "release_date": "2026-01-23"},
                "reactome": {"status": "ok", "release_version": "96"},
                "aopwiki": {"status": "ok", "snapshot_date": "2026-05-06"},
            }
        },
    ],
    indirect=True,
)
def test_unknown_source_still_backfills_aopwiki_anchor(db: Database, manifest_path: Path) -> None:
    _seed_legacy_rows(db.db_path)
    rc = bf.main(["--manifest", str(manifest_path), "--db", db.db_path])
    assert rc == 0
    vals = _read_version_cols(db.db_path)
    # WP column stays NULL because the manifest entry was 'unknown', but the
    # AOP-Wiki anchor is filled in.
    assert vals["mappings"] == (None, "2026-05-06")


@pytest.mark.parametrize(
    "manifest_path",
    [
        {  # All sources unknown — script reports failure (exit 2).
            "sources": {
                "wikipathways": {"status": "unknown"},
                "gene_ontology": {"status": "unknown"},
                "reactome": {"status": "unknown"},
                "aopwiki": {"status": "unknown"},
            }
        },
    ],
    indirect=True,
)
def test_all_unknown_manifest_returns_2(db: Database, manifest_path: Path) -> None:
    _seed_legacy_rows(db.db_path)
    rc = bf.main(["--manifest", str(manifest_path), "--db", db.db_path])
    assert rc == 2


def test_missing_manifest_returns_1(db: Database, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.json"
    rc = bf.main(["--manifest", str(missing), "--db", db.db_path])
    assert rc == 1


def test_missing_db_returns_1(manifest_path: Path, tmp_path: Path) -> None:
    missing_db = tmp_path / "does-not-exist.db"
    rc = bf.main(["--manifest", str(manifest_path), "--db", str(missing_db)])
    assert rc == 1
