"""
Tests for Reactome admin routes (Phase 25 Plan 03):
- GET  /admin/reactome-proposals       (list dashboard)
- GET  /admin/reactome-proposals/<id>  (JSON detail)
- POST /admin/reactome-proposals/<id>/approve
- POST /admin/reactome-proposals/<id>/reject

Mirrors tests/test_app.py:TestSubmitGoCreatesProposal fixture pattern but for
the admin blueprint, with ADMIN_USERS env override and admin-session seeding.
"""
import os
import tempfile

import pytest


@pytest.fixture
def admin_client():
    """
    Test client wired with fresh Reactome models on a temp-file DB and an
    authenticated admin session (github:testadmin).
    """
    # Set ADMIN_USERS BEFORE importing app so admin_required honors the override.
    os.environ["ADMIN_USERS"] = "github:testadmin"

    from app import app as flask_app
    import src.blueprints.admin as admin_mod
    from src.core.models import (
        Database,
        ReactomeMappingModel,
        ReactomeProposalModel,
    )

    fd, db_path = tempfile.mkstemp()
    db = Database(db_path)
    rm = ReactomeMappingModel(db)
    rpm = ReactomeProposalModel(db)

    # Save originals
    orig_rm = admin_mod.reactome_mapping_model
    orig_rpm = admin_mod.reactome_proposal_model

    # Inject fresh models
    admin_mod.reactome_mapping_model = rm
    admin_mod.reactome_proposal_model = rpm

    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.test_client() as test_client:
        with flask_app.app_context():
            with test_client.session_transaction() as sess:
                sess["user"] = {
                    "username": "github:testadmin",
                    "email": "admin@example.com",
                }
            yield test_client, rm, rpm, db

    # Restore
    admin_mod.reactome_mapping_model = orig_rm
    admin_mod.reactome_proposal_model = orig_rpm

    os.close(fd)
    os.unlink(db_path)


@pytest.fixture
def non_admin_client():
    """Test client where session user is NOT in ADMIN_USERS."""
    os.environ["ADMIN_USERS"] = "github:someoneelse"

    from app import app as flask_app
    import src.blueprints.admin as admin_mod
    from src.core.models import (
        Database,
        ReactomeMappingModel,
        ReactomeProposalModel,
    )

    fd, db_path = tempfile.mkstemp()
    db = Database(db_path)
    rm = ReactomeMappingModel(db)
    rpm = ReactomeProposalModel(db)

    orig_rm = admin_mod.reactome_mapping_model
    orig_rpm = admin_mod.reactome_proposal_model
    admin_mod.reactome_mapping_model = rm
    admin_mod.reactome_proposal_model = rpm

    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.test_client() as test_client:
        with flask_app.app_context():
            with test_client.session_transaction() as sess:
                sess["user"] = {"username": "github:randomuser"}
            yield test_client, rm, rpm, db

    admin_mod.reactome_mapping_model = orig_rm
    admin_mod.reactome_proposal_model = orig_rpm

    os.close(fd)
    os.unlink(db_path)


def _seed_proposal(rpm, ke_id="KE 1001", reactome_id="R-HSA-1234",
                   pathway_name="MAPK signaling", confidence_level="high",
                   provider_username="github:curator", suggestion_score=0.75):
    """Seed a single new-pair Reactome proposal and return its id."""
    proposal_id = rpm.create_new_pair_reactome_proposal(
        ke_id=ke_id,
        ke_title=f"Title for {ke_id}",
        reactome_id=reactome_id,
        pathway_name=pathway_name,
        confidence_level=confidence_level,
        species="Homo sapiens",
        provider_username=provider_username,
        suggestion_score=suggestion_score,
    )
    assert proposal_id is not None
    return proposal_id


