"""Fitted geographic features using the notebook's original distance formulas."""

import logging
from typing import Self

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted

from king_county.validation import HouseFeatureValidator

logger = logging.getLogger(__name__)


class HouseFeatureEngineer(TransformerMixin, BaseEstimator):
    """Remember training waterfront coordinates and create ordered model inputs.

    Pass cleaned house data, not raw year fields. Extra columns such as price,
    ID, date, or supplied distances are excluded from the returned features.
    """

    FEATURE_NAMES = (
        "bedrooms",
        "bathrooms",
        "sqft_living",
        "sqft_lot",
        "floors",
        "waterfront",
        "view",
        "condition",
        "grade",
        "sqft_above",
        "sqft_basement",
        "zipcode",
        "lat",
        "long",
        "sqft_living15",
        "sqft_lot15",
        "last_known_change",
        "center_distance",
        "water_distance",
    )

    def fit(self, X: pd.DataFrame, y: object = None) -> Self:
        """Store a copy of waterfront coordinates from the supplied rows only.

        Args:
            X: Cleaned training houses, including at least one waterfront house.
            y: Optional target, ignored; prices never influence these features.

        Returns:
            This fitted transformer. No complete house records are retained.

        Raises:
            TypeError, ValueError: For invalid inputs or no waterfront references.
        """
        data = HouseFeatureValidator(X, self.FEATURE_NAMES[:-2]).validate()
        references = data.loc[data["waterfront"].eq(1), ["long", "lat"]]
        if references.empty:
            raise ValueError(
                "Training data must contain at least one waterfront house."
            )
        self.waterfront_locations_ = references.to_numpy(dtype=float, copy=True)
        logger.debug("Stored %d training waterfront locations", len(references))
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Return 19 ordered features using the already-stored reference locations.

        Args:
            X: Cleaned houses. Inputs and fitted references are not modified.

        Returns:
            A new feature table with original row labels; extras are excluded.

        Raises:
            NotFittedError: If fit() has not succeeded.
            TypeError, ValueError: If the feature inputs are invalid.
        """
        check_is_fitted(self, "waterfront_locations_")
        features = HouseFeatureValidator(X, self.FEATURE_NAMES[:-2]).validate()
        features["center_distance"] = self._center_distance(features)
        features["water_distance"] = self._water_distance(features)
        logger.debug(
            "Created %d features for %d houses", len(self.FEATURE_NAMES), len(X)
        )
        return features.loc[:, list(self.FEATURE_NAMES)]

    def get_feature_names_out(self, input_features=None) -> np.ndarray:
        """Return the 19 output names; optional input names do not change them."""
        check_is_fitted(self, "waterfront_locations_")
        return np.asarray(self.FEATURE_NAMES, dtype=object)

    def _center_distance(self, data: pd.DataFrame) -> np.ndarray:
        """Return centre distances in km, preserving the two notebook latitudes."""
        delta_lat = np.absolute(47.62774 - data["lat"].to_numpy(dtype=float))
        delta_long = np.absolute(-122.24194 - data["long"].to_numpy(dtype=float))
        corrected_longitude = delta_long * np.cos(np.radians(47.6219))
        return self._distance_km(corrected_longitude, delta_lat)

    def _water_distance(self, data: pd.DataFrame) -> np.ndarray:
        """Return nearest training-waterfront distances in km, with linear memory.

        Work on all query rows per reference instead of a nested per-house loop.
        Do not allocate a potentially large query-by-reference distance matrix.
        """
        longitude = data["long"].to_numpy(dtype=float)
        latitude = data["lat"].to_numpy(dtype=float)
        nearest = np.full(len(data), np.inf)
        for ref_long, ref_lat in self.waterfront_locations_:
            delta_long = (longitude - ref_long) * np.cos(np.radians(ref_lat))
            delta_lat = latitude - ref_lat
            distance = self._distance_km(delta_long, delta_lat)
            np.minimum(nearest, distance, out=nearest)
        return nearest

    @staticmethod
    def _distance_km(delta_long: np.ndarray, delta_lat: np.ndarray) -> np.ndarray:
        """Convert corrected degree offsets to notebook-equivalent km distances.

        Args:
            delta_long: Longitude offsets after the caller's latitude correction.
            delta_lat: Latitude offsets in degrees.

        Returns:
            Distances in kilometres using the notebook's 6378 km Earth radius.
        """
        return (delta_long**2 + delta_lat**2) ** (1 / 2) * 2 * np.pi * 6378 / 360
