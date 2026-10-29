"""House storage contract and lifecycle tests."""

import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import ApiSettings
from king_county.house_records.repository import HouseRepository

HOUSE = {
    "bedrooms": 3,
    "bathrooms": 1.5,
    "sqft_living": 1200,
    "grade": 7,
    "zipcode": "98101",
}


@pytest.fixture
def created_house(client):
    """Create and return one house for independent request tests."""
    response = client.post("/houses", json=HOUSE)
    assert response.status_code == 201
    return response.json()


@pytest.mark.contract
def test_create_and_read(client, created_house):
    """Creation returns the assigned ID and the record can be read."""
    assert created_house == {"id": 1, **HOUSE}
    assert client.get("/houses/1").json() == created_house


@pytest.mark.contract
def test_replace(client, created_house):
    """PUT replaces all fields and returns the stored record."""
    replacement = {**HOUSE, "bedrooms": 4}
    response = client.put("/houses/1", json=replacement)
    assert response.status_code == 200
    assert response.json() == {"id": 1, **replacement}
    assert client.get("/houses/1").json() == response.json()


@pytest.mark.contract
def test_delete(client, created_house):
    """DELETE returns no content and removes the record."""
    response = client.delete("/houses/1")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/houses/1").status_code == 404


@pytest.mark.contract
@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_house(client, method):
    """Each operation on an unknown valid ID returns 404."""
    response = getattr(client, method)(
        "/houses/1", **({"json": HOUSE} if method == "put" else {})
    )
    assert response.status_code == 404


@pytest.mark.contract
def test_extra_field(client):
    """Unknown fields are rejected."""
    assert client.post("/houses", json={**HOUSE, "extra": 1}).status_code == 422


@pytest.mark.contract
def test_invalid_replace_is_atomic(client, created_house):
    """A rejected replacement leaves the original record unchanged."""
    assert client.put("/houses/1", json={**HOUSE, "grade": 14}).status_code == 422
    assert client.get("/houses/1").json() == created_house


@pytest.mark.contract
def test_duplicate_keys_rejected(client):
    """The raw-key validator also protects the house endpoint."""
    response = client.post(
        "/houses",
        content='{"bedrooms":1,"bedrooms":2}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422


@pytest.mark.contract
@pytest.mark.parametrize(
    "url",
    [
        "/houses/0",
        "/houses/-1",
        f"/houses/{2**63}",
        "/houses?limit=101",
        "/houses?limit=0",
        "/houses?offset=-1",
        f"/houses?offset={2**63}",
    ],
)
def test_invalid_id_and_page_bounds(client, url):
    """IDs and pagination are bounded before the database is queried."""
    assert client.get(url).status_code == 422


@pytest.mark.contract
def test_valid_id_and_page_upper_bounds(client):
    """The largest supported ID and offset are accepted without overflow."""
    assert client.get(f"/houses/{2**63 - 1}").status_code == 404
    response = client.get(f"/houses?offset={2**63 - 1}&limit=100")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.contract
def test_pagination(client, created_house):
    """Pages are ordered by ID and respect limit and offset."""
    client.post("/houses", json=HOUSE)
    client.post("/houses", json=HOUSE)
    assert [h["id"] for h in client.get("/houses?limit=1&offset=1").json()] == [2]
    assert len(client.get("/houses?limit=100&offset=0").json()) == 3
    assert client.get("/houses?offset=3").json() == []


@pytest.mark.integration
def test_restart_persists(approved_artifact, tmp_path):
    """A new application instance reads records from the same database."""
    settings = ApiSettings(
        model_path=approved_artifact.path, database_path=tmp_path / "house.db"
    )
    with TestClient(create_app(settings)) as client:
        assert client.post("/houses", json=HOUSE).status_code == 201
    with TestClient(create_app(settings)) as client:
        assert client.get("/houses/1").json() == {"id": 1, **HOUSE}


@pytest.mark.integration
def test_database_failure_response_is_safe(client):
    """A runtime database error returns no internal details."""
    with patch.object(
        HouseRepository, "list", side_effect=sqlite3.OperationalError("secret")
    ):
        response = client.get("/houses")
    assert response.status_code == 500
    assert response.json() == {"detail": "House storage unavailable."}


@pytest.mark.integration
def test_unavailable_database_prevents_startup(approved_artifact, tmp_path):
    """An invalid database path fails startup rather than reporting ready."""
    settings = ApiSettings(
        model_path=approved_artifact.path,
        database_path=tmp_path / "missing" / "house.db",
    )
    with pytest.raises(sqlite3.OperationalError), TestClient(create_app(settings)):
        pass
