"""Share the real app lifecycle and temporary approved model across API tests."""

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import ApiSettings


@pytest.fixture
def client(approved_artifact):
    """Yield a started test client; shut down its app after each test."""
    with TestClient(
        create_app(ApiSettings(model_path=approved_artifact.path))
    ) as client:
        yield client
