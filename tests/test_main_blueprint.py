"""
Regression tests for Phase 33-01 baseline cleanup of src/blueprints/main.py.

Locks two contracts:

  - CLEAN-01: GET /confidence_assessment returns 404 (route fully removed;
              Flask's default 404 handler responds).
  - CLEAN-02: GET /dataset/{metadata,versions,citation,datacite} returns
              HTTP 503 with parity body
                  {"error": "dataset metadata not configured",
                   "reason": "metadata_manager unavailable"}
              when the blueprint-level metadata_manager global is None.

The 503 body shape mirrors the empty-graph 503 contract established for
Reactome RDF (Phase 25), WP RDF (Phase 32-05), and GO RDF (Phase 32-06),
giving downstream API consumers consistent "not configured / no data"
semantics across the suite.

Tests monkeypatch the blueprint-module global directly (per the
tests/test_reactome_exports.py pattern) because the client fixture's
temp-DB rebind does not reach blueprint-bound globals set once at
create_app() time.
"""
import src.blueprints.main as main_module


UNCONFIGURED_BODY = {
    "error": "dataset metadata not configured",
    "reason": "metadata_manager unavailable",
}


class TestBaselineCleanup:
    """Phase 33-01 contract regression tests."""

    def test_confidence_assessment_returns_404(self, client):
        """Dead route must be gone; Flask default 404 takes over."""
        resp = client.get("/confidence_assessment")
        assert resp.status_code == 404

    def test_dataset_metadata_returns_503_when_unconfigured(self, client, monkeypatch):
        monkeypatch.setattr(main_module, "metadata_manager", None)
        resp = client.get("/dataset/metadata")
        assert resp.status_code == 503
        assert resp.get_json() == UNCONFIGURED_BODY

    def test_dataset_versions_returns_503_when_unconfigured(self, client, monkeypatch):
        monkeypatch.setattr(main_module, "metadata_manager", None)
        resp = client.get("/dataset/versions")
        assert resp.status_code == 503
        assert resp.get_json() == UNCONFIGURED_BODY

    def test_dataset_citation_returns_503_when_unconfigured(self, client, monkeypatch):
        monkeypatch.setattr(main_module, "metadata_manager", None)
        resp = client.get("/dataset/citation")
        assert resp.status_code == 503
        assert resp.get_json() == UNCONFIGURED_BODY

    def test_dataset_datacite_returns_503_when_unconfigured(self, client, monkeypatch):
        monkeypatch.setattr(main_module, "metadata_manager", None)
        resp = client.get("/dataset/datacite")
        assert resp.status_code == 503
        assert resp.get_json() == UNCONFIGURED_BODY