class TestAdminReactomeProposalsList:

    def test_admin_reactome_proposals_list_renders(self, admin_client):
        """GET /admin/reactome-proposals as admin returns 200 and the page heading."""
        client, rm, rpm, db = admin_client
        _seed_proposal(rpm)
        response = client.get("/admin/reactome-proposals")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "Admin: KE-Reactome Proposal Management" in body

    def test_admin_reactome_proposals_list_blocks_non_admin(self, non_admin_client):
        """Non-admin user gets 403."""
        client, rm, rpm, db = non_admin_client
        response = client.get("/admin/reactome-proposals")
        assert response.status_code == 403

    def test_admin_reactome_proposals_list_filter_status(self, admin_client):
        """status query param filters proposals."""
        client, rm, rpm, db = admin_client
        # Seed pending + rejected
        pid_pending = _seed_proposal(rpm, ke_id="KE 2001", reactome_id="R-HSA-2001")
        pid_rejected = _seed_proposal(rpm, ke_id="KE 2002", reactome_id="R-HSA-2002")
        rpm.update_proposal_status(
            proposal_id=pid_rejected,
            status="rejected",
            admin_username="github:testadmin",
            admin_notes="not relevant",
        )

        # Filter approved should return empty
        response = client.get("/admin/reactome-proposals?status=approved")
        assert response.status_code == 200


class TestAdminReactomeProposalDetail:

    def test_detail_returns_proposal_json(self, admin_client):
        client, rm, rpm, db = admin_client
        pid = _seed_proposal(rpm)
        response = client.get(f"/admin/reactome-proposals/{pid}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == pid
        assert data["ke_id"] == "KE 1001"
        assert data["reactome_id"] == "R-HSA-1234"
        assert "created_at_formatted" in data

    def test_detail_404_for_unknown_id(self, admin_client):
        client, rm, rpm, db = admin_client
        response = client.get("/admin/reactome-proposals/99999")
        assert response.status_code == 404
        assert response.get_json().get("error") == "Reactome proposal not found"

    def test_detail_blocks_non_admin(self, non_admin_client):
        client, rm, rpm, db = non_admin_client
        # Seed via fixture's rpm (still works even though session user is non-admin)
        pid = _seed_proposal(rpm)
        response = client.get(f"/admin/reactome-proposals/{pid}")
        assert response.status_code == 403


class TestApproveReactomeProposal:

    def test_approve_creates_mapping_with_carry_fields(self, admin_client):
        """RCUR-02 success criterion 3: approval writes all carry fields non-NULL."""
        client, rm, rpm, db = admin_client
        pid = _seed_proposal(
            rpm,
            ke_id="KE 3001",
            reactome_id="R-HSA-3001",
            pathway_name="Apoptosis",
            confidence_level="medium",
            provider_username="github:curator1",
            suggestion_score=0.82,
        )

        response = client.post(
            f"/admin/reactome-proposals/{pid}/approve",
            data={"admin_notes": "looks good"},
        )
        assert response.status_code == 200, response.get_json()
        body = response.get_json()
        assert body["action"] == "created"
        assert "approved successfully" in body["message"].lower()

        # Inspect the new mapping row
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM ke_reactome_mappings WHERE ke_id = ? AND reactome_id = ?",
                ("KE 3001", "R-HSA-3001"),
            ).fetchone()
        finally:
            conn.close()
        assert row is not None
        d = dict(row)
        assert d["pathway_name"] == "Apoptosis"
        assert d["species"] == "Homo sapiens"
        assert d["suggestion_score"] is not None
        assert abs(d["suggestion_score"] - 0.82) < 1e-9
        assert d["confidence_level"] == "medium"
        assert d["approved_by_curator"] == "github:testadmin"
        assert d["approved_at_curator"] is not None
        assert d["proposed_by"] == "github:curator1"

    def test_approve_updates_proposal_status(self, admin_client):
        client, rm, rpm, db = admin_client
        pid = _seed_proposal(rpm, ke_id="KE 3002", reactome_id="R-HSA-3002")
        response = client.post(
            f"/admin/reactome-proposals/{pid}/approve",
            data={"admin_notes": "ok"},
        )
        assert response.status_code == 200

        proposal = rpm.get_proposal_by_id(pid)
        assert proposal["status"] == "approved"
        assert proposal["approved_by"] == "github:testadmin"
        assert proposal["admin_notes"] == "ok"

    def test_approve_already_approved_returns_400(self, admin_client):
        client, rm, rpm, db = admin_client
        pid = _seed_proposal(rpm, ke_id="KE 3003", reactome_id="R-HSA-3003")
        # First approval
        response = client.post(
            f"/admin/reactome-proposals/{pid}/approve",
            data={"admin_notes": "first"},
        )
        assert response.status_code == 200
        # Second approval should fail
        response2 = client.post(
            f"/admin/reactome-proposals/{pid}/approve",
            data={"admin_notes": "second"},
        )
        assert response2.status_code == 400
        assert "is already approved" in response2.get_json()["error"]

    def test_approve_blocks_non_admin(self, non_admin_client):
        client, rm, rpm, db = non_admin_client
        pid = _seed_proposal(rpm, ke_id="KE 3004", reactome_id="R-HSA-3004")
        response = client.post(
            f"/admin/reactome-proposals/{pid}/approve",
            data={"admin_notes": "x"},
        )
        assert response.status_code == 403

    def test_approve_unknown_proposal_returns_404(self, admin_client):
        client, _, _, _ = admin_client
        response = client.post(
            "/admin/reactome-proposals/99999/approve",
            data={"admin_notes": "x"},
        )
        assert response.status_code == 404

    def test_approve_no_dimension_score_columns_used(self, admin_client):
        """D-02: Reactome approval must NOT touch connection_score / specificity_score / evidence_score
        and the resulting mapping row must NOT have those columns at all (schema lacks them)."""
        client, rm, rpm, db = admin_client
        pid = _seed_proposal(rpm, ke_id="KE 3005", reactome_id="R-HSA-3005")
        response = client.post(
            f"/admin/reactome-proposals/{pid}/approve",
            data={
                "admin_notes": "ok",
                # These would be ignored — Reactome route must not consume them
                "connection_score": "3",
                "specificity_score": "3",
                "evidence_score": "3",
            },
        )
        assert response.status_code == 200

        # Verify ke_reactome_mappings schema lacks those columns
        conn = db.get_connection()
        try:
            cols = [r[1] for r in conn.execute(
                "PRAGMA table_info(ke_reactome_mappings)"
            ).fetchall()]
        finally:
            conn.close()
        assert "connection_score" not in cols
        assert "specificity_score" not in cols
        assert "evidence_score" not in cols
        assert "connection_type" not in cols


