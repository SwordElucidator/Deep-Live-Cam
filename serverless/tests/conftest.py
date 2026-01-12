"""
Pytest configuration and fixtures
"""

import os
import sys
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set test environment variables
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("MODELS_DIR", "/tmp/models")
os.environ.setdefault("TEMP_DIR", "/tmp/test_jobs")
os.environ.setdefault("LOG_LEVEL", "DEBUG")


@pytest.fixture(scope="session")
def test_data_dir():
    """Get test data directory"""
    return os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory"""
    return tmp_path


@pytest.fixture
def mock_env(monkeypatch):
    """Fixture to set environment variables"""
    def _set_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key, value)
    return _set_env
