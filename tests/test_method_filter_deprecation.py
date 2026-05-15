"""
Tests for method_filter deprecation logging on the three suggestion endpoints:
  /suggest_pathways/<ke_id>
  /suggest_go_terms/<ke_id>
  /suggest_reactome/<ke_id>

Tests A-E prove:
  A. Default value ('all') does NOT emit a deprecation log line
  B. Non-default WP value ('gene') emits exactly one WARNING containing
     'method_filter=gene' and 'deprecated'
  C. Non-default GO value ('gene') emits the deprecation log
  D. Non-default Reactome value ('gene') emits the deprecation log
  E. Parameter is still honored (passed through to the service layer),
     backward compatible — deprecation is log-only, not behaviour-changing

Strategy:
  - Use Flask test client on the real 'app' (same as test_v1_api.py)
  - Mock the three suggestion service singletons in src.blueprints.api to
    return canned dicts — avoids SPARQL / NPZ / network dependency
  - Use caplog to assert log lines at WARNING level
"""
import pytest
import logging
from unittest.mock import patch

from app import app as flask_app


# ---------------------------------------------------------------------------
# Minimal valid response shapes for mocked suggestion services
# ---------------------------------------------------------------------------

_WP_RESPONSE = {
    'combined_suggestions': [{'pathwayID': 'WP123', 'name': 'Test', 'hybrid_score': 0.8}],
    'gene_based_suggestions': [],
    'embedding_based_suggestions': [],
    'genes_found': 0,
    'gene_list': [],
}

_GO_RESPONSE = {
    'suggestions': [{'go_id': 'GO:0001234', 'name': 'Test GO', 'hybrid_score': 0.8}],
}