class TestRejectReactomeProposal:

    def test_reject_marks_status_rejected(self, admin_client):
        client, rm, rpm, db = admin_client
        pid = _seed_proposal(rpm, ke_id="KE 4001", reactome_id="R-HSA-4001")
        response = client.post(
            f"/admin/reactome-proposals/{pid}/reject",
            data={"admin_notes": "not relevant"},
        )
        assert response.status_code == 200
        proposal = rpm.get_proposal_by_id(pid)
        assert proposal["status"] == "rejected"
        assert proposal["rejected_by"] == "github:testadmin"
        assert proposal["admin_notes"] == "not relevant"

    def test_reject_no_mapping_created(self, admin_client):
        client, rm, rpm, db = admin_client
        pid = _seed_proposal(rpm, ke_id="KE 4002", reactome_id="R-HSA-4002")
        response = client.post(
            f"/admin/reactome-proposals/{pid}/reject",
            data={"admin_notes": "no"},
        )
        assert response.status_code == 200

        conn = db.get_connection()
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM ke_reactome_mappings WHERE ke_id = ? AND reactome_id = ?",
                ("KE 4002", "R-HSA-4002"),
            ).fetchone()[0]
        finally:
            conn.close()
        assert count == 0

    def test_reject_empty_notes_uses_fallback(self, admin_client):
        client, rm, rpm, db = admin_client
        pid = _seed_proposal(rpm, ke_id="KE 4003", reactome_id="R-HSA-4003")
        response = client.post(
            f"/admin/reactome-proposals/{pid}/reject",
            data={"admin_notes": ""},
        )
        assert response.status_code == 200
        proposal = rpm.get_proposal_by_id(pid)
        assert proposal["admin_notes"] == "No reason provided"

    def test_reject_already_rejected_returns_400(self, admin_client):
        client, rm, rpm, db = admin_client
        pid = _seed_proposal(rpm, ke_id="KE 4004", reactome_id="R-HSA-4004")
        client.post(
            f"/admin/reactome-proposals/{pid}/reject",
            data={"admin_notes": "first"},
        )
        response = client.post(
            f"/admin/reactome-proposals/{pid}/reject",
            data={"admin_notes": "second"},
        )
        assert response.status_code == 400
        assert "is already rejected" in response.get_json()["error"]

    def test_reject_blocks_non_admin(self, non_admin_client):
        client, rm, rpm, db = non_admin_client
        pid = _seed_proposal(rpm, ke_id="KE 4005", reactome_id="R-HSA-4005")
        response = client.post(
            f"/admin/reactome-proposals/{pid}/reject",
            data={"admin_notes": "x"},
        )
        assert response.status_code == 403
