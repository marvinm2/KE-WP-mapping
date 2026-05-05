"""
Tests for Reactome submission, check, suggest, and search endpoints (Phase 25 Plan 02).

Mirrors tests/test_app.py:TestSubmitGoCreatesProposal fixture pattern.
"""
import os
import tempfile

import pytest


class TestSubmitReactomeCreatesProposal:
    """Verify /submit_reactome_mapping creates a pending proposal, not a direct mapping."""

    @pytest.fixture
    def submit_reactome_client(self):
        """
        Test client that re-wires the api blueprint to a fresh temp-file DB so
        reactome_proposal_model.create_new_pair_reactome_proposal() can persist
        rows. Mirrors the GO submit fixture pattern.
        """
        from app import app as flask_app
        import src.blueprints.api as api_mod
        from src.core.models import (
            CacheModel,
            Database,
            ReactomeMappingModel,
            ReactomeProposalModel,
        )

        fd, db_path = tempfile.mkstemp()
        db = Database(db_path)
        rm = ReactomeMappingModel(db)
        rpm = ReactomeProposalModel(db)
        cm = CacheModel(db)

        # Save originals
        orig_rm = api_mod.reactome_mapping_model
        orig_rpm = api_mod.reactome_proposal_model
        orig_cm = api_mod.cache_model

        # Inject fresh models
        api_mod.reactome_mapping_model = rm
        api_mod.reactome_proposal_model = rpm
        api_mod.cache_model = cm

        flask_app.config["TESTING"] = True
        flask_app.config["WTF_CSRF_ENABLED"] = False
        os.environ["ADMIN_USERS"] = "github:testuser"

        with flask_app.test_client() as test_client:
            with flask_app.app_context():
                with test_client.session_transaction() as sess:
                    sess["user"] = {
                        "username": "github:testuser",
                        "email": "test@example.com",
                    }
                yield test_client

        # Restore originals
        api_mod.reactome_mapping_model = orig_rm
        api_mod.reactome_proposal_model = orig_rpm
        api_mod.cache_model = orig_cm

        os.close(fd)
        os.unlink(db_path)

    @pytest.fixture
    def unauthenticated_client(self):
        """Test client with no session user — for 401 tests."""
        from app import app as flask_app
        import src.blueprints.api as api_mod
        from src.core.models import (
            CacheModel,
            Database,
            ReactomeMappingModel,
            ReactomeProposalModel,
        )

        fd, db_path = tempfile.mkstemp()
        db = Database(db_path)
        rm = ReactomeMappingModel(db)
        rpm = ReactomeProposalModel(db)

        orig_rm = api_mod.reactome_mapping_model
        orig_rpm = api_mod.reactome_proposal_model
        api_mod.reactome_mapping_model = rm
        api_mod.reactome_proposal_model = rpm

        flask_app.config["TESTING"] = True
        flask_app.config["WTF_CSRF_ENABLED"] = False

        with flask_app.test_client() as test_client:
            yield test_client

        api_mod.reactome_mapping_model = orig_rm
        api_mod.reactome_proposal_model = orig_rpm
        os.close(fd)
        os.unlink(db_path)

    @pytest.fixture
    def unwired_client(self):
        """Test client where reactome_proposal_model is None — for 503 tests."""
        from app import app as flask_app
        import src.blueprints.api as api_mod

        orig_rpm = api_mod.reactome_proposal_model
        orig_rm = api_mod.reactome_mapping_model
        api_mod.reactome_proposal_model = None
        api_mod.reactome_mapping_model = None

        flask_app.config["TESTING"] = True
        flask_app.config["WTF_CSRF_ENABLED"] = False

        with flask_app.test_client() as test_client:
            with flask_app.app_context():
                with test_client.session_transaction() as sess:
                    sess["user"] = {"username": "github:testuser"}
                yield test_client

        api_mod.reactome_proposal_model = orig_rpm
        api_mod.reactome_mapping_model = orig_rm

    def test_submit_reactome_creates_proposal_not_mapping(self, submit_reactome_client):
        """POST /submit_reactome_mapping returns 200 with proposal_id."""
        response = submit_reactome_client.post(
            "/submit_reactome_mapping",
            data={
                "ke_id": "KE 12345",
                "ke_title": "Test KE for Reactome",
                "reactome_id": "R-HSA-1234",
                "pathway_name": "MAPK signaling",
                "species": "Homo sapiens",
                "confidence_level": "high",
                "suggestion_score": "0.80",
            },
        )
        assert response.status_code == 200, response.get_json()
        data = response.get_json()
        assert "proposal_id" in data, f"Expected proposal_id, got: {data}"
        assert data["proposal_id"] is not None
        assert "pending" in data.get("message", "").lower()

    def test_submit_reactome_no_live_mapping_created(self, submit_reactome_client):
        """After submit, ke_reactome_mappings table must remain empty."""
        import src.blueprints.api as api_mod

        response = submit_reactome_client.post(
            "/submit_reactome_mapping",
            data={
                "ke_id": "KE 11111",
                "ke_title": "Another Test KE",
                "reactome_id": "R-HSA-5555",
                "pathway_name": "Apoptosis",
                "species": "Homo sapiens",
                "confidence_level": "medium",
            },
        )
        assert response.status_code == 200

        conn = api_mod.reactome_mapping_model.db.get_connection()
        try:
            mapping_count = conn.execute(
                "SELECT COUNT(*) FROM ke_reactome_mappings"
            ).fetchone()[0]
            proposal_count = conn.execute(
                "SELECT COUNT(*) FROM ke_reactome_proposals WHERE status='pending'"
            ).fetchone()[0]
        finally:
            conn.close()

        assert mapping_count == 0, (
            f"Expected 0 live mappings after submit, found {mapping_count}"
        )
        assert proposal_count >= 1, (
            f"Expected >=1 pending proposal, found {proposal_count}"
        )

    def test_submit_reactome_invalid_id_returns_400(self, submit_reactome_client):
        """POST with malformed reactome_id returns 400."""
        response = submit_reactome_client.post(
            "/submit_reactome_mapping",
            data={
                "ke_id": "KE 22222",
                "ke_title": "Bad Reactome ID Test",
                "reactome_id": "HSA-1234",  # missing R- prefix
                "pathway_name": "Some pathway",
                "species": "Homo sapiens",
                "confidence_level": "high",
            },
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get("error") == "Invalid input data"
        assert "details" in data

    def test_submit_reactome_unauthenticated_returns_401(self, unauthenticated_client):
        """Without a session user, /submit_reactome_mapping returns 401."""
        response = unauthenticated_client.post(
            "/submit_reactome_mapping",
            data={
                "ke_id": "KE 33333",
                "ke_title": "Test",
                "reactome_id": "R-HSA-1234",
                "pathway_name": "Test pathway",
                "species": "Homo sapiens",
                "confidence_level": "high",
            },
        )
        # login_required decorator returns 401 for unauth
        assert response.status_code == 401

    def test_submit_reactome_unwired_returns_503(self, unwired_client):
        """When reactome_proposal_model is None, returns 503."""
        response = unwired_client.post(
            "/submit_reactome_mapping",
            data={
                "ke_id": "KE 44444",
                "ke_title": "Unwired test",
                "reactome_id": "R-HSA-1234",
                "pathway_name": "Some pathway",
                "species": "Homo sapiens",
                "confidence_level": "high",
            },
        )
        assert response.status_code == 503
        data = response.get_json()
        assert "unavailable" in data.get("error", "").lower()


class TestCheckReactomeEntry:
    """Verify /check_reactome_entry duplicate detection contract."""

    @pytest.fixture
    def check_client(self):
        """Test client wired to a fresh DB."""
        from app import app as flask_app
        import src.blueprints.api as api_mod
        from src.core.models import (
            Database,
            ReactomeMappingModel,
            ReactomeProposalModel,
        )

        fd, db_path = tempfile.mkstemp()
        db = Database(db_path)
        rm = ReactomeMappingModel(db)
        rpm = ReactomeProposalModel(db)

        orig_rm = api_mod.reactome_mapping_model
        orig_rpm = api_mod.reactome_proposal_model
        api_mod.reactome_mapping_model = rm
        api_mod.reactome_proposal_model = rpm

        flask_app.config["TESTING"] = True
        flask_app.config["WTF_CSRF_ENABLED"] = False

        with flask_app.test_client() as test_client:
            with flask_app.app_context():
                yield test_client, rm, rpm, db

        api_mod.reactome_mapping_model = orig_rm
        api_mod.reactome_proposal_model = orig_rpm
        os.close(fd)
        os.unlink(db_path)

    def test_check_reactome_entry_empty_db_returns_pair_not_exists(self, check_client):
        """On an empty DB, no pair exists."""
        client, rm, rpm, db = check_client
        response = client.post(
            "/check_reactome_entry",
            data={"ke_id": "KE 1", "reactome_id": "R-HSA-1234"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["pair_exists"] is False
        assert data["blocking_type"] is None

    def test_check_reactome_entry_approved_mapping_blocks(self, check_client):
        """After seeding an approved mapping, the same pair is blocked as approved_mapping."""
        client, rm, rpm, db = check_client
        # Seed an approved mapping
        mapping_id = rm.create_mapping(
            ke_id="KE 999",
            ke_title="Seeded KE",
            reactome_id="R-HSA-9999",
            pathway_name="Seeded pathway",
            species="Homo sapiens",
            confidence_level="high",
            suggestion_score=0.9,
            created_by="curator",
        )
        assert mapping_id is not None
        rm.update_reactome_mapping(
            mapping_id=mapping_id,
            approved_by_curator="github:admin",
            approved_at_curator="2026-05-05T00:00:00",
        )

        response = client.post(
            "/check_reactome_entry",
            data={"ke_id": "KE 999", "reactome_id": "R-HSA-9999"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["pair_exists"] is True
        assert data["blocking_type"] == "approved_mapping"
        assert data["existing"]["ke_id"] == "KE 999"
        assert data["existing"]["reactome_id"] == "R-HSA-9999"

    def test_check_reactome_entry_invalid_id_returns_400(self, check_client):
        """Malformed reactome_id returns 400."""
        client, rm, rpm, db = check_client
        response = client.post(
            "/check_reactome_entry",
            data={"ke_id": "KE 1", "reactome_id": "HSA-1234"},  # missing R-
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get("error") == "Invalid input data"


class _FakeReactomeSuggestionService:
    """Minimal fake mirroring the public surface used by the api endpoints."""

    def __init__(self):
        self.calls = []

    def get_reactome_suggestions(self, ke_id, ke_title=None, limit=20):
        self.calls.append(("suggest", ke_id, ke_title, limit))
        return {
            "ke_id": ke_id,
            "ke_title": ke_title or "",
            "suggestions": [
                {
                    "reactome_id": "R-HSA-1234",
                    "pathway_name": "MAPK signaling",
                    "species": "Homo sapiens",
                    "suggestion_score": 0.8,
                }
            ],
            "total_results": 1,
        }

    def search_reactome_terms(self, query, threshold=0.4, limit=10):
        self.calls.append(("search", query, threshold, limit))
        return [
            {
                "reactome_id": "R-HSA-1234",
                "pathway_name": "MAPK signaling pathway",
                "species": "Homo sapiens",
                "description": "MAPK cascade",
                "name_similarity": 0.9,
                "relevance_score": 0.9,
            }
        ]


class TestSuggestReactomeEndpoint:
    """Verify GET /suggest_reactome/<ke_id> wraps Phase 24 suggestions."""

    @pytest.fixture
    def suggest_client(self):
        from app import app as flask_app
        import src.blueprints.api as api_mod

        fake = _FakeReactomeSuggestionService()
        orig = api_mod.reactome_suggestion_service
        api_mod.reactome_suggestion_service = fake

        flask_app.config["TESTING"] = True
        flask_app.config["WTF_CSRF_ENABLED"] = False

        with flask_app.test_client() as test_client:
            yield test_client, fake

        api_mod.reactome_suggestion_service = orig

    @pytest.fixture
    def unwired_suggest_client(self):
        from app import app as flask_app
        import src.blueprints.api as api_mod

        orig = api_mod.reactome_suggestion_service
        api_mod.reactome_suggestion_service = None

        flask_app.config["TESTING"] = True
        flask_app.config["WTF_CSRF_ENABLED"] = False

        with flask_app.test_client() as test_client:
            yield test_client

        api_mod.reactome_suggestion_service = orig

    def test_suggest_reactome_returns_payload_with_request_info(self, suggest_client):
        client, fake = suggest_client
        response = client.get("/suggest_reactome/KE%2012345?ke_title=Test&limit=20")
        assert response.status_code == 200
        data = response.get_json()
        assert "suggestions" in data
        assert "request_info" in data
        info = data["request_info"]
        assert info["ke_id"] == "KE 12345"
        assert info["ke_title"] == "Test"
        assert info["limit"] == 20
        assert "timestamp" in info

    def test_suggest_reactome_clamps_limit_to_50(self, suggest_client):
        client, fake = suggest_client
        response = client.get("/suggest_reactome/KE%201?limit=999")
        assert response.status_code == 200
        # Verify limit was clamped before the service call
        assert fake.calls[-1][3] == 50  # the limit passed to the service

    def test_suggest_reactome_unwired_returns_503(self, unwired_suggest_client):
        response = unwired_suggest_client.get("/suggest_reactome/KE%201")
        assert response.status_code == 503

    def test_suggest_reactome_blank_id_returns_400(self, suggest_client):
        client, _ = suggest_client
        # `/suggest_reactome/` (no ke_id) -> 404 from Flask routing.
        # `/suggest_reactome/%20` (whitespace ke_id) -> validated to 400.
        response = client.get("/suggest_reactome/%20")
        assert response.status_code == 400


class TestSearchReactomeEndpoint:
    """Verify GET /search_reactome wraps fuzzy search."""

    @pytest.fixture
    def search_client(self):
        from app import app as flask_app
        import src.blueprints.api as api_mod

        fake = _FakeReactomeSuggestionService()
        orig = api_mod.reactome_suggestion_service
        api_mod.reactome_suggestion_service = fake

        flask_app.config["TESTING"] = True
        flask_app.config["WTF_CSRF_ENABLED"] = False

        with flask_app.test_client() as test_client:
            yield test_client, fake

        api_mod.reactome_suggestion_service = orig

    @pytest.fixture
    def unwired_search_client(self):
        from app import app as flask_app
        import src.blueprints.api as api_mod

        orig = api_mod.reactome_suggestion_service
        api_mod.reactome_suggestion_service = None

        flask_app.config["TESTING"] = True
        flask_app.config["WTF_CSRF_ENABLED"] = False

        with flask_app.test_client() as test_client:
            yield test_client

        api_mod.reactome_suggestion_service = orig

    def test_search_reactome_returns_results_envelope(self, search_client):
        client, fake = search_client
        response = client.get("/search_reactome?q=MAPK&threshold=0.4&limit=5")
        assert response.status_code == 200
        data = response.get_json()
        for key in ("query", "threshold", "limit", "results", "total_results", "timestamp"):
            assert key in data, f"Missing key {key} in response: {data}"
        assert data["query"] == "MAPK"
        assert data["total_results"] == len(data["results"])

    def test_search_reactome_no_query_returns_400(self, search_client):
        client, _ = search_client
        response = client.get("/search_reactome")
        assert response.status_code == 400
        data = response.get_json()
        assert "required" in data.get("error", "").lower()

    def test_search_reactome_clamps_threshold(self, search_client):
        client, fake = search_client
        response = client.get("/search_reactome?q=MAPK&threshold=99")
        assert response.status_code == 200
        # The clamped threshold (0.4) appears in the response envelope
        assert response.get_json()["threshold"] == 0.4
        # And was passed to the service
        assert fake.calls[-1][2] == 0.4

    def test_search_reactome_unwired_returns_503(self, unwired_search_client):
        response = unwired_search_client.get("/search_reactome?q=MAPK")
        assert response.status_code == 503


# ---------------------------------------------------------------------------
# Phase 25 Plan 05 — top-level functional + static-source tests
# ---------------------------------------------------------------------------
# These tests verify the JS frontend (Plan 25-05) integrates correctly with
# the Plan 25-02 endpoints. The check_entry test is named to match the Plan
# 25-05 verify command (top-level discoverability via
# `tests/test_reactome_submission.py::test_check_reactome_entry_blocks_approved_mapping`).


@pytest.fixture
def _plan_05_check_client():
    """Module-level fixture mirroring TestCheckReactomeEntry.check_client."""
    from app import app as flask_app
    import src.blueprints.api as api_mod
    from src.core.models import (
        Database,
        ReactomeMappingModel,
        ReactomeProposalModel,
    )

    fd, db_path = tempfile.mkstemp()
    db = Database(db_path)
    rm = ReactomeMappingModel(db)
    rpm = ReactomeProposalModel(db)

    orig_rm = api_mod.reactome_mapping_model
    orig_rpm = api_mod.reactome_proposal_model
    api_mod.reactome_mapping_model = rm
    api_mod.reactome_proposal_model = rpm

    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.test_client() as test_client:
        with flask_app.app_context():
            yield test_client, rm, rpm, db

    api_mod.reactome_mapping_model = orig_rm
    api_mod.reactome_proposal_model = orig_rpm
    os.close(fd)
    os.unlink(db_path)


def test_check_reactome_entry_blocks_approved_mapping(_plan_05_check_client):
    """Plan 25-05 Task 2 — POST /check_reactome_entry returns blocking_type=approved_mapping
    when an approved mapping exists for the (KE, Reactome) pair, and the `existing` payload
    contains the documented fields but not admin_notes."""
    client, rm, rpm, db = _plan_05_check_client
    mapping_id = rm.create_mapping(
        ke_id="KE 1",
        ke_title="Increase, Oxidative Stress",
        reactome_id="R-HSA-1234",
        pathway_name="MAPK signaling",
        species="Homo sapiens",
        confidence_level="medium",
        suggestion_score=0.72,
        created_by="curator",
    )
    assert mapping_id is not None
    rm.update_reactome_mapping(
        mapping_id=mapping_id,
        approved_by_curator="github:admin",
        approved_at_curator="2026-05-05T00:00:00",
    )

    response = client.post(
        "/check_reactome_entry",
        data={"ke_id": "KE 1", "reactome_id": "R-HSA-1234"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["pair_exists"] is True
    assert data["blocking_type"] == "approved_mapping"
    existing = data["existing"]
    # Documented carry-fields per Plan 25-05 threat model
    for key in (
        "ke_id",
        "ke_title",
        "reactome_id",
        "pathway_name",
        "confidence_level",
        "approved_by_curator",
        "approved_at_curator",
    ):
        assert key in existing, f"missing {key} in existing payload"
    # admin_notes is NOT exposed via /check_reactome_entry
    assert "admin_notes" not in existing


def test_submit_reactome_form_field_set_matches_schema():
    """Plan 25-05 Task 3 — Static-source verification that the JS submit handler's
    payload object contains exactly the fields the /submit_reactome_mapping endpoint
    and ReactomeMappingSchema accept (per CONTEXT.md D-18). Pure regex over the JS source.
    """
    import re
    here = os.path.dirname(os.path.abspath(__file__))
    js_path = os.path.normpath(os.path.join(here, "..", "static", "js", "main.js"))
    with open(js_path, "r", encoding="utf-8") as fh:
        src = fh.read()

    # Locate the handleReactomeFormSubmission method body.
    m = re.search(
        r"handleReactomeFormSubmission\s*\([^)]*\)\s*\{(.*?)\n    \}",
        src,
        re.DOTALL,
    )
    assert m, "handleReactomeFormSubmission method not found in static/js/main.js"
    body = m.group(1)

    # Locate the payload object literal inside the method body.
    payload_m = re.search(r"const\s+payload\s*=\s*\{(.+?)\};", body, re.DOTALL)
    assert payload_m, "payload object not found inside handleReactomeFormSubmission"
    payload_src = payload_m.group(1)

    required_keys = {
        "ke_id",
        "ke_title",
        "reactome_id",
        "pathway_name",
        "species",
        "confidence_level",
        "suggestion_score",
        "csrf_token",
    }
    for key in required_keys:
        # Match `key:` at start of token (ignoring whitespace)
        assert re.search(r"\b" + re.escape(key) + r"\s*:", payload_src), (
            f"submit payload is missing field '{key}': {payload_src}"
        )

    # The POST URL must be /submit_reactome_mapping
    assert "/submit_reactome_mapping" in body, (
        "handleReactomeFormSubmission should POST to /submit_reactome_mapping"
    )


# ---------------------------------------------------------------------------
# Phase 25 Plan 06 — GO-parity gap-fill tests
# ---------------------------------------------------------------------------
# These augmentations close GO-parity gaps surfaced while authoring the e2e
# suite (tests/test_reactome_e2e.py). They live alongside Plan 25-02's
# class-based tests in this file rather than in a new file because they share
# the same blueprint surface.


@pytest.fixture
def _gapfill_unauthenticated_client():
    """Fresh test client with NO session user (mirrors unauthenticated_client)."""
    from app import app as flask_app
    import src.blueprints.api as api_mod
    from src.core.models import (
        Database,
        ReactomeMappingModel,
        ReactomeProposalModel,
    )

    fd, db_path = tempfile.mkstemp()
    db = Database(db_path)
    rm = ReactomeMappingModel(db)
    rpm = ReactomeProposalModel(db)

    orig_rm = api_mod.reactome_mapping_model
    orig_rpm = api_mod.reactome_proposal_model
    api_mod.reactome_mapping_model = rm
    api_mod.reactome_proposal_model = rpm

    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.test_client() as test_client:
        yield test_client

    api_mod.reactome_mapping_model = orig_rm
    api_mod.reactome_proposal_model = orig_rpm
    os.close(fd)
    os.unlink(db_path)


@pytest.fixture
def _gapfill_curator_client():
    """Authenticated curator session (NOT admin) on a fresh DB."""
    from app import app as flask_app
    import src.blueprints.api as api_mod
    from src.core.models import (
        Database,
        ReactomeMappingModel,
        ReactomeProposalModel,
    )

    fd, db_path = tempfile.mkstemp()
    db = Database(db_path)
    rm = ReactomeMappingModel(db)
    rpm = ReactomeProposalModel(db)

    orig_rm = api_mod.reactome_mapping_model
    orig_rpm = api_mod.reactome_proposal_model
    api_mod.reactome_mapping_model = rm
    api_mod.reactome_proposal_model = rpm

    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.test_client() as test_client:
        with flask_app.app_context():
            with test_client.session_transaction() as sess:
                sess["user"] = {"username": "github:gapfilluser"}
            yield test_client, rpm

    api_mod.reactome_mapping_model = orig_rm
    api_mod.reactome_proposal_model = orig_rpm
    os.close(fd)
    os.unlink(db_path)


def test_submit_reactome_unauthenticated(_gapfill_unauthenticated_client):
    """Plan 25-06 RCUR-04: @login_required gate must reject anonymous POSTs.

    Alias-named gap-fill mirroring TestSubmitReactomeCreatesProposal's
    test_submit_reactome_unauthenticated_returns_401 — the success-criteria
    grep tracks the shorter name. Reactome submission MUST refuse anonymous
    submissions (auth gate) regardless of CSRF state.
    """
    client = _gapfill_unauthenticated_client
    r = client.post(
        "/submit_reactome_mapping",
        data={
            "ke_id": "KE 1",
            "ke_title": "Test",
            "reactome_id": "R-HSA-1234",
            "pathway_name": "MAPK signaling",
            "species": "Homo sapiens",
            "confidence_level": "high",
            "suggestion_score": "0.8",
        },
    )
    # login_required returns 401 (Reactome blueprint contract — verified at
    # api.py:1481+); 302 redirect would also be acceptable for some auth setups.
    assert r.status_code in (401, 302), (
        f"Expected 401/302 for unauthenticated POST, got {r.status_code}"
    )


def test_submit_reactome_invalid_csrf():
    """Plan 25-06 RCUR-04: invalid/missing CSRF token must reject the submission
    even when the user is authenticated.

    With Flask-WTF CSRF enabled (production default per app.py:95), a POST that
    arrives without a valid csrf_token must be rejected before the route body
    runs — no proposal created. This test enables CSRF on the test app to
    verify the protection wires correctly to /submit_reactome_mapping.
    """
    from app import app as flask_app
    import src.blueprints.api as api_mod
    from src.core.models import (
        Database,
        ReactomeMappingModel,
        ReactomeProposalModel,
    )

    fd, db_path = tempfile.mkstemp()
    db = Database(db_path)
    rm = ReactomeMappingModel(db)
    rpm = ReactomeProposalModel(db)

    orig_rm = api_mod.reactome_mapping_model
    orig_rpm = api_mod.reactome_proposal_model
    api_mod.reactome_mapping_model = rm
    api_mod.reactome_proposal_model = rpm

    # Restore prior CSRF setting so this test does not leak state to siblings.
    prior_csrf = flask_app.config.get("WTF_CSRF_ENABLED", True)
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = True

    try:
        with flask_app.test_client() as client:
            with flask_app.app_context():
                with client.session_transaction() as sess:
                    sess["user"] = {"username": "github:csrfuser"}
                # No csrf_token field included — CSRF protection must reject.
                r = client.post(
                    "/submit_reactome_mapping",
                    data={
                        "ke_id": "KE 1",
                        "ke_title": "Test",
                        "reactome_id": "R-HSA-1234",
                        "pathway_name": "MAPK signaling",
                        "species": "Homo sapiens",
                        "confidence_level": "high",
                        "suggestion_score": "0.8",
                    },
                )
                # Project-wide CSRF handler returns 400 with a JSON error
                # (app.py:handle_csrf_error). Some configurations return 403.
                assert r.status_code in (400, 403), (
                    f"Expected 400/403 for missing CSRF token, got {r.status_code}"
                )
                # And no proposal must have been written
                conn = db.get_connection()
                try:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM ke_reactome_proposals"
                    ).fetchone()[0]
                finally:
                    conn.close()
                assert count == 0, (
                    "CSRF-rejected submit must not write a proposal row"
                )
    finally:
        flask_app.config["WTF_CSRF_ENABLED"] = prior_csrf
        api_mod.reactome_mapping_model = orig_rm
        api_mod.reactome_proposal_model = orig_rpm
        os.close(fd)
        os.unlink(db_path)


def test_submit_reactome_drops_unknown_form_fields(_gapfill_curator_client):
    """Plan 25-06 RCUR-04: Marshmallow schema strips unknown form fields.

    Attackers must not be able to smuggle non-Reactome fields like
    `connection_type` or `go_namespace` through the submit endpoint —
    ReactomeMappingSchema does not declare them, so they must not land on
    the proposal row. Defends against silent column-shadowing attacks.
    """
    client, rpm = _gapfill_curator_client
    r = client.post(
        "/submit_reactome_mapping",
        data={
            "ke_id": "KE 99",
            "ke_title": "Drop-unknown test",
            "reactome_id": "R-HSA-9999",
            "pathway_name": "Apoptosis",
            "species": "Homo sapiens",
            "confidence_level": "medium",
            "suggestion_score": "0.5",
            # Smuggling attempts — must be ignored, never persisted
            "connection_type": "increase",
            "go_namespace": "BP",
            "approved_by_curator": "github:attacker",  # privilege-escalation attempt
        },
    )
    assert r.status_code == 200, r.get_json()
    proposal_id = r.get_json()["proposal_id"]
    proposal = rpm.get_proposal_by_id(proposal_id)
    assert proposal is not None
    # Reactome proposal schema has none of these columns — at most they would
    # appear as None on the dict if they existed; but they should not exist.
    for forbidden in ("connection_type", "go_namespace"):
        assert proposal.get(forbidden) in (None, ""), (
            f"Unknown form field '{forbidden}' leaked into proposal row: "
            f"{proposal.get(forbidden)!r}"
        )
    # Status must remain pending — the smuggled approved_by_curator column
    # would be on the mappings table not the proposal, but assert sanity:
    assert proposal["status"] == "pending"
