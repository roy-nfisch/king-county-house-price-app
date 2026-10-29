"""Small validated-record inputs shared by schema and storage tests."""

import pytest


@pytest.fixture
def house_fields():
    """Return a fresh five-field record, without a database ID."""
    return {
        "bedrooms": 2,
        "bathrooms": 1.0,
        "sqft_living": 900,
        "grade": 6,
        "zipcode": "01234",
    }
