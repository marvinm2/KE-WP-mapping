"""
Test configuration and fixtures
"""
import pytest
import os
import tempfile
from app import app
from models import Database

@pytest.fixture
def client():
    """Create a test client"""
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    # Configure app for testing
    app.config['TESTING'] = True
    app.config['DATABASE_PATH'] = db_path
    
    with app.test_client() as client:
        with app.app_context():
            # Initialize test database
            test_db = Database(db_path)
            yield client
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def auth_client(client):
    """Create an authenticated test client"""
    with client.session_transaction() as sess:
        sess['user'] = {
            'username': 'testuser',
            'email': 'test@example.com'
        }
    return client