"""Feature formulas, fixed output contract, and training-reference isolation."""

from math import cos, pi, radians, sqrt
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_array_equal
from pandas.testing import assert_frame_equal
from sklearn.base import clone
from sklearn.exceptions import NotFittedError
from sklearn.pipeline import Pipeline

from king_county.cleaning import HouseCleaner
from king_county.features import HouseFeatureEngineer


def test_features_match_frozen_notebook_values(cleaned_houses, baseline):
    """Match original distances and every feature name in the same order."""
    engineer = HouseFeatureEngineer()

    features = engineer.fit_transform(cleaned_houses)

    expected = pd.DataFrame(
        baseline["expected_values"],
        index=baseline["output_rows"],
        columns=baseline["output_columns"],
    )
    assert_frame_equal(
        features[expected.columns], expected, check_dtype=False, rtol=1e-10, atol=1e-8
    )
    assert features.columns.tolist() == baseline["feature_names"]
    assert_array_equal(engineer.get_feature_names_out(), baseline["feature_names"])


def test_center_point_has_zero_distance(cleaned_houses):
    """The fixed centre maps to zero, not to the separate cosine latitude."""
    query = cleaned_houses.loc[[0]].copy()
    query["lat"], query["long"] = 47.62774, -122.24194

    features = HouseFeatureEngineer().fit(cleaned_houses).transform(query)

    assert features.loc[0, "center_distance"] == 0


def test_held_out_waterfront_does_not_become_its_own_reference(cleaned_houses):
    """A new waterfront house must measure distance to training references."""
    training = cleaned_houses.loc[[0, 49]].copy()
    query = cleaned_houses.loc[[230]].copy()
    engineer = HouseFeatureEngineer().fit(training)
    reference = training.loc[49]
    house = query.loc[230]
    dx = (house["long"] - reference["long"]) * cos(radians(reference["lat"]))
    dy = house["lat"] - reference["lat"]
    expected = sqrt(dx**2 + dy**2) * 2 * pi * 6378 / 360

    with patch.object(engineer, "fit", side_effect=AssertionError("Must not refit")):
        features = engineer.transform(query)

    assert features.loc[230, "water_distance"] == pytest.approx(expected)
    assert features.loc[230, "water_distance"] > 0
    assert len(engineer.waterfront_locations_) == 1


def test_query_batch_does_not_change_reference_state(cleaned_houses):
    """Predictions are independent of other houses in the incoming batch."""
    engineer = HouseFeatureEngineer().fit(cleaned_houses.loc[[0, 49]])
    before = engineer.waterfront_locations_.copy()

    alone = engineer.transform(cleaned_houses.loc[[230]])
    together = engineer.transform(cleaned_houses.loc[[230, 7]])

    assert_frame_equal(alone, together.loc[[230]])
    assert_array_equal(engineer.waterfront_locations_, before)


def test_fit_copies_references_and_transform_preserves_input(cleaned_houses):
    """Changing the source table later must not change the stored locations."""
    engineer = HouseFeatureEngineer()
    assert engineer.fit(cleaned_houses) is engineer
    references = engineer.waterfront_locations_.copy()
    cleaned_houses.loc[49, "lat"] = 0
    before = cleaned_houses.copy(deep=True)

    engineer.transform(cleaned_houses)

    assert_frame_equal(cleaned_houses, before)
    assert_array_equal(engineer.waterfront_locations_, references)
    assert references.shape == (2, 2)


def test_output_excludes_targets_ids_and_overwrites_supplied_distances(cleaned_houses):
    """Only the canonical model inputs leave the transformer."""
    expected = HouseFeatureEngineer().fit_transform(cleaned_houses)
    supplied = cleaned_houses.assign(
        price=-1,
        id=-1,
        date="not-a-feature",
        sqft_price=-1,
        center_distance=-1,
        water_distance=-1,
    )

    actual = HouseFeatureEngineer().fit_transform(supplied)

    assert_frame_equal(actual, expected)


def test_feature_order_does_not_depend_on_input_order(cleaned_houses):
    """Keep canonical columns and preserve duplicate, nonsequential row labels."""
    raw = cleaned_houses.iloc[:3].copy()
    raw.index = [42, 7, 42]
    engineer = HouseFeatureEngineer().fit(cleaned_houses)

    features = engineer.transform(raw[raw.columns[::-1]])

    expected = engineer.transform(raw)
    assert_frame_equal(features, expected)
    assert features.index.tolist() == [42, 7, 42]


def test_empty_query_returns_empty_ordered_features(cleaned_houses):
    """An empty prediction batch must not create fake houses or lose columns."""
    engineer = HouseFeatureEngineer().fit(cleaned_houses)

    features = engineer.transform(cleaned_houses.iloc[:0])

    assert features.empty
    assert features.columns.tolist() == list(engineer.FEATURE_NAMES)
    assert features.index.equals(cleaned_houses.iloc[:0].index)


