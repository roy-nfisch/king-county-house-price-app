"""Request-to-response checks through the real app lifespan and tiny model."""

import json
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import ApiSettings
from king_county.artifacts import MODEL_VERSION, ModelArtifact, ModelLoadError
from king_county.prediction import PredictionError, PredictionService

pytestmark = pytest.mark.integration


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


def test_api_price_matches_direct_pipeline_prediction(client, house_payload):
    """Check response forwarding against the same loaded fitted pipeline."""
    values = dict(house_payload, zipcode=int(house_payload["zipcode"]))
    pipeline = client.app.state.prediction_service._pipeline
    expected = float(pipeline.predict(pd.DataFrame([values]))[0])
    response = client.post("/predict", json=house_payload)
    assert response.status_code == 200
    assert response.json()["predicted_price"] == pytest.approx(
        expected, rel=1e-12, abs=1e-6
    )


@pytest.mark.parametrize("field,value", [("bedrooms", 10**100), ("sqft_lot", 1e200)])
def test_oversized_numbers_return_422_before_prediction(
    client, house_payload, field, value
):
    """Reject technically unusable inputs rather than reporting model failure."""
    house_payload[field] = value
    with patch.object(PredictionService, "predict") as predict:
        response = client.post("/predict", json=house_payload)
    assert response.status_code == 422
    predict.assert_not_called()


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


@pytest.mark.parametrize(
    ("key", "value"),
    [("bedrooms", 3), ("bedrooms", 8), (r"\u0062edrooms", 8)],
    ids=["same-value", "conflicting-value", "escaped-key"],
)
def test_duplicate_json_keys_return_422(client, house_payload, key, value):
    """Reject repeated decoded field names instead of silently taking the last."""
    body = json.dumps(house_payload)[:-1] + f', "{key}": {value}}}'
    response = client.post(
        "/predict",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_duplicate_json_keys_never_reach_prediction(client, house_payload):
    """Ambiguous input is blocked before the service is called."""
    body = json.dumps(house_payload)[:-1] + ', "bedrooms": 8}'
    with patch.object(PredictionService, "predict") as predict:
        client.post(
            "/predict", content=body, headers={"Content-Type": "application/json"}
        )
    predict.assert_not_called()


@pytest.mark.parametrize("body", ['{"bedrooms":', "", "[]"])
def test_malformed_or_non_object_json_returns_422(client, body):
    """Raw-key validation must not turn other invalid-body cases into 500s."""
    response = client.post(
        "/predict",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_startup_loads_once_for_all_requests(
    approved_artifact, house_payload, tmp_path
):
    """One worker reuses one verified pipeline rather than loading per request."""
    with patch.object(
        ModelArtifact, "load", autospec=True, return_value=approved_artifact.load()
    ) as load:
        with TestClient(
            create_app(
                ApiSettings(
                    model_path=approved_artifact.path,
                    database_path=tmp_path / "houses.db",
                )
            )
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


@pytest.mark.parametrize(
    "field,value",
    [
        ("price", 500000),
        ("bathrooms", "2"),
        ("bedrooms", True),
        ("lat", 90.01),
    ],
)
def test_invalid_house_values_never_reach_service(client, house_payload, field, value):
    """Check representative schema rules at the HTTP boundary, not only in units."""
    house_payload[field] = value
    with patch.object(PredictionService, "predict") as predict:
        response = client.post("/predict", json=house_payload)
    predict.assert_not_called()
    assert response.status_code == 422


def test_area_above_living_area_never_reaches_service(client, house_payload):
    """Derive the invalid area from the request rather than example constants."""
    house_payload["sqft_above"] = house_payload["sqft_living"] + 1
    with patch.object(PredictionService, "predict") as predict:
        response = client.post("/predict", json=house_payload)
    predict.assert_not_called()
    assert response.status_code == 422


@pytest.mark.parametrize("output", [[float("nan")], []])
def test_invalid_pipeline_output_becomes_controlled_http_error(
    client, house_payload, output
):
    """Exercise pipeline -> real service validation -> route error translation."""
    pipeline = client.app.state.prediction_service._pipeline
    with patch.object(pipeline, "predict", return_value=output):
        response = client.post("/predict", json=house_payload)
    assert response.status_code == 500
    assert response.json() == {"detail": "The model could not produce a valid price."}
