"""
End-to-end Reactome curator -> admin workflow tests (Phase 25 Plan 06).

Each test maps directly to a ROADMAP Phase 25 success criterion / RCUR-0X
requirement so a regression points at the broken acceptance criterion:

- test_e2e_submit_then_approve_carry_fields_non_null  -> RCUR-02 SC#3
- test_e2e_submit_then_reject_no_mapping              -> RCUR-02 SC#4
- test_e2e_duplicate_approved_blocks                  -> RCUR-03 (approved branch)
- test_e2e_duplicate_pending_blocks                   -> RCUR-03 (pending branch)

Fixture pattern mirrors tests/test_reactome_submission.py and
tests/test_reactome_admin.py: temp-file SQLite DB, fresh model instances
re-wired into both the api and admin blueprints, CSRF disabled, ADMIN_USERS
overridden, session seeded via test_client.session_transaction().
"""
import os
import tempfile

import pytest


# ---------------------------------------------------------------------------
# Shared e2e fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def reactome_e2e_app():
    """
    Boot the Flask test app with a temp DB and Reactome models wired into
    BOTH blueprints (api + admin) so a single test can exercise the full
    curator -> admin pipeline without touching the production DB.
    """
    # ADMIN_USERS must be set before any code path checks it.
    os.environ["ADMIN_USERS"] = "github:e2eadmin"

    from app import app as flask_app
    import src.blueprints.api as api_mod
    import src.blueprints.admin as admin_mod
    from src.core.models import (
        Database,
        ReactomeMappingModel,
        ReactomeProposalModel,
    )

    fd, db_path = tempfile.mkstemp()
    db = Database(db_path)
    rmm = ReactomeMappingModel(db)
    rpm = ReactomeProposalModel(db)

    # Save originals to restore after the test
    orig_api_rmm = api_mod.reactome_mapping_model
    orig_api_rpm = api_mod.reactome_proposal_model
    orig_admin_rmm = admin_mod.reactome_mapping_model
    orig_admin_rpm = admin_mod.reactome_proposal_model

    api_mod.reactome_mapping_model = rmm
    api_mod.reactome_proposal_model = rpm
    admin_mod.reactome_mapping_model = rmm
    admin_mod.reactome_proposal_model = rpm

    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield {"client": client, "db": db, "rmm": rmm, "rpm": rpm}

    # Teardown
    api_mod.reactome_mapping_model = orig_api_rmm
    api_mod.reactome_proposal_model = orig_api_rpm
    admin_mod.reactome_mapping_model = orig_admin_rmm
    admin_mod.reactome_proposal_model = orig_admin_rpm

    os.close(fd)
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login_curator(client, username="github:e2ecurator"):
    """Seed a non-admin curator session into the test client."""
    with client.session_transaction() as sess:
        sess["user"] = {"username": username, "email": "curator@example.com"}


def _login_admin(client, username="github:e2eadmin"):
    """Seed an admin session into the test client (must match ADMIN_USERS)."""
    with client.session_transaction() as sess:
        sess["user"] = {"username": username, "email": "admin@example.com"}


def _submit_payload(
    ke_id="KE 1",
    reactome_id="R-HSA-1234",
    pathway_name="MAPK signaling pathway",
    species="Homo sapiens",
    confidence="high",
    suggestion_score="0.85",
):
    """Build the exact field set Plan 25-05's JS submit handler posts."""
    return {
        "ke_id": ke_id,
        "ke_title": "Test KE for e2e",
        "reactome_id": reactome_id,
        "pathway_name": pathway_name,
        "species": species,
        "confidence_level": confidence,
        "suggestion_score": suggestion_score,
    }


# ---------------------------------------------------------------------------
# Test 1 — RCUR-02 success criterion 3
# ---------------------------------------------------------------------------

def test_e2e_submit_then_approve_carry_fields_non_null(reactome_e2e_app):
    """RCUR-02 SC#3: approved Reactome mapping has all carry-fields non-NULL.

    Curator submits a proposal -> admin approves -> the resulting
    ke_reactome_mappings row must have pathway_name, species, suggestion_score,
    confidence_level, approved_by_curator, approved_at_curator and proposed_by
    all populated. This is the regression sentinel for the carry-field
    propagation chain in src/blueprints/admin.py:approve_reactome_proposal.
    """
    client = reactome_e2e_app["client"]
    rmm = reactome_e2e_app["rmm"]
    rpm = reactome_e2e_app["rpm"]
    db = reactome_e2e_app["db"]

    # 1. Curator submits
    _login_curator(client)
    r = client.post("/submit_reactome_mapping", data=_submit_payload())
    assert r.status_code == 200, r.get_json()
    proposal_id = r.get_json()["proposal_id"]
    assert proposal_id is not None

    # 2. Pre-approval: proposal pending, no mapping
    proposal = rpm.get_proposal_by_id(proposal_id)
    assert proposal is not None
    assert proposal["status"] == "pending"
    pre = rmm.check_mapping_exists("KE 1", "R-HSA-1234")
    assert pre.get("pair_exists") is False

    # 3. Admin approves
    _login_admin(client)
    r = client.post(
        f"/admin/reactome-proposals/{proposal_id}/approve",
        data={"admin_notes": "ok"},
    )
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body["action"] == "created"

    # 4. Post-approval: proposal flipped to approved
    proposal = rpm.get_proposal_by_id(proposal_id)
    assert proposal["status"] == "approved"
    assert proposal["approved_by"] == "github:e2eadmin"

    # 5. Mapping row exists with every carry-field non-NULL
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM ke_reactome_mappings WHERE ke_id = ? AND reactome_id = ?",
            ("KE 1", "R-HSA-1234"),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, "Approved mapping row was not created"
    d = dict(row)

    required_non_null = (
        "pathway_name",
        "species",
        "suggestion_score",
        "confidence_level",
        "approved_by_curator",
        "approved_at_curator",
        "proposed_by",
        "ke_id",
        "reactome_id",
    )
    for col in required_non_null:
        assert d.get(col) is not None, (
            f"RCUR-02 SC#3 FAIL: column {col} is NULL on approved mapping row"
        )

    # Identity carry-through
    assert d["approved_by_curator"] == "github:e2eadmin"
    assert d["proposed_by"] == "github:e2ecurator"
    assert d["confidence_level"] == "high"
    assert d["pathway_name"] == "MAPK signaling pathway"
    assert d["species"] == "Homo sapiens"
    assert d["ke_id"] == "KE 1"
    assert d["reactome_id"] == "R-HSA-1234"
    assert abs(float(d["suggestion_score"]) - 0.85) < 1e-6


