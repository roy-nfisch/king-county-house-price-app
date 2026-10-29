"""Test stored-house field rules without HTTP or a database."""

import pytest
from pydantic import ValidationError

from king_county.house_records.schemas import HouseCreate, HouseOutput, HouseUpdate

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "field,value",
    [
        ("bedrooms", 0),
        ("bedrooms", 20),
        ("bathrooms", 0),
        ("bathrooms", 20),
        ("sqft_living", 100),
        ("sqft_living", 2**53 - 1),
        ("grade", 1),
        ("grade", 13),
        ("zipcode", "12345"),
        ("zipcode", "1234567890"),
    ],
)
def test_valid_boundaries(house_fields, field, value):
    """Both ends of each documented field range remain accepted."""
    house = HouseCreate.model_validate({**house_fields, field: value})
    assert getattr(house, field) == value


@pytest.mark.parametrize(
    "field,value",
    [
        ("bedrooms", -1),
        ("bedrooms", 21),
        ("bedrooms", True),
        ("bedrooms", "1"),
        ("bathrooms", -0.1),
        ("bathrooms", 20.1),
        ("sqft_living", 99),
        ("sqft_living", 2**53),
        ("sqft_living", 100.5),
        ("grade", 0),
        ("grade", 14),
        ("zipcode", "1234"),
        ("zipcode", "12345678901"),
    ],
)
def test_invalid_boundaries(house_fields, field, value):
    """Incorrect types and out-of-range fields still fail validation."""
    with pytest.raises(ValidationError):
        HouseCreate.model_validate({**house_fields, field: value})


@pytest.mark.parametrize(
    "field", ["bedrooms", "bathrooms", "sqft_living", "grade", "zipcode"]
)
@pytest.mark.parametrize("kind", ["missing", "null"])
def test_required_nonnull_fields(house_fields, field, kind):
    """All five keys must be present and non-null."""
    if kind == "missing":
        del house_fields[field]
    else:
        house_fields[field] = None
    with pytest.raises(ValidationError):
        HouseCreate.model_validate(house_fields)


def test_update_and_output_keep_the_same_fields(house_fields):
    """Replacement shares validation; output only adds the stored identifier."""
    assert HouseUpdate.model_validate(house_fields).model_dump() == house_fields
    output = HouseOutput.model_validate({"id": 3, **house_fields})
    assert output.model_dump() == {"id": 3, **house_fields}
