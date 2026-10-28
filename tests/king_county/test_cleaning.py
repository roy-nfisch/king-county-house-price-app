"""Unit tests for notebook-equivalent cleaning and explicit failure behaviour."""

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal, assert_series_equal
from sklearn.base import clone
from sklearn.pipeline import Pipeline

from king_county.cleaning import HouseCleaner

TINY_FLOAT = np.nextafter(0.0, 1.0)
BELOW_ONE = np.nextafter(1.0, 0.0)
ABOVE_ONE = np.nextafter(1.0, np.inf)
MAX_FLOAT = np.finfo(float).max


def test_cleaning_matches_notebook_baseline(raw_houses, baseline):
    """Match the frozen original outputs on the retained comparison rows."""
    raw = raw_houses.loc[baseline["output_rows"]]
    expected = pd.DataFrame(
        baseline["expected_values"],
        index=baseline["output_rows"],
        columns=baseline["output_columns"],
    ).drop(columns=["center_distance", "water_distance"])

    cleaned = HouseCleaner().fit_transform(raw)

    assert_frame_equal(cleaned[expected.columns], expected, check_dtype=False)
    assert "yr_built" not in cleaned and "yr_renovated" not in cleaned


def test_cleaning_does_not_mutate_or_drop_rows(raw_houses):
    """Keep the input, row labels, target, and even the training exclusion row."""
    before = raw_houses.copy(deep=True)
    unchanged_columns = raw_houses.columns.drop(
        ["sqft_basement", "view", "waterfront", "yr_built", "yr_renovated"]
    )

    cleaned = HouseCleaner().fit_transform(raw_houses)

    assert_frame_equal(raw_houses, before)
    assert cleaned is not raw_houses
    assert_frame_equal(cleaned[unchanged_columns], before[unchanged_columns])


def test_existing_basement_value_is_recomputed(raw_houses):
    """Do not trust an incorrect supplied basement value."""
    raw_houses["sqft_basement"] = "unknown"

    cleaned = HouseCleaner().transform(raw_houses)

    assert cleaned.loc[1, "sqft_basement"] == 400
    assert raw_houses.loc[1, "sqft_basement"] == "unknown"


def test_null_optional_values_follow_notebook_rules(raw_houses):
    """Accept a one-house request with explicit nulls in optional fields."""
    raw = raw_houses.loc[[0]].copy()
    raw["view"] = None
    raw["waterfront"] = None
    raw["yr_renovated"] = None

    cleaned = HouseCleaner().transform(raw)

    expected = pd.Series({"view": 0, "waterfront": 0, "last_known_change": 1955})
    assert_series_equal(
        cleaned.loc[0, expected.index], expected, check_dtype=False, check_names=False
    )


def test_cleaner_works_in_sklearn_pipeline(raw_houses):
    """Allow cloning and ordinary pipeline fit/transform without training a model."""
    cleaner = clone(HouseCleaner())
    pipeline = Pipeline([("cleaning", cleaner)])

    result = pipeline.fit_transform(raw_houses)

    assert_frame_equal(result, HouseCleaner().transform(raw_houses))
    assert cleaner.fit(raw_houses) is cleaner


@pytest.mark.parametrize(
    ("living", "above", "basement"),
    [
        pytest.param(0.0, 0.0, 0.0, id="both-at-zero"),
        pytest.param(1.0, 0.0, 1.0, id="above-at-zero"),
        pytest.param(TINY_FLOAT, 0.0, TINY_FLOAT, id="just-above-zero"),
        pytest.param(1000.0, 999.0, 1.0, id="below-living-limit"),
        pytest.param(1000.0, 1000.0, 0.0, id="at-living-limit"),
        pytest.param(
            1.0,
            BELOW_ONE,
            np.spacing(1.0) / 2,
            id="just-below-living-limit",
        ),
        pytest.param(MAX_FLOAT, 0.0, MAX_FLOAT, id="largest-finite-living"),
        pytest.param(MAX_FLOAT, MAX_FLOAT, 0.0, id="largest-finite-equal-areas"),
    ],
)
def test_valid_area_boundaries(raw_houses, living, above, basement):
    """Accept the implemented area boundaries without imposing an invented cap."""
    raw = raw_houses.loc[[0]].copy()
    raw["sqft_living"] = living
    raw["sqft_above"] = above
    before = raw.copy(deep=True)

    cleaned = HouseCleaner().fit_transform(raw)

    assert cleaned.loc[0, "sqft_basement"] == pytest.approx(basement, rel=1e-12, abs=0)
    assert_frame_equal(raw, before)


