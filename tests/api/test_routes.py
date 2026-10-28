"""Request-to-response checks through the real app lifespan and tiny model."""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import ApiSettings
from king_county.artifacts import MODEL_VERSION, ModelArtifact, ModelLoadError
from king_county.prediction import PredictionError, PredictionService


@pytest.fixture
def client(approved_artifact):
    """Start/stop the real application with the test's approved tiny model."""
    with TestClient(
        create_app(ApiSettings(model_path=approved_artifact.path))
    ) as client:
        yield client


@pytest.mark.parametrize("endpoint", ["/health", "/docs", "/openapi.json"])
def test_readiness_and_documentation_are_available(client, endpoint):
    """Documented endpoints are usable after successful model loading."""
    assert client.get(endpoint).status_code == 200


def test_health_reports_the_loaded_model_version(client):
    """Health means ready, not model quality or deployment approval."""
    assert client.get("/health").json() == {
        "status": "ready",
        "model_version": MODEL_VERSION,
    }


@pytest.mark.parametrize(
    "field, expected", [("currency", "USD"), ("model_version", MODEL_VERSION)]
)
def test_prediction_response_identity(client, house_payload, field, expected):
    """Check independent response fields without hiding one behind another."""
    assert client.post("/predict", json=house_payload).json()[field] == expected


def test_prediction_returns_a_positive_price(client, house_payload):
    """A real pipeline handles the example, including nullable waterfront."""
    response = client.post("/predict", json=house_payload)
    assert response.json()["predicted_price"] > 0


@pytest.mark.parametrize("field", ["bedrooms", "zipcode", "view"])
def test_missing_inputs_return_422_before_prediction(client, house_payload, field):
    """No default values or model calls are substituted for missing keys."""
    del house_payload[field]
    with patch.object(PredictionService, "predict") as predict:
        response = client.post("/predict", json=house_payload)
    predict.assert_not_called()
    assert response.status_code == 422


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_http_inputs_return_422_not_500(client, house_payload, value):
    """A non-standard JSON number must not break error-response serialization."""
    house_payload["bathrooms"] = value
    response = client.post(
        "/predict",
        content=json.dumps(house_payload),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_validation_errors_do_not_echo_input_records(client, house_payload):
    """Error responses identify the field without returning whole house records."""
    house_payload["sqft_above"] = house_payload["sqft_living"] + 1
    errors = client.post("/predict", json=house_payload).json()["detail"]
    assert all(set(error) == {"type", "loc", "msg"} for error in errors)


def test_startup_loads_once_for_all_requests(approved_artifact, house_payload):
    """One worker reuses one verified pipeline rather than loading per request."""
    with patch.object(
        ModelArtifact, "load", autospec=True, return_value=approved_artifact.load()
    ) as load:
        with TestClient(
            create_app(ApiSettings(model_path=approved_artifact.path))
        ) as client:
            for _ in range(2):
                client.post("/predict", json=house_payload)
                client.get("/health")
    load.assert_called_once()


def test_missing_model_prevents_startup(tmp_path):
    """A server cannot report ready when its required artifact is missing."""
    app = create_app(ApiSettings(model_path=tmp_path / "missing.skops"))
    with pytest.raises(ModelLoadError, match="missing or unreadable"), TestClient(app):
        pass


def test_app_factory_does_not_load_a_model(tmp_path):
    """Creating/importing the app is separate from startup verification."""
    with patch.object(ModelArtifact, "load") as load:
        create_app(ApiSettings(model_path=tmp_path / "missing.skops"))
    load.assert_not_called()


def test_wrong_model_prevents_startup(approved_artifact):
    """Startup, not the first user request, catches modified artifact bytes."""
    approved_artifact.path.write_bytes(b"wrong")
    app = create_app(ApiSettings(model_path=approved_artifact.path))
    with pytest.raises(ModelLoadError, match="checksum mismatch"), TestClient(app):
        pass


def test_model_failure_returns_clear_error_without_internal_detail(
    client, house_payload
):
    """Expose a controlled server error, not an internal model exception."""
    with patch.object(
        PredictionService, "predict", side_effect=PredictionError("Unable to predict.")
    ):
        response = client.post("/predict", json=house_payload)
    assert response.json() == {"detail": "Unable to predict."}


def test_model_failure_returns_500(client, house_payload):
    """An invalid model response is not a successful price prediction."""
    with patch.object(
        PredictionService, "predict", side_effect=PredictionError("Unable to predict.")
    ):
        assert client.post("/predict", json=house_payload).status_code == 500
