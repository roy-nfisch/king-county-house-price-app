"""Predict with a verified fitted pipeline; never fit, train, or save requests."""

import logging

import numpy as np
import pandas as pd

from king_county.artifacts import MODEL_VERSION, ModelArtifact
from king_county.schemas import HouseInput, PredictionResult

logger = logging.getLogger(__name__)


class PredictionError(RuntimeError):
    """The fitted model could not produce a valid price response."""


class PredictionService:
    """Own one verified pipeline and reuse it for all prediction requests."""

    def __init__(self, artifact: ModelArtifact) -> None:
        """Load the artifact once; fail construction if verification fails."""
        self._pipeline = artifact.load()
        self.model_version = MODEL_VERSION
        logger.info("Prediction model loaded: %s", self.model_version)

    def predict(self, house: HouseInput) -> PredictionResult:
        """Return a validated total price, or raise PredictionError.

        Convert the validated ZIP string to the notebook's numeric feature.
        The fitted pipeline creates derived features; no CSV is read or fitted.
        Non-positive or non-finite outputs fail rather than being clamped.
        """
        values = house.model_dump()
        values["zipcode"] = int(values["zipcode"])
        try:
            predictions = np.asarray(self._pipeline.predict(pd.DataFrame([values])))
            if predictions.shape != (1,):
                raise ValueError("Expected one price for one house.")
            return PredictionResult(
                predicted_price=float(predictions[0]),
                model_version=self.model_version,
            )
        except (ValueError, TypeError, ArithmeticError) as exc:
            logger.warning("Prediction rejected: %s", type(exc).__name__)
            raise PredictionError("The model could not produce a valid price.") from exc
