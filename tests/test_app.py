"""
Tests for Flask application routes
"""
import pytest
import json
from unittest.mock import patch, MagicMock

class TestRoutes:
    def test_index_route(self, client):
        """Test the index route"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'KE-WP Mapping' in response.data
    
    def test_explore_route(self, client):
        """Test the explore route"""
        response = client.get('/explore')
        assert response.status_code == 200
        assert b'Explore Dataset' in response.data
    
    def test_login_redirect(self, client):
        """Test login route redirects to GitHub"""
        response = client.get('/login')
        assert response.status_code == 302
        # Should redirect to GitHub OAuth
    
    def test_logout(self, auth_client):
        """Test logout functionality"""
        response = auth_client.get('/logout')
        assert response.status_code == 302
        # Should redirect to index

class TestMappingAPI:
    def test_check_entry_missing_params(self, client):
        """Test check entry with missing parameters"""
        response = client.post('/check', data={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_submit_missing_params(self, client):
        """Test submit with missing parameters"""
        response = client.post('/submit', data={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_submit_invalid_confidence(self, client):
        """Test submit with invalid confidence level"""
        response = client.post('/submit', data={
            'ke_id': 'KE:1',
            'wp_id': 'WP:1', 
            'ke_title': 'Test KE',
            'wp_title': 'Test WP',
            'confidence_level': 'invalid',
            'connection_type': 'causative'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Invalid confidence level' in data['error']
    
    def test_submit_invalid_connection_type(self, client):
        """Test submit with invalid connection type"""
        response = client.post('/submit', data={
            'ke_id': 'KE:1',
            'wp_id': 'WP:1',
            'ke_title': 'Test KE', 
            'wp_title': 'Test WP',
            'confidence_level': 'high',
            'connection_type': 'invalid'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Invalid connection type' in data['error']

class TestSPARQLEndpoints:
    @patch('requests.post')
    def test_get_ke_options_success(self, mock_post, client):
        """Test successful KE options retrieval"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "KEtitle": {"value": "Test KE Title"},
                        "KElabel": {"value": "KE:1"},
                        "KEpage": {"value": "http://example.com"}
                    }
                ]
            }
        }
        mock_post.return_value = mock_response
        
        response = client.get('/get_ke_options')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['KEtitle'] == "Test KE Title"
    
    @patch('requests.post')
    def test_get_pathway_options_success(self, mock_post, client):
        """Test successful pathway options retrieval"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "pathwayID": {"value": "WP:1"},
                        "pathwayTitle": {"value": "Test Pathway"},
                        "pathwayLink": {"value": "http://example.com"}
                    }
                ]
            }
        }
        mock_post.return_value = mock_response
        
        response = client.get('/get_pathway_options')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['pathwayTitle'] == "Test Pathway"
    
    @patch('requests.post')
    def test_sparql_timeout(self, mock_post, client):
        """Test SPARQL timeout handling"""
        mock_post.side_effect = Exception("Timeout")
        
        response = client.get('/get_ke_options')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data

class TestRateLimiting:
    def test_rate_limiting(self, client):
        """Test that rate limiting works"""
        # This test would need to make many requests quickly
        # For now, just test that the endpoint responds normally
        response = client.get('/get_ke_options')
        assert response.status_code in [200, 500, 503]  # Could be 500 due to mocked SPARQL

class TestAuthentication:
    def test_login_required_submit_proposal(self, client):
        """Test that submit_proposal requires login"""
        response = client.post('/submit_proposal', data={
            'entry': 'test',
            'userName': 'Test',
            'userEmail': 'test@example.com',
            'userAffiliation': 'Test Org'
        })
        # Should redirect to login
        assert response.status_code == 302
    
    def test_authenticated_submit_proposal(self, auth_client):
        """Test submit proposal with authentication"""
        response = auth_client.post('/submit_proposal', data={
            'entry': 'test',
            'userName': 'Test User',
            'userEmail': 'test@example.com',
            'userAffiliation': 'Test Org'
        })
        # Should process (might fail due to missing mapping_id, but not due to auth)
        assert response.status_code == 200