def test_preprocessing_pipeline_works_with_raw_house_fields(raw_houses, baseline):
    """Combine the two objects without exposing price or ID to a model."""
    pipeline = Pipeline(
        [
            ("cleaning", HouseCleaner()),
            ("features", HouseFeatureEngineer()),
        ]
    )
    training = raw_houses.loc[baseline["output_rows"]]

    expected = pipeline.fit_transform(training)
    raw_inputs = training.drop(columns=["price", "id", "date", "sqft_basement"])
    actual = pipeline.transform(raw_inputs)

    assert_frame_equal(actual, expected)


def test_cloning_discards_learned_reference_state(cleaned_houses):
    """Cross-validation clones must learn their own references, not inherit them."""
    fitted = HouseFeatureEngineer().fit(cleaned_houses)
    fresh = clone(fitted)

    with pytest.raises(NotFittedError):
        fresh.transform(cleaned_houses)


@pytest.mark.parametrize(
    "operation",
    [
        lambda obj, data: obj.transform(data),
        lambda obj, data: obj.get_feature_names_out(),
    ],
    ids=["transform", "feature-names"],
)
def test_transform_requires_a_successful_fit(cleaned_houses, operation):
    """Do not guess reference locations when fit() has never succeeded."""
    engineer = HouseFeatureEngineer()

    with pytest.raises(NotFittedError):
        operation(engineer, cleaned_houses)


@pytest.mark.parametrize("empty", [False, True], ids=["no-waterfront", "no-rows"])
def test_fit_without_references_fails_clearly(cleaned_houses, empty):
    """No training references is an explicit error, not an invented fallback."""
    data = cleaned_houses.iloc[:0] if empty else cleaned_houses.assign(waterfront=0)

    with pytest.raises(ValueError, match="at least one waterfront house"):
        HouseFeatureEngineer().fit(data)


@pytest.mark.parametrize("column", HouseFeatureEngineer.FEATURE_NAMES[:-2])
def test_missing_feature_column_is_named(cleaned_houses, column):
    """Report missing feature inputs instead of supplying hidden defaults."""
    engineer = HouseFeatureEngineer().fit(cleaned_houses)

    with pytest.raises(ValueError, match=column):
        engineer.transform(cleaned_houses.drop(columns=column))


@pytest.mark.parametrize("column", ["lat", "long", "waterfront", "zipcode"])
@pytest.mark.parametrize("value", ["unknown", True, 1 + 2j])
def test_non_real_feature_inputs_fail(cleaned_houses, column, value):
    """Coordinate and feature measurements must be real numeric values."""
    data = cleaned_houses.copy()
    data[column] = value

    with pytest.raises(ValueError, match=f"{column}.*real numbers"):
        HouseFeatureEngineer().fit(data)


@pytest.mark.parametrize("column", ["lat", "long", "waterfront", "bedrooms"])
@pytest.mark.parametrize("value", [np.nan, pd.NA, np.inf, -np.inf])
def test_non_finite_feature_inputs_fail(cleaned_houses, column, value):
    """Nullable numeric dtypes must not bypass finite-value checks."""
    data = cleaned_houses.copy()
    data[column] = pd.Series(value, index=data.index, dtype="Float64")

    with pytest.raises(ValueError, match="finite, non-null"):
        HouseFeatureEngineer().fit(data)


@pytest.mark.parametrize(
    ("column", "value"),
    [("lat", -90.0), ("lat", 90.0), ("long", -180.0), ("long", 180.0)],
)
def test_geographic_boundaries_are_accepted(cleaned_houses, column, value):
    """Accept the physical latitude/longitude endpoints."""
    query = cleaned_houses.loc[[0]].copy()
    query[column] = value

    result = HouseFeatureEngineer().fit(cleaned_houses).transform(query)

    assert np.isfinite(result[["center_distance", "water_distance"]]).all().all()


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("lat", np.nextafter(-90.0, -np.inf)),
        ("lat", np.nextafter(90.0, np.inf)),
        ("long", np.nextafter(-180.0, -np.inf)),
        ("long", np.nextafter(180.0, np.inf)),
    ],
)
def test_coordinates_just_outside_limits_fail(cleaned_houses, column, value):
    """Reject coordinates immediately beyond each geographic boundary."""
    data = cleaned_houses.copy()
    data[column] = value

    with pytest.raises(ValueError, match=column):
        HouseFeatureEngineer().fit(data)


def test_feature_input_requires_a_dataframe(cleaned_houses):
    """Preserve named input columns rather than accepting ambiguous arrays."""
    with pytest.raises(TypeError, match="pandas DataFrame"):
        HouseFeatureEngineer().fit(cleaned_houses.to_numpy())


def test_duplicate_feature_columns_fail(cleaned_houses):
    """Reject ambiguous coordinate names rather than selecting both columns."""
    data = pd.concat([cleaned_houses, cleaned_houses[["lat"]]], axis=1)

    with pytest.raises(ValueError, match="unique column names"):
        HouseFeatureEngineer().fit(data)
