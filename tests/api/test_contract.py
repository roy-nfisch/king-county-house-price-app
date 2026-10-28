"""Pin the public consumer contract independently of the application models.

Intentional API changes need an explicit review of these expectations. Ignore
OpenAPI titles/descriptions and generated IDs, which do not affect consumers.
Behavioural validation and model-quality checks belong in their existing tests.
"""

import math

import pytest

from king_county.artifacts import MODEL_VERSION

# Do not derive this agreement from HouseInput: both could then change unnoticed.
REQUEST_TYPES = {
    "bedrooms": {"integer"},
    "bathrooms": {"number"},
    "sqft_living": {"number"},
    "sqft_lot": {"number"},
    "floors": {"number"},
    "waterfront": {"integer", "null"},
    "view": {"number", "null"},
    "condition": {"integer"},
    "grade": {"integer"},
    "sqft_above": {"number"},
    "yr_built": {"integer"},
    "yr_renovated": {"integer", "null"},
    "zipcode": {"string"},
    "lat": {"number"},
    "long": {"number"},
    "sqft_living15": {"number"},
    "sqft_lot15": {"number"},
}


@pytest.fixture
def openapi(client):
    """Return the API document actually served to clients and generated SDKs."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


def test_predict_declares_required_json_body(openapi):
    """A client must send a JSON house, not query parameters or an optional body."""
    body = openapi["paths"]["/predict"]["post"]["requestBody"]
    assert body == {
        "required": True,
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/HouseInput"}}
        },
    }


@pytest.mark.parametrize("part", ["properties", "required"])
def test_request_field_names_are_fixed(openapi, part):
    """Renaming, adding, removing or making a field optional requires review."""
    assert set(openapi["components"]["schemas"]["HouseInput"][part]) == set(
        REQUEST_TYPES
    )


def test_request_forbids_unknown_fields(openapi):
    """The published schema must not silently permit additional input keys."""
    assert (
        openapi["components"]["schemas"]["HouseInput"]["additionalProperties"] is False
    )


@pytest.mark.parametrize("field,expected", REQUEST_TYPES.items())
def test_request_field_types_and_nullability_are_fixed(openapi, field, expected):
    """Check each field separately so one changed type does not hide another."""
    schema = openapi["components"]["schemas"]["HouseInput"]["properties"][field]
    variants = schema.get("anyOf", [schema])
    assert {variant["type"] for variant in variants} == expected


def test_predict_declares_json_response(openapi):
    """Keep the successful route connected to the public prediction schema."""
    response = openapi["paths"]["/predict"]["post"]["responses"]["200"]
    assert response["content"] == {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/PredictionResult"}
        }
    }


@pytest.fixture
def prediction_response(client, house_payload):
    """Return a real successful HTTP response using the shared tiny-model setup."""
    response = client.post("/predict", json=house_payload)
    assert response.status_code == 200, response.text
    return response


def test_prediction_response_is_json(prediction_response):
    """Clients can decode the documented response as JSON."""
    assert prediction_response.headers["content-type"] == "application/json"


def test_prediction_response_has_exact_public_fields(prediction_response):
    """Do not remove expected fields or leak additional internal model data."""
    assert set(prediction_response.json()) == {
        "predicted_price",
        "currency",
        "model_version",
    }


@pytest.mark.parametrize(
    "field,expected_types",
    [
        ("predicted_price", (int, float)),
        ("currency", (str,)),
        ("model_version", (str,)),
    ],
)
def test_prediction_response_field_types(prediction_response, field, expected_types):
    """Check the actual wire types rather than trusting Pydantic definitions."""
    assert type(prediction_response.json()[field]) in expected_types


@pytest.mark.parametrize(
    "field,expected", [("currency", "USD"), ("model_version", MODEL_VERSION)]
)
def test_prediction_response_identity(prediction_response, field, expected):
    """Keep existing response identity checks here instead of duplicating them."""
    assert prediction_response.json()[field] == expected


def test_prediction_response_price_is_finite_and_positive(prediction_response):
    """The public value is a usable total price, not a score or invalid number."""
    price = prediction_response.json()["predicted_price"]
    assert math.isfinite(price) and price > 0


@pytest.mark.parametrize("invalid_field", ["bedrooms", "sqft_above"])
def test_validation_error_contract_omits_private_input(
    client, house_payload, invalid_field
):
    """Field and cross-field failures expose locations/messages, not input/ctx."""
    house_payload[invalid_field] = (
        "private-invalid-value"
        if invalid_field == "bedrooms"
        else house_payload["sqft_living"] + 1
    )
    response = client.post("/predict", json=house_payload)
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"detail"}
    assert isinstance(body["detail"], list) and body["detail"]
    for error in body["detail"]:
        assert set(error) == {"type", "loc", "msg"}
        assert isinstance(error["type"], str)
        assert isinstance(error["loc"], list) and error["loc"][0] == "body"
        assert isinstance(error["msg"], str)
    assert "private-invalid-value" not in response.text
