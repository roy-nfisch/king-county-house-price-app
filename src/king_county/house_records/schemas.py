"""Validate the five stored house fields, independently of HTTP."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from king_county.schemas import MAX_MEASUREMENT


class HouseCreate(BaseModel):
    """Require all five stored fields, using the course reference bounds."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    bedrooms: Annotated[int, Field(ge=0, le=20)]
    bathrooms: Annotated[float, Field(ge=0, le=20)]
    sqft_living: Annotated[int, Field(ge=100, le=MAX_MEASUREMENT)]
    grade: Annotated[int, Field(ge=1, le=13)]
    zipcode: Annotated[str, Field(min_length=5, max_length=10)]


class HouseUpdate(HouseCreate):
    """Replace all five fields; null and omitted fields are invalid."""


class HouseOutput(HouseCreate):
    """Return a stored house with its database-assigned identifier."""

    id: int
