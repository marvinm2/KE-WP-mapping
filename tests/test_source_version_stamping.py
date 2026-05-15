"""Source-data versioning Phase C — approval-time stamping tests.

Two layers:

1. Container — `source_versions` property handles missing / malformed manifests
   gracefully, and `source_version_fields_for(resource)` returns the right
   per-resource kwargs dict (skipping `unknown` upstreams so columns stay
   NULL rather than erroring).

2. Model — `create_mapping` / `create_approved_mapping` / `update_mapping`
   accept the new version kwargs and persist them in the new schema columns
   added by Phase B.

The full admin-route approval flow is exercised by the existing integration
tests in test_assessment_roundtrip_*.py and test_reactome_admin.py, which
already cover the proposal-to-mapping pipeline; we add a minimal smoke test
here that goes through the container helper and writes directly via the
model to keep this test module focused on the new wiring.
"""
import json
import sqlite3
from pathlib import Path

import pytest
import src.services.container as cont_mod

from src.core.models import (
    Database,
    GoMappingModel,
    MappingModel,
    ReactomeMappingModel,
    ReactomeProposalModel,
)


# ---------- Container `source_versions` property ----------

def _make_container(tmp_path: Path, manifest: dict | None):
    """Mint a bare cont_mod.ServiceContainer with the manifest path overridden."""
    # ServiceContainer accessed via cont_mod to avoid mixed import styles

    class _StubConfig:
        DATABASE_PATH = str(tmp_path / "test.db")

    c = cont_mod.ServiceContainer(_StubConfig())

    # Redirect the container's manifest lookup at the tmp_path directory.
    # cont_mod.ServiceContainer.source_versions hard-codes the path under PROJECT_ROOT,
    # so we monkeypatch the relevant module-level constant in-place.

    if manifest is None:
        # Caller wants the "manifest missing" case — point PROJECT_ROOT at an
        # empty directory so the existence check returns False.
        missing_root = tmp_path / "empty"
        missing_root.mkdir()
        c._project_root_override = missing_root
        original_project_root = cont_mod.PROJECT_ROOT
        cont_mod.PROJECT_ROOT = str(missing_root)
        return c, lambda: setattr(cont_mod, "PROJECT_ROOT", original_project_root)

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "source_versions.json").write_text(json.dumps(manifest), encoding="utf-8")
    original_project_root = cont_mod.PROJECT_ROOT
    cont_mod.PROJECT_ROOT = str(tmp_path)
    return c, lambda: setattr(cont_mod, "PROJECT_ROOT", original_project_root)


_ALL_OK_MANIFEST = {
    "captured_at": "2026-05-14T21:00:00Z",
    "sources": {
        "wikipathways": {
            "status": "ok", "release_date": "2026-05-10",
        },
        "gene_ontology": {
            "status": "ok", "release_date": "2026-01-23",
        },
        "reactome": {
            "status": "ok",
            "release_version": "96", "release_date": "2026-03-25",
        },
        "aopwiki": {
            "status": "ok", "snapshot_date": "2026-05-06",
        },
    },
}


def test_source_versions_returns_empty_dict_when_file_missing(tmp_path):
    container, undo = _make_container(tmp_path, manifest=None)
    try:
        assert container.source_versions == {}
        # And the resource-resolver returns an empty dict — caller can `**unpack` it.
        for resource in ("wp", "go", "reactome"):
            assert container.source_version_fields_for(resource) == {}
    finally:
        undo()


def test_source_versions_returns_empty_dict_when_file_unreadable(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "source_versions.json").write_text("not valid json{", encoding="utf-8")

    class _StubConfig:
        DATABASE_PATH = str(tmp_path / "x.db")

    container = cont_mod.ServiceContainer(_StubConfig())
    original = cont_mod.PROJECT_ROOT
    cont_mod.PROJECT_ROOT = str(tmp_path)
    try:
        assert container.source_versions == {}
    finally:
        cont_mod.PROJECT_ROOT = original


