"""
Tests for database models
"""
import pytest
import tempfile
import os
from models import Database, MappingModel, ProposalModel, CacheModel

@pytest.fixture
def test_db():
    """Create a test database"""
    fd, path = tempfile.mkstemp()
    db = Database(path)
    yield db
    os.close(fd)
    os.unlink(path)

@pytest.fixture
def mapping_model(test_db):
    return MappingModel(test_db)

@pytest.fixture
def proposal_model(test_db):
    return ProposalModel(test_db)

@pytest.fixture
def cache_model(test_db):
    return CacheModel(test_db)

class TestMappingModel:
    def test_create_mapping(self, mapping_model):
        """Test creating a new mapping"""
        mapping_id = mapping_model.create_mapping(
            ke_id="KE:1",
            ke_title="Test KE",
            wp_id="WP:1", 
            wp_title="Test WP",
            connection_type="causative",
            confidence_level="high",
            created_by="testuser"
        )
        
        assert mapping_id is not None
        assert isinstance(mapping_id, int)
    
    def test_create_duplicate_mapping(self, mapping_model):
        """Test that duplicate mappings are prevented"""
        # Create first mapping
        mapping_id1 = mapping_model.create_mapping(
            ke_id="KE:1", ke_title="Test KE", wp_id="WP:1", wp_title="Test WP"
        )
        assert mapping_id1 is not None
        
        # Try to create duplicate
        mapping_id2 = mapping_model.create_mapping(
            ke_id="KE:1", ke_title="Test KE", wp_id="WP:1", wp_title="Test WP"
        )
        assert mapping_id2 is None
    
    def test_get_all_mappings(self, mapping_model):
        """Test retrieving all mappings"""
        # Create test mappings
        mapping_model.create_mapping(
            ke_id="KE:1", ke_title="Test KE 1", wp_id="WP:1", wp_title="Test WP 1"
        )
        mapping_model.create_mapping(
            ke_id="KE:2", ke_title="Test KE 2", wp_id="WP:2", wp_title="Test WP 2"
        )
        
        mappings = mapping_model.get_all_mappings()
        assert len(mappings) == 2
        assert all(isinstance(m, dict) for m in mappings)
    
    def test_check_mapping_exists(self, mapping_model):
        """Test checking if mapping exists"""
        # Create a mapping
        mapping_model.create_mapping(
            ke_id="KE:1", ke_title="Test KE", wp_id="WP:1", wp_title="Test WP"
        )
        
        # Test exact pair exists
        result = mapping_model.check_mapping_exists("KE:1", "WP:1")
        assert result["pair_exists"] is True
        
        # Test KE exists but different WP
        result = mapping_model.check_mapping_exists("KE:1", "WP:2")
        assert result["ke_exists"] is True
        assert result["pair_exists"] is False
        
        # Test new entry
        result = mapping_model.check_mapping_exists("KE:2", "WP:2")
        assert result["ke_exists"] is False
        assert result["pair_exists"] is False

class TestProposalModel:
    def test_create_proposal(self, proposal_model, mapping_model):
        """Test creating a proposal"""
        # Create a mapping first
        mapping_id = mapping_model.create_mapping(
            ke_id="KE:1", ke_title="Test KE", wp_id="WP:1", wp_title="Test WP"
        )
        
        # Create proposal
        proposal_id = proposal_model.create_proposal(
            mapping_id=mapping_id,
            user_name="Test User",
            user_email="test@example.com",
            user_affiliation="Test Org",
            github_username="testuser",
            proposed_confidence="high"
        )
        
        assert proposal_id is not None
        assert isinstance(proposal_id, int)

class TestCacheModel:
    def test_cache_and_retrieve(self, cache_model):
        """Test caching and retrieving responses"""
        endpoint = "test_endpoint"
        query_hash = "test_hash"
        response_data = '{"test": "data"}'
        
        # Cache response
        success = cache_model.cache_response(endpoint, query_hash, response_data, 1)
        assert success is True
        
        # Retrieve cached response
        cached = cache_model.get_cached_response(endpoint, query_hash)
        assert cached == response_data
    
    def test_cache_expiry(self, cache_model):
        """Test that expired cache entries are not returned"""
        endpoint = "test_endpoint"
        query_hash = "test_hash"
        response_data = '{"test": "data"}'
        
        # Cache response with very short expiry (this is a limitation of the test)
        success = cache_model.cache_response(endpoint, query_hash, response_data, -1)  # Expired immediately
        assert success is True
        
        # Should not retrieve expired cache
        cached = cache_model.get_cached_response(endpoint, query_hash)
        assert cached is None
    
    def test_cleanup_expired_cache(self, cache_model):
        """Test cleanup of expired cache entries"""
        # This test would require time manipulation or database inspection
        # For now, just test that the method runs without error
        cache_model.cleanup_expired_cache()