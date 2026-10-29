"""Authentication is optional locally and mandatory in cloud mode."""

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import ApiSettings

pytestmark = pytest.mark.integration
TEST_TOKEN = "a" * 32
HOUSE = {
    "bedrooms": 3,
    "bathrooms": 1.5,
    "sqft_living": 1200,
    "grade": 7,
    "zipcode": "98101",
}


@pytest.fixture
def cloud_client(approved_artifact, tmp_path):
    """Start a token-protected API with an isolated database."""
    settings = ApiSettings(
        model_path=approved_artifact.path,
        database_path=tmp_path / "houses.db",
        mode="cloud",
        api_token=TEST_TOKEN,
    )
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/houses"),
        ("POST", "/houses"),
        ("PUT", "/houses/1"),
        ("DELETE", "/houses/1"),
    ],
)
def test_cloud_protects_house_routes_without_mutation(cloud_client, method, path):
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    created = cloud_client.post("/houses", json=HOUSE, headers=headers)
    assert created.status_code == 201
    response = cloud_client.request(method, path, json={**HOUSE, "bedrooms": 4})
    assert response.status_code == 401
    assert cloud_client.get("/houses", headers=headers).json() == [created.json()]


@pytest.mark.parametrize(
    "header",
    [
        None,
        "Bearer wrong",
        "Basic token",
        "Bearer",
        "Bearer token extra",
    ],
)
def test_cloud_rejects_bad_credentials(
    approved_artifact, house_payload, header, tmp_path
):
    app = create_app(
        ApiSettings(
            model_path=approved_artifact.path,
            database_path=tmp_path / "houses.db",
            mode="cloud",
            api_token=TEST_TOKEN,
        )
    )
    headers = {"Authorization": header} if header else {}
    with TestClient(app) as client:
        response = client.post("/predict", json=house_payload, headers=headers)
        assert response.status_code == 401
        assert response.json() == {"detail": "Unauthorized"}
        assert response.headers["www-authenticate"] == "Bearer"
        assert client.get("/health").json() == {"status": "ready"}
        assert client.post("/predict", content="{bad").status_code == 401
        assert client.get("/houses").status_code == 401


def test_correct_token_and_whitespace(approved_artifact, house_payload, tmp_path):
    app = create_app(
        ApiSettings(
            model_path=approved_artifact.path,
            database_path=tmp_path / "houses.db",
            mode="cloud",
            api_token=TEST_TOKEN,
        )
    )
    with TestClient(app) as client:
        assert (
            client.post(
                "/predict",
                json=house_payload,
                headers={"Authorization": f"bearer   {TEST_TOKEN}"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/predict",
                json=house_payload,
                headers=[
                    ("Authorization", f"Bearer {TEST_TOKEN}"),
                    ("Authorization", f"Bearer {TEST_TOKEN}"),
                ],
            ).status_code
            == 401
        )
        assert client.get("/openapi.json").status_code == 401
        assert (
            client.get(
                "/houses", headers={"Authorization": f"Bearer {TEST_TOKEN}"}
            ).status_code
            == 200
        )
        assert (
            TEST_TOKEN
            not in client.get(
                "/openapi.json", headers={"Authorization": f"Bearer {TEST_TOKEN}"}
            ).text
        )


def test_token_can_protect_local_mode(approved_artifact, house_payload, tmp_path):
    app = create_app(
        ApiSettings(
            model_path=approved_artifact.path,
            database_path=tmp_path / "houses.db",
            api_token="token",
        )
    )
    with TestClient(app) as client:
        assert client.post("/predict", json=house_payload).status_code == 401
        assert (
            client.post(
                "/predict",
                json=house_payload,
                headers={"Authorization": b"Bearer t\xf3ken"},
            ).status_code
            == 401
        )
        assert client.get("/health").status_code == 200


def test_credential_not_logged_or_returned(approved_artifact, caplog, tmp_path):
    app = create_app(
        ApiSettings(
            model_path=approved_artifact.path,
            database_path=tmp_path / "houses.db",
            mode="cloud",
            api_token=TEST_TOKEN,
        )
    )
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            content="{bad",
            headers={"Authorization": f"Bearer {TEST_TOKEN}x"},
        )
    assert response.status_code == 401
    assert TEST_TOKEN not in response.text
    assert TEST_TOKEN not in caplog.text
