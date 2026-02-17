"""
Test configuration and fixtures
"""
import os
import tempfile

import pytest

from app import app
from src.core.models import Database


@pytest.fixture
def client():
    """Create a test client"""
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()

    # Set up environment variables for testing
    os.environ["FLASK_SECRET_KEY"] = "test-secret-key"
    os.environ["GITHUB_CLIENT_ID"] = "dummy"
    os.environ["GITHUB_CLIENT_SECRET"] = "dummy"
    os.environ["ADMIN_USERS"] = "testuser"
    os.environ["DATABASE_PATH"] = db_path

    # Configure app for testing
    app.config["TESTING"] = True
    app.config["DATABASE_PATH"] = db_path
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

    with app.test_client() as client:
        with app.app_context():
            # Initialize test database
            test_db = Database(db_path)
            # Initialize database tables
            test_db.init_db()
            yield client

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def auth_client(client):
    """Create an authenticated test client"""
    with client.session_transaction() as sess:
        sess["user"] = {"username": "testuser", "email": "test@example.com"}
    return client
