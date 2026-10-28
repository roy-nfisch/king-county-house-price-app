"""Direct tests of the validation object, separate from cleaning behaviour."""

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from king_county.validation import HouseDataValidator

pytestmark = pytest.mark.unit


def test_validate_returns_numeric_columns_without_changing_input(raw_houses):
    """The object validates data, but never performs cleaning or removes rows."""
    before = raw_houses.copy(deep=True)
    expected = raw_houses[list(HouseDataValidator.REQUIRED_COLUMNS)].apply(
        pd.to_numeric
    )
    validator = HouseDataValidator(raw_houses)

    numeric = validator.validate()

    assert_frame_equal(numeric, expected)
    assert_frame_equal(raw_houses, before)


@pytest.mark.parametrize("column", HouseDataValidator.REQUIRED_COLUMNS)
def test_missing_column_fails_clearly(raw_houses, column):
    """Name missing inputs instead of inventing default house measurements."""
    validator = HouseDataValidator(raw_houses.drop(columns=[column]))

    with pytest.raises(ValueError, match=column):
        validator.validate()


@pytest.mark.parametrize("column", HouseDataValidator.NON_NULL_COLUMNS)
@pytest.mark.parametrize(
    "value", [None, np.nan, pd.NA], ids=["None", "NaN", "pandas-NA"]
)
def test_missing_required_measurement_fails(raw_houses, column, value):
    """Reject missing measurements that have no notebook fallback rule."""
    raw_houses[column] = value

    with pytest.raises(ValueError, match="must be finite"):
        HouseDataValidator(raw_houses).validate()


@pytest.mark.parametrize("column", HouseDataValidator.REQUIRED_COLUMNS)
@pytest.mark.parametrize("value", [np.inf, -np.inf], ids=["positive", "negative"])
def test_infinite_measurement_fails(raw_houses, column, value):
    """Reject both infinities in every required cleaning column."""
    raw_houses[column] = raw_houses[column].astype(float)
    raw_houses.loc[0, column] = value

    with pytest.raises(ValueError, match="finite|infinity"):
        HouseDataValidator(raw_houses).validate()


def test_non_numeric_column_fails_clearly(raw_houses):
    """Do not silently convert strings to house measurements."""
    raw_houses["view"] = "unknown"

    with pytest.raises(ValueError, match="view.*must contain numbers"):
        HouseDataValidator(raw_houses).validate()


def test_duplicate_column_names_fail(raw_houses):
    """Reject ambiguous input columns."""
    duplicated = pd.concat([raw_houses, raw_houses[["view"]]], axis=1)

    with pytest.raises(ValueError, match="unique column names"):
        HouseDataValidator(duplicated).validate()


def test_non_dataframe_input_fails():
    """Require named columns instead of an ambiguous numeric array."""
    with pytest.raises(TypeError, match="pandas DataFrame"):
        HouseDataValidator(np.zeros((1, 6))).validate()


@pytest.mark.parametrize("column", HouseDataValidator.REQUIRED_COLUMNS)
@pytest.mark.parametrize("value", [True, 1 + 2j], ids=["boolean", "complex"])
def test_non_real_measurement_fails(raw_houses, column, value):
    """Do not accept flags as measurements or discard imaginary values."""
    raw_houses[column] = value

    with pytest.raises(ValueError, match=f"{column}.*must contain numbers"):
        HouseDataValidator(raw_houses).validate()


@pytest.mark.parametrize("column", ["yr_built", "yr_renovated"])
@pytest.mark.parametrize(
    "year",
    [float(2**63), np.nextafter(float(-(2**63)), -np.inf), 1e20, -1e20],
    ids=["upper-bound", "below-lower-bound", "too-large", "too-small"],
)
def test_year_outside_storage_range_fails(raw_houses, column, year):
    """Finite values must not silently overflow when stored as integer years."""
    raw_houses[column] = year

    with pytest.raises(ValueError, match=f"{column}.*must fit int64 storage"):
        HouseDataValidator(raw_houses).validate()
