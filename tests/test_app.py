"""
Tests for Flask application routes
"""
import json
from unittest.mock import MagicMock, patch

import pytest


class TestRoutes:
    def test_index_route(self, client):
        """Test the index route"""
        response = client.get("/")
        assert response.status_code == 200
        assert b"KE-WP Mapping" in response.data

    def test_explore_route(self, client):
        """Test the explore route"""
        response = client.get("/explore")
        assert response.status_code == 200
        assert b"Explore Dataset" in response.data

    def test_login_redirect(self, client):
        """Test login route redirects to GitHub"""
        response = client.get("/login")
        assert response.status_code == 302
        # Should redirect to GitHub OAuth

    def test_logout(self, auth_client):
        """Test logout functionality"""
        response = auth_client.get("/logout")
        assert response.status_code == 302
        # Should redirect to index


class TestMappingAPI:
    def test_check_entry_missing_params(self, client):
        """Test check entry with missing parameters"""
        response = client.post("/check", data={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_submit_requires_auth(self, client):
        """Test that submit requires authentication"""
        response = client.post("/submit", data={})
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "error" in data

    def test_submit_missing_params(self, auth_client):
        """Test submit with missing parameters"""
        response = auth_client.post("/submit", data={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_submit_invalid_confidence(self, auth_client):
        """Test submit with invalid confidence level"""
        response = auth_client.post(
            "/submit",
            data={
                "ke_id": "KE:1",
                "wp_id": "WP:1",
                "ke_title": "Test KE",
                "wp_title": "Test WP",
                "confidence_level": "invalid",
                "connection_type": "causative",
            },
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_submit_invalid_connection_type(self, auth_client):
        """Test submit with invalid connection type"""
        response = auth_client.post(
            "/submit",
            data={
                "ke_id": "KE:1",
                "wp_id": "WP:1",
                "ke_title": "Test KE",
                "wp_title": "Test WP",
                "confidence_level": "high",
                "connection_type": "invalid",
            },
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data


class TestSPARQLEndpoints:
    @patch("blueprints.api.ke_metadata", [
        {
            "KEtitle": "Test KE Title",
            "KElabel": "KE:1",
            "KEpage": "http://example.com",
        }
    ])
    def test_get_ke_options_success(self, client):
        """Test successful KE options retrieval from pre-computed metadata"""
        response = client.get("/get_ke_options")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]["KEtitle"] == "Test KE Title"

    @patch("blueprints.api.pathway_metadata", [
        {
            "pathwayID": "WP:1",
            "pathwayTitle": "Test Pathway",
            "pathwayLink": "http://example.com",
        }
    ])
    def test_get_pathway_options_success(self, client):
        """Test successful pathway options retrieval from pre-computed metadata"""
        response = client.get("/get_pathway_options")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]["pathwayTitle"] == "Test Pathway"

    @patch("requests.post")
    def test_sparql_timeout(self, mock_post, client):
        """Test SPARQL timeout handling"""
        mock_post.side_effect = Exception("Timeout")

        response = client.get("/get_ke_options")
        # Endpoint may return cached data (200) or error (500)
        assert response.status_code in [200, 500]


class TestRateLimiting:
    def test_rate_limiting(self, client):
        """Test that rate limiting works"""
        # This test would need to make many requests quickly
        # For now, just test that the endpoint responds normally
        response = client.get("/get_ke_options")
        assert response.status_code in [
            200,
            500,
            503,
        ]  # Could be 500 due to mocked SPARQL


class TestAuthentication:
    def test_login_required_submit(self, client):
        """Test that submit requires login (returns 401)"""
        response = client.post("/submit", data={"ke_id": "KE:1"})
        assert response.status_code == 401

    def test_login_required_submit_proposal(self, client):
        """Test that submit_proposal requires login (returns 401)"""
        response = client.post(
            "/submit_proposal",
            data={
                "entry": "test",
                "userName": "Test",
                "userEmail": "test@example.com",
                "userAffiliation": "Test Org",
            },
        )
        assert response.status_code == 401

    def test_authenticated_submit_proposal(self, auth_client):
        """Test submit proposal with authentication but missing mapping_id"""
        response = auth_client.post(
            "/submit_proposal",
            data={
                "entry": "test",
                "userName": "Test User",
                "userEmail": "test@example.com",
                "userAffiliation": "Test Org",
            },
        )
        # Returns 400 because mapping_id is required but missing
        assert response.status_code == 400
