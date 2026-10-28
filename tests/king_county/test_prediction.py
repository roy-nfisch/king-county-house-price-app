"""Prediction service behavior, isolated from HTTP and the production artifact."""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from king_county.cleaning import HouseCleaner
from king_county.features import HouseFeatureEngineer
from king_county.prediction import PredictionError, PredictionService
from king_county.schemas import HouseInput


def test_predictions_reuse_one_loaded_artifact(approved_artifact, house_payload):
    """Repeated calls do not re-read or deserialize the model."""
    with patch.object(approved_artifact, "load", wraps=approved_artifact.load) as load:
        service = PredictionService(approved_artifact)
        house = HouseInput.model_validate(house_payload)
        service.predict(house)
        service.predict(house)
    load.assert_called_once_with()


def test_prediction_never_refits_or_reads_the_csv(approved_artifact, house_payload):
    """Only stored references are used when turning the request into features."""
    service = PredictionService(approved_artifact)
    house = HouseInput.model_validate(house_payload)
    with (
        patch.object(HouseCleaner, "fit", side_effect=AssertionError("No fit")),
        patch.object(HouseFeatureEngineer, "fit", side_effect=AssertionError("No fit")),
        patch.object(pd, "read_csv", side_effect=AssertionError("No CSV")),
    ):
        assert service.predict(house).predicted_price > 0


def test_request_zipcode_is_converted_for_the_fitted_pipeline(
    approved_artifact, house_payload
):
    """The public string contract meets the notebook's numeric ZIP feature."""
    service = PredictionService(approved_artifact)
    with patch.object(
        service._pipeline, "predict", return_value=np.array([100.0])
    ) as predict:
        service.predict(HouseInput.model_validate(house_payload))
    assert predict.call_args.args[0].loc[0, "zipcode"] == 98178


@pytest.mark.parametrize("output", [[np.nan], [np.inf], [-1.0], [0.0], [], [1.0, 2.0]])
def test_invalid_model_outputs_fail_explicitly(
    approved_artifact, house_payload, output
):
    """Fail rather than returning an invalid price or taking an arbitrary row."""
    service = PredictionService(approved_artifact)
    with (
        patch.object(service._pipeline, "predict", return_value=np.array(output)),
        pytest.raises(PredictionError, match="valid price"),
    ):
        service.predict(HouseInput.model_validate(house_payload))


def test_pipeline_failure_has_a_clear_service_error(approved_artifact, house_payload):
    """Model exceptions stay explicit without exposing request details."""
    service = PredictionService(approved_artifact)
    with (
        patch.object(
            service._pipeline, "predict", side_effect=ValueError("private detail")
        ),
        pytest.raises(PredictionError, match="valid price"),
    ):
        service.predict(HouseInput.model_validate(house_payload))
