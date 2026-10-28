"""An explicit validation object for the house-cleaning input table."""

import numpy as np
import pandas as pd
from pandas.api.types import (
    is_any_real_numeric_dtype,
    is_object_dtype,
    is_string_dtype,
)


class HouseDataValidator:
    """Own the house data and run the cleaning input checks in a fixed order.

    Validation does not fill values, drop rows, or modify the supplied table.
    The cleaner receives a separate numeric table only after all checks pass.
    """

    REQUIRED_COLUMNS = (
        "sqft_living",
        "sqft_above",
        "view",
        "waterfront",
        "yr_built",
        "yr_renovated",
    )
    NON_NULL_COLUMNS = ("sqft_living", "sqft_above", "yr_built")

    def __init__(self, data: pd.DataFrame) -> None:
        """Store the input table for validation without changing its contents.

        Args:
            data: Raw house table to check when validate() is called.

        Returns:
            None. Creates a validator; checks are not run until validate().
        """
        self.data = data

    def validate(self) -> pd.DataFrame:
        """Run each check and return the validated numeric cleaning columns.

        Returns:
            A separate numeric DataFrame, with original row labels preserved.

        Raises:
            TypeError: If the input is not a pandas DataFrame.
            ValueError: If a column or value violates a cleaning input rule.
        """
        for check in (self._check_table, self._check_column_types):
            check()
        numeric = self.data[list(self.REQUIRED_COLUMNS)].apply(pd.to_numeric)
        for check in (
            self._check_finite_values,
            self._check_areas,
            self._check_year_storage,
        ):
            check(numeric)
        return numeric

    def _check_table(self) -> None:
        """Check the input table and required column names; return None or raise."""
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("House data must be a pandas DataFrame.")
        if not self.data.columns.is_unique:
            raise ValueError("House data requires unique column names.")
        missing = set(self.REQUIRED_COLUMNS) - set(self.data.columns)
        if missing:
            raise ValueError(f"Missing cleaning columns: {', '.join(sorted(missing))}")

    def _check_column_types(self) -> None:
        """Check each configured cleaning column; return None or raise ValueError."""
        for column in self.REQUIRED_COLUMNS:
            values = self.data[column]
            missing_placeholder = values.isna().all() and (
                is_object_dtype(values) or is_string_dtype(values)
            )
            if not is_any_real_numeric_dtype(values) and not missing_placeholder:
                raise ValueError(
                    f"Cleaning column '{column}' must contain numbers; "
                    "use real values, not booleans or complex values."
                )

    def _check_finite_values(self, numeric: pd.DataFrame) -> None:
        """Check allowed missing/finite values; return None or raise ValueError."""
        required = numeric[list(self.NON_NULL_COLUMNS)]
        if not np.isfinite(required.to_numpy(dtype=float, na_value=np.nan)).all():
            raise ValueError(
                "Living area, above-ground area, and build year must be finite."
            )
        if np.isinf(numeric.to_numpy(dtype=float, na_value=np.nan)).any():
            raise ValueError("Cleaning columns must not contain infinity.")

    def _check_areas(self, numeric: pd.DataFrame) -> None:
        """Check non-negative ordered areas; return None or raise ValueError."""
        if (
            (numeric["sqft_living"] < 0)
            | (numeric["sqft_above"] < 0)
            | (numeric["sqft_above"] > numeric["sqft_living"])
        ).any():
            raise ValueError(
                "Areas must be non-negative and sqft_above <= sqft_living."
            )

    def _check_year_storage(self, numeric: pd.DataFrame) -> None:
        """Reject years that cannot fit int64; return None or raise ValueError.

        This is a storage limit, not a rule about plausible construction dates.
        Python integers avoid rounding the int64 boundaries during the check.
        """
        for column in ("yr_built", "yr_renovated"):
            years = numeric[column].dropna()
            fits_int64 = years.map(lambda year: -(2**63) <= int(year) < 2**63)
            if not fits_int64.all():
                raise ValueError(f"Cleaning column '{column}' must fit int64 storage.")