def test_source_version_fields_for_wp(tmp_path):
    container, undo = _make_container(tmp_path, manifest=_ALL_OK_MANIFEST)
    try:
        out = container.source_version_fields_for("wp")
        assert out == {
            "wp_release_date": "2026-05-10",
            "aopwiki_snapshot_date": "2026-05-06",
        }
    finally:
        undo()


def test_source_version_fields_for_go(tmp_path):
    container, undo = _make_container(tmp_path, manifest=_ALL_OK_MANIFEST)
    try:
        out = container.source_version_fields_for("go")
        assert out == {
            "go_release_date": "2026-01-23",
            "aopwiki_snapshot_date": "2026-05-06",
        }
    finally:
        undo()


def test_source_version_fields_for_reactome(tmp_path):
    container, undo = _make_container(tmp_path, manifest=_ALL_OK_MANIFEST)
    try:
        out = container.source_version_fields_for("reactome")
        assert out == {
            "reactome_release_version": "96",
            "reactome_release_date": "2026-03-25",
            "aopwiki_snapshot_date": "2026-05-06",
        }
    finally:
        undo()


def test_source_version_fields_skips_unknown_sources(tmp_path):
    """A source flagged 'unknown' in the manifest is omitted from the result dict."""
    manifest = {
        "captured_at": "now",
        "sources": {
            "wikipathways": {"status": "unknown", "reason": "endpoint down"},
            "gene_ontology": {"status": "ok", "release_date": "2026-01-23"},
            "reactome": {"status": "ok", "release_version": "96"},
            "aopwiki": {"status": "ok", "snapshot_date": "2026-05-06"},
        },
    }
    container, undo = _make_container(tmp_path, manifest=manifest)
    try:
        # WP is unknown so only the AOP-Wiki anchor is stamped for WP approvals.
        wp = container.source_version_fields_for("wp")
        assert wp == {"aopwiki_snapshot_date": "2026-05-06"}
        # Reactome OK but without release_date — version still surfaces.
        rx = container.source_version_fields_for("reactome")
        assert rx == {
            "reactome_release_version": "96",
            "aopwiki_snapshot_date": "2026-05-06",
        }
    finally:
        undo()


def test_source_version_fields_unknown_resource_raises(tmp_path):
    container, undo = _make_container(tmp_path, manifest=_ALL_OK_MANIFEST)
    try:
        with pytest.raises(ValueError, match="Unknown resource"):
            container.source_version_fields_for("orcid")
    finally:
        undo()


# ---------- Model — kwargs persist into the new columns ----------

@pytest.fixture
def db(tmp_path):
    return Database(str(tmp_path / "k.db"))


def test_wp_create_mapping_persists_version_columns(db):
    mm = MappingModel(db)
    mid = mm.create_mapping(
        ke_id="KE 100", ke_title="t", wp_id="WP100", wp_title="t",
        created_by="u",
        wp_release_date="2026-05-10",
        aopwiki_snapshot_date="2026-05-06",
    )
    assert mid is not None
    conn = sqlite3.connect(db.db_path)
    row = conn.execute(
        "SELECT wp_release_date, aopwiki_snapshot_date FROM mappings WHERE id = ?",
        (mid,),
    ).fetchone()
    conn.close()
    assert row == ("2026-05-10", "2026-05-06")


def test_wp_update_mapping_persists_version_columns(db):
    mm = MappingModel(db)
    mid = mm.create_mapping(
        ke_id="KE 101", ke_title="t", wp_id="WP101", wp_title="t", created_by="u",
    )
    assert mid is not None
    ok = mm.update_mapping(
        mapping_id=mid,
        approved_by_curator="admin",
        approved_at_curator="2026-05-14T21:00:00",
        wp_release_date="2026-05-10",
        aopwiki_snapshot_date="2026-05-06",
    )
    assert ok is True
    conn = sqlite3.connect(db.db_path)
    row = conn.execute(
        "SELECT wp_release_date, aopwiki_snapshot_date FROM mappings WHERE id = ?",
        (mid,),
    ).fetchone()
    conn.close()
    assert row == ("2026-05-10", "2026-05-06")


