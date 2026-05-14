"""Phase 34 (ASMT-02/07/08) — KE-WP HTTP end-to-end assessment round-trip.

HTTP path: POST /submit (with step1..step4) -> /admin/proposals/<id>/approve ->
MappingModel.get_all_mappings(). Asserts the four proposed_* columns +
assessment_version survive the proposal -> mapping handoff AND appear in the
bulk-export SELECT.

Guards Pitfall 1 (the named 4th-recurrence bulk-export SELECT drift) AND
Pitfall 4 (Marshmallow silently dropping unknown fields).

Fixture pattern mirrors tests/test_reactome_admin.py::admin_client (a single
test_client wired with both /submit and /admin/* model globals on a shared
temp-file DB, with an admin-role session).
"""
import os
import tempfile

import pytest


@pytest.fixture
def wp_admin_client():
    """Test client with both api + admin blueprints wired to a shared temp-file
    WP DB, authenticated as a github:testadmin user (in ADMIN_USERS)."""
    # Set ADMIN_USERS BEFORE importing app so admin_required honors the override.
    os.environ["ADMIN_USERS"] = "github:testadmin"

    from app import app as flask_app
    import src.blueprints.admin as admin_mod
    import src.blueprints.api as api_mod
    from src.core.models import CacheModel, Database, MappingModel, ProposalModel

    fd, db_path = tempfile.mkstemp()
    db = Database(db_path)
    mm = MappingModel(db)
    pm = ProposalModel(db)
    cm = CacheModel(db)

    # Save originals
    orig_api_pm = api_mod.proposal_model
    orig_api_mm = api_mod.mapping_model
    orig_api_cm = api_mod.cache_model
    orig_admin_pm = admin_mod.proposal_model
    orig_admin_mm = admin_mod.mapping_model

    # Inject fresh models into BOTH blueprints (they each hold their own
    # module globals — wiring only api wouldn't let admin see the proposals
    # row when approve_proposal runs).
    api_mod.proposal_model = pm
    api_mod.mapping_model = mm
    api_mod.cache_model = cm
    admin_mod.proposal_model = pm
    admin_mod.mapping_model = mm

    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.test_client() as test_client:
        with flask_app.app_context():
            with test_client.session_transaction() as sess:
                sess["user"] = {
                    "username": "github:testadmin",
                    "email": "admin@example.com",
                }
            yield test_client, mm, pm, db

    # Restore
    api_mod.proposal_model = orig_api_pm
    api_mod.mapping_model = orig_api_mm
    api_mod.cache_model = orig_api_cm
    admin_mod.proposal_model = orig_admin_pm
    admin_mod.mapping_model = orig_admin_mm

    os.close(fd)
    os.unlink(db_path)


def test_assessment_roundtrip_wp(wp_admin_client):
    """Happy path: submit with all four step* answers, approve, assert the
    four proposed_* columns + assessment_version='v2' survive end-to-end."""
    client, mm, pm, db = wp_admin_client

    # 1. Submit a proposal with all four assessment answers populated.
    resp = client.post(
        "/submit",
        data={
            "ke_id": "KE 300",
            "ke_title": "Test KE 300",
            "wp_id": "WP100",
            "wp_title": "Test Pathway 100",
            "connection_type": "causative",
            "confidence_level": "high",
            "step1": "causative",
            "step2": "known",
            "step3": "specific",
            "step4": "complete",
        },
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    proposal_id = resp.get_json()["proposal_id"]
    assert proposal_id is not None

    # 2. Admin approves the proposal.
    resp = client.post(
        f"/admin/proposals/{proposal_id}/approve",
        data={"admin_notes": "looks good"},
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body.get("action") == "created"

    # 3. Read via the bulk-export SELECT (guards Pitfall 1).
    rows = mm.get_all_mappings()
    wp_row = next(r for r in rows if r["ke_id"] == "KE 300")
    assert wp_row["proposed_relationship"] == "causative"
    assert wp_row["proposed_basis"] == "known"
    assert wp_row["proposed_specificity"] == "specific"
    assert wp_row["proposed_coverage"] == "complete"
    assert wp_row["assessment_version"] == "v2"


def test_assessment_legacy_v1_wp(wp_admin_client):
    """Backward-compat: submit WITHOUT any step* fields; assert the four
    proposed_* columns are NULL and assessment_version defaults to 'v1'."""
    client, mm, pm, db = wp_admin_client

    resp = client.post(
        "/submit",
        data={
            "ke_id": "KE 301",
            "ke_title": "Legacy KE 301",
            "wp_id": "WP101",
            "wp_title": "Legacy Pathway 101",
            "connection_type": "undefined",
            "confidence_level": "low",
        },
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    proposal_id = resp.get_json()["proposal_id"]

    resp = client.post(
        f"/admin/proposals/{proposal_id}/approve",
        data={"admin_notes": "legacy approval"},
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)

    rows = mm.get_all_mappings()
    wp_row = next(r for r in rows if r["ke_id"] == "KE 301")
    assert wp_row["assessment_version"] == "v1"
    assert wp_row["proposed_relationship"] is None
    assert wp_row["proposed_basis"] is None
    assert wp_row["proposed_specificity"] is None
    assert wp_row["proposed_coverage"] is None


def test_assessment_schema_rejects_invalid_option(wp_admin_client):
    """Whitelist enforcement: POST with an out-of-whitelist step1 value
    returns 400 via the MappingSchema validate.OneOf check."""
    client, mm, pm, db = wp_admin_client

    resp = client.post(
        "/submit",
        data={
            "ke_id": "KE 302",
            "ke_title": "Bad KE 302",
            "wp_id": "WP102",
            "wp_title": "Bad Pathway 102",
            "connection_type": "causative",
            "confidence_level": "high",
            "step1": "banana",  # not in KE_WP_RELATIONSHIP_OPTIONS
        },
    )
    assert resp.status_code == 400
    body = resp.get_json()
    # Marshmallow surfaces the per-field error under details.<field>
    assert "step1" in str(body.get("details", body))