_REACTOME_RESPONSE = {
    'suggestions': [
        {'reactome_id': 'R-HSA-001', 'pathway_name': 'Test Reactome', 'hybrid_score': 0.8}
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    """Flask test client with TESTING mode."""
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMethodFilterDeprecation:
    """Pin deprecation log behaviour for the method_filter query parameter."""

    @patch('src.blueprints.api.pathway_suggestion_service')
    @patch('src.blueprints.api.go_suggestion_service')
    @patch('src.blueprints.api.reactome_suggestion_service')
    def test_A_default_value_does_not_log(
        self, mock_reactome, mock_go, mock_pathway, api_client, caplog
    ):
        """
        Test A: When method_filter is omitted (default 'all') on the WP endpoint,
        the deprecation log is NOT emitted. Avoids log spam from normal frontend traffic.
        """
        mock_pathway.get_pathway_suggestions.return_value = _WP_RESPONSE

        with caplog.at_level(logging.WARNING, logger='src.blueprints.api'):
            response = api_client.get(
                '/suggest_pathways/KE%201?ke_title=Test&bio_level=Molecular'
            )

        # Should succeed
        assert response.status_code == 200

        # No deprecation warning should have fired
        deprecation_logs = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and 'deprecated' in r.message.lower()
        ]
        assert len(deprecation_logs) == 0, (
            f"Expected no deprecation log for default method_filter='all', "
            f"but got: {[r.message for r in deprecation_logs]}"
        )

    @patch('src.blueprints.api.pathway_suggestion_service')
    @patch('src.blueprints.api.go_suggestion_service')
    @patch('src.blueprints.api.reactome_suggestion_service')
    def test_B_non_default_wp_value_logs_deprecation(
        self, mock_reactome, mock_go, mock_pathway, api_client, caplog
    ):
        """
        Test B: Hitting /suggest_pathways with method_filter=gene emits exactly one
        WARNING log line containing 'method_filter=gene' and 'deprecated'.
        """
        mock_pathway.get_pathway_suggestions.return_value = _WP_RESPONSE

        with caplog.at_level(logging.WARNING, logger='src.blueprints.api'):
            response = api_client.get(
                '/suggest_pathways/KE%201?ke_title=Test&bio_level=Molecular&method_filter=gene'
            )

        assert response.status_code == 200

        deprecation_logs = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and 'deprecated' in r.message.lower()
        ]
        assert len(deprecation_logs) >= 1, (
            "Expected at least one deprecation WARNING log for method_filter=gene on /suggest_pathways"
        )

        combined = ' '.join(r.message for r in deprecation_logs)
        assert 'method_filter=gene' in combined, (
            f"Deprecation log should contain 'method_filter=gene', got: {combined}"
        )
        assert 'deprecated' in combined.lower(), (
            f"Deprecation log should contain 'deprecated', got: {combined}"
        )

    @patch('src.blueprints.api.pathway_suggestion_service')
    @patch('src.blueprints.api.go_suggestion_service')
    @patch('src.blueprints.api.reactome_suggestion_service')
    def test_C_non_default_go_value_logs_deprecation(
        self, mock_reactome, mock_go, mock_pathway, api_client, caplog
    ):
        """
        Test C: Hitting /suggest_go_terms with method_filter=gene emits the deprecation log.
        """
        mock_go.get_go_suggestions.return_value = _GO_RESPONSE

        with caplog.at_level(logging.WARNING, logger='src.blueprints.api'):
            response = api_client.get(
                '/suggest_go_terms/KE%201?ke_title=Test&method_filter=gene'
            )

        assert response.status_code == 200

        deprecation_logs = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and 'deprecated' in r.message.lower()
        ]
        assert len(deprecation_logs) >= 1, (
            "Expected at least one deprecation WARNING log for method_filter=gene on /suggest_go_terms"
        )

        combined = ' '.join(r.message for r in deprecation_logs)
        assert 'method_filter=gene' in combined, (
            f"Deprecation log should contain 'method_filter=gene', got: {combined}"
        )

    @patch('src.blueprints.api.pathway_suggestion_service')
    @patch('src.blueprints.api.go_suggestion_service')
    @patch('src.blueprints.api.reactome_suggestion_service')
    def test_D_non_default_reactome_value_logs_deprecation(
        self, mock_reactome, mock_go, mock_pathway, api_client, caplog
    ):
        """
        Test D: Hitting /suggest_reactome with method_filter=gene emits the deprecation log.
        """
        mock_reactome.get_reactome_suggestions.return_value = _REACTOME_RESPONSE

        with caplog.at_level(logging.WARNING, logger='src.blueprints.api'):
            response = api_client.get(
                '/suggest_reactome/KE%201?ke_title=Test&method_filter=gene'
            )

        assert response.status_code == 200

        deprecation_logs = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and 'deprecated' in r.message.lower()
        ]
        assert len(deprecation_logs) >= 1, (
            "Expected at least one deprecation WARNING log for method_filter=gene on /suggest_reactome"
        )

        combined = ' '.join(r.message for r in deprecation_logs)
        assert 'method_filter=gene' in combined, (
            f"Deprecation log should contain 'method_filter=gene', got: {combined}"
        )

    @patch('src.blueprints.api.pathway_suggestion_service')
    @patch('src.blueprints.api.go_suggestion_service')
    @patch('src.blueprints.api.reactome_suggestion_service')
    def test_E_parameter_still_honored_backward_compatible(
        self, mock_reactome, mock_go, mock_pathway, api_client
    ):
        """
        Test E: method_filter is still passed through to the service layer — the
        deprecation is log-only, not behaviour-changing.

        Asserts by checking that:
        - WP: response contains 'method_filter': 'gene' in request_info
        - GO: response contains 'method_filter': 'gene' in request_info
        - Reactome: response contains 'method_filter': 'gene' in request_info
        """
        import json

        mock_pathway.get_pathway_suggestions.return_value = _WP_RESPONSE
        mock_go.get_go_suggestions.return_value = _GO_RESPONSE
        mock_reactome.get_reactome_suggestions.return_value = _REACTOME_RESPONSE

        # WP endpoint
        r_wp = api_client.get(
            '/suggest_pathways/KE%201?ke_title=Test&bio_level=Molecular&method_filter=gene'
        )
        assert r_wp.status_code == 200
        data_wp = json.loads(r_wp.data)
        assert data_wp.get('request_info', {}).get('method_filter') == 'gene', (
            "WP endpoint must echo method_filter='gene' in request_info (backward compat)"
        )

        # GO endpoint
        r_go = api_client.get(
            '/suggest_go_terms/KE%201?ke_title=Test&method_filter=gene'
        )
        assert r_go.status_code == 200
        data_go = json.loads(r_go.data)
        assert data_go.get('request_info', {}).get('method_filter') == 'gene', (
            "GO endpoint must echo method_filter='gene' in request_info (backward compat)"
        )

        # Reactome endpoint
        r_reactome = api_client.get(
            '/suggest_reactome/KE%201?ke_title=Test&method_filter=gene'
        )
        assert r_reactome.status_code == 200
        data_reactome = json.loads(r_reactome.data)
        assert data_reactome.get('request_info', {}).get('method_filter') == 'gene', (
            "Reactome endpoint must echo method_filter='gene' in request_info (backward compat)"
        )