def test_go_create_mapping_persists_version_columns(db):
    gm = GoMappingModel(db)
    mid = gm.create_mapping(
        ke_id="KE 102", ke_title="t", go_id="GO:0000001", go_name="t",
        created_by="u",
        go_release_date="2026-01-23",
        aopwiki_snapshot_date="2026-05-06",
    )
    assert mid is not None
    conn = sqlite3.connect(db.db_path)
    row = conn.execute(
        "SELECT go_release_date, aopwiki_snapshot_date FROM ke_go_mappings "
        "WHERE id = ?",
        (mid,),
    ).fetchone()
    conn.close()
    assert row == ("2026-01-23", "2026-05-06")


def test_reactome_create_approved_mapping_persists_version_columns(db):
    rm = ReactomeMappingModel(db)
    rpm = ReactomeProposalModel(db)
    # Create a pending new-pair proposal so create_approved_mapping has
    # carry-fields to read (it loads ke_id/title/reactome_id/etc. from the
    # proposal row internally — Phase 25 H-1 single-INSERT carry path).
    proposal_id = rpm.create_new_pair_reactome_proposal(
        ke_id="KE 200", ke_title="t",
        reactome_id="R-HSA-200", pathway_name="t",
        confidence_level="high",
        provider_username="github:u",
    )
    assert proposal_id is not None and proposal_id != "duplicate_pending"

    mid = rm.create_approved_mapping(
        proposal_id=proposal_id,
        approved_by_curator="admin",
        approved_at_curator="2026-05-14T21:00:00",
        reactome_release_version="96",
        reactome_release_date="2026-03-25",
        aopwiki_snapshot_date="2026-05-06",
    )
    assert mid is not None
    conn = sqlite3.connect(db.db_path)
    row = conn.execute(
        "SELECT reactome_release_version, reactome_release_date, "
        "aopwiki_snapshot_date FROM ke_reactome_mappings WHERE id = ?",
        (mid,),
    ).fetchone()
    conn.close()
    assert row == ("96", "2026-03-25", "2026-05-06")


def test_reactome_create_mapping_persists_version_columns(db):
    """The non-approval `create_mapping` path on Reactome also accepts the kwargs."""
    rm = ReactomeMappingModel(db)
    mid = rm.create_mapping(
        ke_id="KE 201", ke_title="t",
        reactome_id="R-HSA-201", pathway_name="t",
        created_by="u",
        reactome_release_version="96",
        reactome_release_date="2026-03-25",
        aopwiki_snapshot_date="2026-05-06",
    )
    assert mid is not None
    conn = sqlite3.connect(db.db_path)
    row = conn.execute(
        "SELECT reactome_release_version, reactome_release_date, "
        "aopwiki_snapshot_date FROM ke_reactome_mappings WHERE id = ?",
        (mid,),
    ).fetchone()
    conn.close()
    assert row == ("96", "2026-03-25", "2026-05-06")


def test_omitting_version_kwargs_leaves_columns_null(db):
    """Backwards compatibility — existing callers that don't pass the new
    kwargs continue to work, with NULL in the new columns."""
    mm = MappingModel(db)
    mid = mm.create_mapping(
        ke_id="KE 300", ke_title="t", wp_id="WP300", wp_title="t", created_by="u",
    )
    assert mid is not None
    conn = sqlite3.connect(db.db_path)
    row = conn.execute(
        "SELECT wp_release_date, aopwiki_snapshot_date FROM mappings WHERE id = ?",
        (mid,),
    ).fetchone()
    conn.close()
    assert row == (None, None)
