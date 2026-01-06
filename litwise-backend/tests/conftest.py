"""
Pytest configuration and fixtures for Litwise Backend Tests
"""
import pytest
import os
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@pytest.fixture(scope="session")
def app():
    """Import and return FastAPI app"""
    # Suppress warnings during test import
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    from app import app as fastapi_app
    return fastapi_app

@pytest.fixture(scope="session")
def client(app):
    """Create test client for FastAPI app"""
    return TestClient(app)

@pytest.fixture
def test_headers():
    """Return test headers with valid JWT token"""
    # Using a test token from environment or hardcoded test token
    token = os.getenv("TEST_JWT_TOKEN", "test-token-placeholder")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

@pytest.fixture
def test_user_id():
    """Return test user ID"""
    return os.getenv("TEST_USER_ID", "test-user-123")

@pytest.fixture
def test_session_id():
    """Return test session ID"""
    return "test-session-" + str(os.getenv("TEST_SESSION_ID", "123"))
