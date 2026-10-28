"""Explicit raw-house inputs and prediction outputs shared by interfaces."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Technical input policies, not estimates of realistic house sizes. Keep counts
# within pandas int64 storage and measurements within float64's consecutive-
# integer precision range. Squaring these measurements also remains finite.
MAX_MEASUREMENT = 2**53 - 1
MAX_COUNT = 2**63 - 1
NonNegative = Annotated[float, Field(ge=0, le=MAX_MEASUREMENT)]
Count = Annotated[int, Field(ge=0, le=MAX_COUNT)]
Year = Annotated[int, Field(ge=0, le=2**63 - 1)]


class HouseInput(BaseModel):
    """Require 17 raw fields; reject extras, non-finite numbers, and coercion.

    Null view, waterfront, and renovation follow the notebook's cleaning rules.
    All three keys are still required. ZIP codes are five-character strings.
    """

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    bedrooms: Count
    bathrooms: NonNegative
    sqft_living: NonNegative
    sqft_lot: NonNegative
    floors: NonNegative
    waterfront: Annotated[int, Field(ge=0, le=1)] | None
    view: NonNegative | None
    condition: Count
    grade: Count
    sqft_above: NonNegative
    yr_built: Year
    yr_renovated: Year | None
    zipcode: Annotated[str, Field(pattern=r"^[0-9]{5}$")]
    lat: Annotated[float, Field(ge=-90, le=90)]
    long: Annotated[float, Field(ge=-180, le=180)]
    sqft_living15: NonNegative
    sqft_lot15: NonNegative

    @model_validator(mode="after")
    def validate_area_relationship(self) -> Self:
        """Return this house, or reject above-ground area exceeding living area."""
        if self.sqft_above > self.sqft_living:
            raise ValueError("sqft_above must not exceed sqft_living.")
        return self


class PredictionResult(BaseModel):
    """Return a finite positive total price in USD and its reviewed model version."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    predicted_price: Annotated[float, Field(gt=0)]
    currency: Literal["USD"] = "USD"
    model_version: Annotated[str, Field(min_length=1)]
