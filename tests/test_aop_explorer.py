"""
Regression tests for Phase 36-01: AOP Explorer rename + new backend endpoints.

Guards:
  - AOPX-01: /aop-explorer renders the renamed AOP Explorer page (200)
  - AOPX-02: /aop-network permanently redirects to /aop-explorer (301)
             NOTE: DO NOT DELETE — this test enforces the redirect contract that
             preserves ~10 weeks of inbound links from papers/Slack/slides
             (STATE.md Pitfall 2). Removing /aop-network registration is a
             known footgun.
  - LINK-04: /ke-details and /pw-details deep-links still return 200 (untouched)
  - New API: /api/mapped-ke-ids?type=reactome returns correct JSON shape
  - New API: /api/aop-oecd-status returns 200 with a dict body (empty or populated)
"""
from unittest.mock import MagicMock

import src.blueprints.main as main_module


class TestAopExplorerRename:
    """Route rename and 301 redirect contract (AOPX-01, AOPX-02)."""

    def test_aop_network_redirects_to_explorer(self, client):
        """GET /aop-network must return 301 Location: /aop-explorer.

        DO NOT DELETE — guards Pitfall 2 from STATE.md: the /aop-network route
        must remain registered as the 301 source for inbound links.
        """
        resp = client.get("/aop-network")
        assert resp.status_code == 301, (
            f"Expected 301 redirect, got {resp.status_code}. "
            "The /aop-network route must not be removed — it has ~10 weeks of inbound links."
        )
        location = resp.headers.get("Location", "")
        assert "/aop-explorer" in location, (
            f"Expected Location to contain /aop-explorer, got: {location!r}"
        )

    def test_aop_explorer_returns_200(self, client):
        """GET /aop-explorer must return 200 (AOPX-01)."""
        resp = client.get("/aop-explorer")
        assert resp.status_code == 200


class TestDeepLinkGuards:
    """LINK-04: deep-link routes must not be broken by the rename."""

    def test_ke_details_still_200(self, client):
        """GET /ke-details must still return 200 — untouched by AOPX rename."""
        resp = client.get("/ke-details")
        assert resp.status_code == 200

    def test_pw_details_still_200(self, client):
        """GET /pw-details must still return 200 — untouched by AOPX rename."""
        resp = client.get("/pw-details")
        assert resp.status_code == 200


class TestMappedKeIdsReactomeBranch:
    """New reactome branch on /api/mapped-ke-ids."""

    def test_mapped_ke_ids_reactome_branch(self, client, monkeypatch):
        """GET /api/mapped-ke-ids?type=reactome returns 200 JSON with ke_ids list.

        Monkeypatches reactome_mapping_model to avoid a live DB dependency —
        mirrors the pattern used in tests/test_main_blueprint.py for metadata_manager.
        """
        mock_model = MagicMock()
        mock_model.get_mapped_ke_ids.return_value = ["KE 1", "KE 2"]
        monkeypatch.setattr(main_module, "reactome_mapping_model", mock_model)

        resp = client.get("/api/mapped-ke-ids?type=reactome")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None, "Response body must be valid JSON"
        assert "ke_ids" in data, f"Expected 'ke_ids' key in response, got: {list(data.keys())}"
        assert isinstance(data["ke_ids"], list), (
            f"Expected ke_ids to be a list, got {type(data['ke_ids'])}"
        )
        assert data.get("type") == "reactome", (
            f"Expected type == 'reactome', got {data.get('type')!r}"
        )


class TestApiAopOecdStatus:
    """New /api/aop-oecd-status endpoint."""

    def test_api_aop_oecd_status_200(self, client):
        """GET /api/aop-oecd-status returns 200 and a dict (empty or populated)."""
        resp = client.get("/api/aop-oecd-status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None, "Response body must be valid JSON"
        assert isinstance(data, dict), (
            f"Expected a JSON object (dict), got {type(data)}"
        )

    def test_api_aop_oecd_status_degrades_gracefully(self, client, monkeypatch):
        """When oecd_status_data is empty (file absent on CI), endpoint still returns 200 {}."""
        monkeypatch.setattr(main_module, "oecd_status_data", {})
        resp = client.get("/api/aop-oecd-status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == {}, f"Expected empty dict fallback, got: {data!r}"