@pytest.mark.parametrize("method", ["fit", "transform"])
@pytest.mark.parametrize(
    ("living", "above"),
    [
        pytest.param(-TINY_FLOAT, 0.0, id="living-just-below-zero"),
        pytest.param(0.0, -TINY_FLOAT, id="above-just-below-zero"),
        pytest.param(0.0, TINY_FLOAT, id="above-just-over-zero-living"),
        pytest.param(1.0, ABOVE_ONE, id="just-over-living-limit"),
        pytest.param(1000.0, 1001.0, id="one-square-foot-over-limit"),
        pytest.param(-1.0, -1.0, id="both-negative"),
    ],
)
def test_invalid_area_boundaries(raw_houses, method, living, above):
    """Reject values immediately outside either bound in fit and transform."""
    raw = raw_houses.loc[[0]].copy()
    raw["sqft_living"] = living
    raw["sqft_above"] = above
    before = raw.copy(deep=True)

    with pytest.raises(ValueError, match="Areas must"):
        getattr(HouseCleaner(), method)(raw)

    assert_frame_equal(raw, before)


@pytest.mark.parametrize(
    ("column", "output_column", "expected"),
    [
        pytest.param("view", "view", 0, id="view"),
        pytest.param("waterfront", "waterfront", 0, id="waterfront"),
        pytest.param("yr_renovated", "last_known_change", 1955, id="yr_renovated"),
    ],
)
@pytest.mark.parametrize(
    "value", [None, np.nan, pd.NA], ids=["None", "NaN", "pandas-NA"]
)
def test_each_nullable_column_uses_its_fallback(
    raw_houses, column, output_column, expected, value
):
    """Check each missing-value representation independently on one house."""
    raw = raw_houses.loc[[0]].copy()
    raw[column] = value

    cleaned = HouseCleaner().transform(raw)

    assert cleaned.loc[0, output_column] == expected


@pytest.mark.parametrize(
    ("column", "output_column", "value"),
    [
        ("view", "view", 0),
        ("view", "view", 4),
        ("waterfront", "waterfront", 0),
        ("waterfront", "waterfront", 1),
        ("yr_renovated", "last_known_change", 1978),
    ],
)
def test_explicit_values_are_preserved(raw_houses, column, output_column, value):
    """Do not treat valid zeros or supplied renovation years as missing data."""
    raw = raw_houses.loc[[0]].copy()
    raw[column] = value

    cleaned = HouseCleaner().transform(raw)

    assert cleaned.loc[0, output_column] == value


@pytest.mark.parametrize("value", [0, 0.0], ids=["integer-zero", "float-zero"])
def test_zero_renovation_uses_build_year(raw_houses, value):
    """The notebook's zero sentinel selects construction year, not year zero."""
    raw = raw_houses.loc[[0]].copy()
    raw["yr_renovated"] = value

    cleaned = HouseCleaner().transform(raw)

    assert cleaned.loc[0, "last_known_change"] == raw.loc[0, "yr_built"]


def test_empty_table_returns_empty_cleaned_table(raw_houses):
    """A zero-row preprocessing batch stays empty without creating fake houses."""
    raw = raw_houses.iloc[:0].copy()

    cleaned = HouseCleaner().fit_transform(raw)

    columns = [*raw.columns.drop(["yr_built", "yr_renovated"]), "last_known_change"]
    expected = pd.DataFrame(columns=columns, index=raw.index)
    assert_frame_equal(cleaned, expected, check_dtype=False)


def test_nonsequential_duplicate_row_labels_are_preserved(raw_houses):
    """Keep row order and duplicate labels rather than resetting or sorting them."""
    raw = raw_houses.iloc[:3].copy()
    raw.index = [42, 7, 42]

    cleaned = HouseCleaner().transform(raw)

    expected = pd.Series(
        [1955, 1991, 1933], index=[42, 7, 42], name="last_known_change"
    )
    assert_series_equal(cleaned["last_known_change"], expected)


@pytest.mark.parametrize("column", ["yr_built", "yr_renovated"])
@pytest.mark.parametrize(
    "year",
    [-(2**63), 2**63 - 1, np.nextafter(float(2**63), 0), float(-(2**63))],
    ids=["minimum-integer", "maximum-integer", "below-upper-float", "lower-float"],
)
def test_year_storage_boundaries_are_preserved(raw_houses, column, year):
    """Keep representable years exact, including mixed integer/float inputs."""
    raw = raw_houses.loc[[0]].copy()
    raw["yr_renovated"] = 0.0
    raw[column] = year

    cleaned = HouseCleaner().transform(raw)

    assert cleaned.loc[0, "last_known_change"] == int(year)
