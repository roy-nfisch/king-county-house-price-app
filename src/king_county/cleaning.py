"""Copy-first cleaning rules extracted from the King County notebook."""

import logging
from typing import Self

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from king_county.validation import HouseDataValidator

logger = logging.getLogger(__name__)


class HouseCleaner(TransformerMixin, BaseEstimator):
    """Apply fixed cleaning rules without learning values or removing rows.

    Other columns, such as house IDs or a training target, pass through unchanged.
    Training-row exclusions belong to the notebook, not this transformer.
    """

    def fit(self, X: pd.DataFrame, y: object = None) -> Self:
        """Validate training input; no averages or other state are learned.

        Args:
            X: Raw house table with the required numeric cleaning columns.
            y: Optional target, ignored because these rules are fixed.

        Returns:
            This cleaner, ready for use in a scikit-learn pipeline.
        """
        validator = HouseDataValidator(X)
        validator.validate()
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Return cleaned data without modifying the input or its row labels.

        Args:
            X: Raw house table. View, waterfront, and renovation may be missing.

        Returns:
            A copy with corrected basement/view/waterfront values and
            last_known_change replacing yr_built and yr_renovated.

        Raises:
            TypeError: If X is not a pandas DataFrame.
            ValueError: If required columns or usable numeric inputs are missing.
        """
        validator = HouseDataValidator(X)
        numeric = validator.validate()
        cleaned = X.copy()
        cleaned["sqft_basement"] = numeric["sqft_living"] - numeric["sqft_above"]
        cleaned[["view", "waterfront"]] = numeric[["view", "waterfront"]].fillna(0)
        # Keep integer years exact when the other column contains floats/nulls.
        renovation = numeric["yr_renovated"].astype(object)
        cleaned["last_known_change"] = (
            renovation.where(
                renovation.notna() & renovation.ne(0),
                numeric["yr_built"].astype(object),
            )
            .map(int)
            .astype("int64")
        )
        logger.debug("Cleaned %d house rows", len(cleaned))
        return cleaned.drop(columns=["yr_built", "yr_renovated"])
