import pytest
import os
import sys
from fastapi.testclient import TestClient
from pymongo import MongoClient
from unittest.mock import patch

# Add src to path - use absolute path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), 'src')
sys.path.insert(0, src_dir)

@pytest.fixture
def test_db():
    """Setup test database and cleanup after tests."""
    # Use test database
    test_uri = "mongodb://localhost:27017/"
    test_db_name = "clarityGR_test"
    
    client = MongoClient(test_uri)
    db = client[test_db_name]
    
    # Clean up before test
    db.reports.delete_many({})
    
    yield db
    
    # Clean up after test
    db.reports.delete_many({})
    client.close()

@pytest.fixture
def client(test_db):
    """Create test client with test database."""
    # Set environment variables for test database
    test_env = {
        "MONGODB_URI": "mongodb://localhost:27017/",
        "MONGODB_DB": "clarityGR_test"
    }
    
    with patch.dict(os.environ, test_env, clear=False):
        import importlib
        import src.config.settings
        importlib.reload(src.config.settings)
        
        from src.main import app
        with TestClient(app) as test_client:
            yield test_client 