"""Input/output contract checks, including boundaries and explicit null rules."""

import numpy as np
import pytest
from pydantic import ValidationError

from king_county.schemas import HouseInput, PredictionResult


def test_dataset_example_has_exactly_the_raw_input_contract(house_payload):
    """The documented example provides the 17 fields, without derived features."""
    assert set(house_payload) == set(HouseInput.model_fields)


@pytest.mark.parametrize("field", list(HouseInput.model_fields))
def test_all_input_keys_are_required(house_payload, field):
    """Even nullable fields need explicit keys; no hidden default is supplied."""
    del house_payload[field]
    with pytest.raises(ValidationError):
        HouseInput.model_validate(house_payload)


@pytest.mark.parametrize(
    "field", ["price", "id", "date", "sqft_price", "water_distance"]
)
def test_targets_identifiers_and_derived_inputs_are_rejected(house_payload, field):
    """Users cannot supply a training target or bypass computed features."""
    house_payload[field] = 1
    with pytest.raises(ValidationError):
        HouseInput.model_validate(house_payload)


@pytest.mark.parametrize("field", ["view", "waterfront", "yr_renovated"])
def test_documented_nullable_inputs_are_accepted(house_payload, field):
    """The cleaner, not the request schema, applies the original null rules."""
    house_payload[field] = None
    assert getattr(HouseInput.model_validate(house_payload), field) is None


@pytest.mark.parametrize("field", ["bedrooms", "lat", "sqft_living", "zipcode"])
@pytest.mark.parametrize("value", [True, [], {}])
def test_wrong_input_types_are_rejected(house_payload, field, value):
    """Reject coercion from booleans or unrelated JSON types."""
    house_payload[field] = value
    with pytest.raises(ValidationError):
        HouseInput.model_validate(house_payload)


@pytest.mark.parametrize("field", ["bathrooms", "lat", "long", "view", "sqft_lot"])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_non_finite_measurements_are_rejected(house_payload, field, value):
    """A valid JSON number must also be usable by the fitted pipeline."""
    house_payload[field] = value
    with pytest.raises(ValidationError):
        HouseInput.model_validate(house_payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("lat", -90),
        ("lat", 90),
        ("long", -180),
        ("long", 180),
        ("waterfront", 0),
        ("waterfront", 1),
        ("yr_built", 0),
        ("yr_renovated", 2**63 - 1),
        ("bedrooms", 0),
    ],
)
def test_input_boundaries_are_accepted(house_payload, field, value):
    """Physical endpoints and technical storage bounds are inclusive."""
    house_payload[field] = value
    assert getattr(HouseInput.model_validate(house_payload), field) == value


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("lat", np.nextafter(-90.0, -np.inf)),
        ("lat", np.nextafter(90.0, np.inf)),
        ("long", np.nextafter(-180.0, -np.inf)),
        ("long", np.nextafter(180.0, np.inf)),
        ("waterfront", -1),
        ("waterfront", 2),
        ("yr_built", -1),
        ("yr_renovated", 2**63),
        ("bedrooms", -1),
        ("sqft_lot", np.nextafter(0.0, -np.inf)),
    ],
)
def test_just_outside_input_boundaries_fails(house_payload, field, value):
    """Fail just beyond bounds rather than rounding an invalid input into range."""
    house_payload[field] = value
    with pytest.raises(ValidationError):
        HouseInput.model_validate(house_payload)


@pytest.mark.parametrize("zipcode", [98178, "9817", "981789", "9817A", " 98178"])
def test_zipcode_requires_five_ascii_digits(house_payload, zipcode):
    """Keep ZIP codes explicit strings; the service converts them for the model."""
    house_payload["zipcode"] = zipcode
    with pytest.raises(ValidationError):
        HouseInput.model_validate(house_payload)


def test_equal_above_ground_and_living_areas_are_allowed(house_payload):
    """A house with no basement is valid."""
    house_payload["sqft_above"] = house_payload["sqft_living"]
    assert (
        HouseInput.model_validate(house_payload).sqft_above
        == house_payload["sqft_living"]
    )


def test_above_ground_area_just_above_living_area_fails(house_payload):
    """Area consistency is checked before the pipeline receives the request."""
    house_payload["sqft_above"] = np.nextafter(
        float(house_payload["sqft_living"]), np.inf
    )
    with pytest.raises(ValidationError, match="must not exceed"):
        HouseInput.model_validate(house_payload)


@pytest.mark.parametrize("price", [0, -1, np.nan, np.inf, -np.inf])
def test_invalid_price_outputs_are_rejected(price):
    """Do not silently clamp or expose unusable predicted prices."""
    with pytest.raises(ValidationError):
        PredictionResult(predicted_price=price, model_version="test")