# ---------------------------------------------------------------------------
# Test 2 — RCUR-02 success criterion 4
# ---------------------------------------------------------------------------

def test_e2e_submit_then_reject_no_mapping(reactome_e2e_app):
    """RCUR-02 SC#4: rejected proposal does not appear as approved mapping.

    Curator submits -> admin rejects -> ke_reactome_mappings remains empty,
    proposal status flips to rejected with admin_notes / rejected_by /
    rejected_at all set, and the rejected proposal is listable via the
    status=rejected admin filter.
    """
    client = reactome_e2e_app["client"]
    rpm = reactome_e2e_app["rpm"]
    db = reactome_e2e_app["db"]

    _login_curator(client)
    r = client.post("/submit_reactome_mapping", data=_submit_payload())
    assert r.status_code == 200, r.get_json()
    proposal_id = r.get_json()["proposal_id"]

    _login_admin(client)
    r = client.post(
        f"/admin/reactome-proposals/{proposal_id}/reject",
        data={"admin_notes": "not relevant"},
    )
    assert r.status_code == 200, r.get_json()

    proposal = rpm.get_proposal_by_id(proposal_id)
    assert proposal["status"] == "rejected"
    assert proposal["admin_notes"] == "not relevant"
    assert proposal["rejected_by"] == "github:e2eadmin"
    assert proposal["rejected_at"] is not None

    # No mapping row was created
    conn = db.get_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM ke_reactome_mappings "
            "WHERE ke_id = ? AND reactome_id = ?",
            ("KE 1", "R-HSA-1234"),
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 0, "Rejected proposal must not create a mapping row"

    # Rejected proposal is visible via admin status filter
    r = client.get("/admin/reactome-proposals?status=rejected")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "R-HSA-1234" in body, (
        "Rejected proposal not listed under status=rejected admin filter"
    )


# ---------------------------------------------------------------------------
# Test 3 — RCUR-03 (approved-mapping branch)
# ---------------------------------------------------------------------------

def test_e2e_duplicate_approved_blocks(reactome_e2e_app):
    """RCUR-03: an approved (KE, Reactome) pair blocks resubmission.

    Curator submits + admin approves -> a subsequent POST to
    /check_reactome_entry for the same pair returns
    pair_exists=True with blocking_type='approved_mapping' and an `existing`
    payload that exposes the documented carry-fields but never `admin_notes`.
    """
    client = reactome_e2e_app["client"]

    # Setup: submit + approve one pair
    _login_curator(client)
    r = client.post("/submit_reactome_mapping", data=_submit_payload())
    assert r.status_code == 200
    proposal_id = r.get_json()["proposal_id"]

    _login_admin(client)
    r = client.post(
        f"/admin/reactome-proposals/{proposal_id}/approve",
        data={"admin_notes": "ok"},
    )
    assert r.status_code == 200

    # Re-submit attempt: hit the duplicate-check endpoint
    _login_curator(client)
    r = client.post(
        "/check_reactome_entry",
        data={"ke_id": "KE 1", "reactome_id": "R-HSA-1234"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["pair_exists"] is True
    assert body["blocking_type"] == "approved_mapping"
    assert "existing" in body and body["existing"] is not None

    ex = body["existing"]
    for k in (
        "ke_id",
        "ke_title",
        "reactome_id",
        "pathway_name",
        "confidence_level",
        "approved_by_curator",
    ):
        assert k in ex, f"existing payload missing key {k}"
    # Info-disclosure guard: admin_notes must never leak to curators
    assert "admin_notes" not in ex


# ---------------------------------------------------------------------------
# Test 4 — RCUR-03 (pending-proposal branch)
# ---------------------------------------------------------------------------

def test_e2e_duplicate_pending_blocks(reactome_e2e_app):
    """RCUR-03: a pending proposal blocks resubmission of the same pair.

    Curator submits a pair (no admin action yet) -> a subsequent
    /check_reactome_entry for the same pair returns
    pair_exists=True with blocking_type='pending_proposal' and an `existing`
    payload exposing submitted_by + submitted_at but never `admin_notes`.
    """
    client = reactome_e2e_app["client"]

    _login_curator(client)
    r = client.post("/submit_reactome_mapping", data=_submit_payload())
    assert r.status_code == 200

    r = client.post(
        "/check_reactome_entry",
        data={"ke_id": "KE 1", "reactome_id": "R-HSA-1234"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["pair_exists"] is True
    assert body["blocking_type"] == "pending_proposal"

    ex = body["existing"]
    assert "submitted_by" in ex
    assert "submitted_at" in ex
    assert "admin_notes" not in ex
