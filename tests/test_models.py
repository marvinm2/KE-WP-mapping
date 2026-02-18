"""
Tests for database models
"""
import os
import tempfile
from datetime import datetime, timedelta

import pytest

from src.core.models import CacheModel, Database, GuestCodeModel, MappingModel, ProposalModel


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
            created_by="testuser",
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
            proposed_confidence="high",
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

    def test_cache_expiry_clamped(self, cache_model):
        """Test that invalid expiry_hours is clamped to default (24h)"""
        endpoint = "test_endpoint"
        query_hash = "test_hash"
        response_data = '{"test": "data"}'

        # Negative expiry gets clamped to 24h, so entry should be retrievable
        success = cache_model.cache_response(
            endpoint, query_hash, response_data, -1
        )
        assert success is True

        # Entry is valid (clamped to 24h), so it should be found
        cached = cache_model.get_cached_response(endpoint, query_hash)
        assert cached == response_data

    def test_cleanup_expired_cache(self, cache_model):
        """Test cleanup of expired cache entries"""
        # This test would require time manipulation or database inspection
        # For now, just test that the method runs without error
        cache_model.cleanup_expired_cache()


class TestGuestCodeModel:
    @pytest.fixture
    def guest_code_model(self, test_db):
        return GuestCodeModel(test_db)

    def test_create_code(self, guest_code_model):
        """Test creating a guest access code"""
        expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        code = guest_code_model.create_code(
            label="test-workshop",
            created_by="admin",
            expires_at=expires,
            max_uses=5,
        )
        assert code is not None
        assert isinstance(code, str)
        assert len(code) > 0

    def test_validate_valid_code(self, guest_code_model):
        """Test validating a valid code"""
        expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        code = guest_code_model.create_code(
            label="valid-code",
            created_by="admin",
            expires_at=expires,
            max_uses=5,
        )

        result = guest_code_model.validate_code(code)
        assert result is not None
        assert result["label"] == "valid-code"

    def test_validate_expired_code(self, guest_code_model):
        """Test that expired codes are rejected"""
        expires = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        code = guest_code_model.create_code(
            label="expired-code",
            created_by="admin",
            expires_at=expires,
            max_uses=5,
        )

        result = guest_code_model.validate_code(code)
        assert result is None

    def test_validate_revoked_code(self, guest_code_model):
        """Test that revoked codes are rejected"""
        expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        code = guest_code_model.create_code(
            label="revoked-code",
            created_by="admin",
            expires_at=expires,
            max_uses=5,
        )

        # Get code ID from all codes
        all_codes = guest_code_model.get_all_codes()
        code_entry = [c for c in all_codes if c["code"] == code][0]

        guest_code_model.revoke_code(code_entry["id"], "admin")

        result = guest_code_model.validate_code(code)
        assert result is None

    def test_validate_exhausted_code(self, guest_code_model):
        """Test that exhausted codes are rejected"""
        expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        code = guest_code_model.create_code(
            label="single-use",
            created_by="admin",
            expires_at=expires,
            max_uses=1,
        )

        # First use should succeed
        result = guest_code_model.validate_code(code)
        assert result is not None

        # Second use should fail
        result = guest_code_model.validate_code(code)
        assert result is None

    def test_revoke_code(self, guest_code_model):
        """Test revoking a code"""
        expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        code = guest_code_model.create_code(
            label="to-revoke",
            created_by="admin",
            expires_at=expires,
        )

        all_codes = guest_code_model.get_all_codes()
        code_entry = [c for c in all_codes if c["code"] == code][0]

        success = guest_code_model.revoke_code(code_entry["id"], "admin")
        assert success is True

        # Verify status
        all_codes = guest_code_model.get_all_codes()
        code_entry = [c for c in all_codes if c["code"] == code][0]
        assert code_entry["status"] == "revoked"

    def test_get_all_codes_with_status(self, guest_code_model):
        """Test that get_all_codes computes status correctly"""
        # Active code
        active_expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        guest_code_model.create_code(
            label="active-code",
            created_by="admin",
            expires_at=active_expires,
        )

        # Expired code
        expired_expires = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        guest_code_model.create_code(
            label="expired-code2",
            created_by="admin",
            expires_at=expired_expires,
        )

        codes = guest_code_model.get_all_codes()
        assert len(codes) == 2

        statuses = {c["label"]: c["status"] for c in codes}
        assert statuses["active-code"] == "active"
        assert statuses["expired-code2"] == "expired"
