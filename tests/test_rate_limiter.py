"""
Tests for rate limiting functionality
"""
import pytest
import tempfile
import os
import time
from rate_limiter import RateLimiter

@pytest.fixture
def rate_limiter():
    """Create a test rate limiter with temporary database"""
    fd, path = tempfile.mkstemp()
    limiter = RateLimiter(path)
    yield limiter
    os.close(fd)
    os.unlink(path)

class TestRateLimiter:
    def test_rate_limiter_allows_initial_requests(self, rate_limiter):
        """Test that initial requests are allowed"""
        client_ip = "192.168.1.1"
        endpoint = "test_endpoint"
        
        # Should not be rate limited initially
        assert not rate_limiter.is_rate_limited(client_ip, endpoint, limit=5, window=60)
    
    def test_rate_limiter_blocks_excessive_requests(self, rate_limiter):
        """Test that excessive requests are blocked"""
        client_ip = "192.168.1.1"
        endpoint = "test_endpoint"
        limit = 3
        window = 60
        
        # Make requests up to the limit
        for i in range(limit):
            assert not rate_limiter.is_rate_limited(client_ip, endpoint, limit, window)
        
        # Next request should be blocked
        assert rate_limiter.is_rate_limited(client_ip, endpoint, limit, window)
    
    def test_rate_limiter_different_ips(self, rate_limiter):
        """Test that different IPs are tracked separately"""
        endpoint = "test_endpoint"
        limit = 2
        window = 60
        
        # Fill up limit for first IP
        for i in range(limit):
            assert not rate_limiter.is_rate_limited("192.168.1.1", endpoint, limit, window)
        
        # First IP should now be blocked
        assert rate_limiter.is_rate_limited("192.168.1.1", endpoint, limit, window)
        
        # Second IP should still be allowed
        assert not rate_limiter.is_rate_limited("192.168.1.2", endpoint, limit, window)
    
    def test_rate_limiter_different_endpoints(self, rate_limiter):
        """Test that different endpoints are tracked separately"""
        client_ip = "192.168.1.1"
        limit = 2
        window = 60
        
        # Fill up limit for first endpoint
        for i in range(limit):
            assert not rate_limiter.is_rate_limited(client_ip, "endpoint1", limit, window)
        
        # First endpoint should now be blocked
        assert rate_limiter.is_rate_limited(client_ip, "endpoint1", limit, window)
        
        # Second endpoint should still be allowed
        assert not rate_limiter.is_rate_limited(client_ip, "endpoint2", limit, window)
    
    def test_rate_limiter_window_expiry(self, rate_limiter):
        """Test that rate limit window expires"""
        client_ip = "192.168.1.1"
        endpoint = "test_endpoint"
        limit = 2
        window = 1  # 1 second window
        
        # Fill up the limit
        for i in range(limit):
            assert not rate_limiter.is_rate_limited(client_ip, endpoint, limit, window)
        
        # Should be blocked
        assert rate_limiter.is_rate_limited(client_ip, endpoint, limit, window)
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        assert not rate_limiter.is_rate_limited(client_ip, endpoint, limit, window)
    
    def test_memory_fallback(self, rate_limiter):
        """Test memory fallback when database fails"""
        # Force database error by closing the connection
        client_ip = "192.168.1.1"
        endpoint = "test_endpoint"
        limit = 2
        window = 60
        
        # Simulate database error by using invalid path
        broken_limiter = RateLimiter("/invalid/path/that/does/not/exist")
        
        # Should still work with memory fallback
        assert not broken_limiter.is_rate_limited(client_ip, endpoint, limit, window)
        assert not broken_limiter.is_rate_limited(client_ip, endpoint, limit, window)
        assert broken_limiter.is_rate_limited(client_ip, endpoint, limit, window)  # Third should be blocked