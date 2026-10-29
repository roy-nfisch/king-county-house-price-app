"""Exercise the form through Streamlit with a verified test pipeline."""

from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("streamlit", reason="UI tests require the ui extra")
from streamlit.testing.v1 import AppTest  # noqa: E402

from king_county.cleaning import HouseCleaner
from king_county.features import HouseFeatureEngineer
from king_county.prediction import PredictionService
from king_county.schemas import HouseInput
from king_county.streamlit import page as ui

pytestmark = pytest.mark.integration
APP = ui.ROOT / "src/king_county/streamlit/app.py"


def test_valid_form_reuses_service_without_training(
    approved_artifact, monkeypatch, house_payload
):
    """A valid example yields USD and a model version across repeated submissions."""
    monkeypatch.setattr(ui, "MODEL_PATH", approved_artifact.path)
    expected = PredictionService(approved_artifact).predict(
        HouseInput.model_validate(house_payload)
    )
    app = AppTest.from_file(str(APP)).run()
    with (
        patch.object(HouseCleaner, "fit", side_effect=AssertionError("No fit")),
        patch.object(HouseFeatureEngineer, "fit", side_effect=AssertionError("No fit")),
        patch.object(pd, "read_csv", side_effect=AssertionError("No CSV")),
        patch.object(
            approved_artifact.__class__, "load", wraps=approved_artifact.load
        ) as load,
    ):
        app.button[0].click().run()
        app.button[0].click().run()
    assert not app.exception
    assert app.success[0].value == (
        f"Estimated price: ${expected.predicted_price:,.2f} USD"
    )
    assert any("Model version:" in caption.value for caption in app.caption)
    load.assert_called_once()


def test_invalid_form_does_not_load_model(monkeypatch):
    """Bad ZIP and incompatible areas give safe feedback before loading."""
    app = AppTest.from_file(str(APP)).run()
    app.text_input[0].set_value("bad")
    next(
        widget for widget in app.number_input if widget.label == "sqft_above"
    ).set_value(2000.0)
    with patch.object(ui, "PredictionService", side_effect=AssertionError("loaded")):
        app.button[0].click().run()
    assert not app.exception
    assert "zipcode" in app.error[0].value
    assert "bad" not in app.error[0].value
    app.text_input[0].set_value("98178")
    app.button[0].click().run()
    assert "house" in app.error[0].value


def test_missing_model_fails_safely_and_does_not_cache(tmp_path, monkeypatch):
    """Missing model paths and exceptions are not displayed or stored."""
    monkeypatch.setattr(ui, "MODEL_PATH", tmp_path / "secret-model")
    app = AppTest.from_file(str(APP)).run()
    app.button[0].click().run()
    assert not app.exception
    assert "unavailable" in app.error[0].value
    assert "secret-model" not in app.error[0].value
    assert "prediction_service" not in app.session_state


def test_sessions_do_not_share_a_cached_model(approved_artifact, monkeypatch, tmp_path):
    """A successful session cannot mask a missing model in a new session."""
    monkeypatch.setattr(ui, "MODEL_PATH", approved_artifact.path)
    first = AppTest.from_file(str(APP)).run()
    first.button[0].click().run()
    assert first.success
    monkeypatch.setattr(ui, "MODEL_PATH", tmp_path / "missing")
    second = AppTest.from_file(str(APP)).run()
    second.button[0].click().run()
    assert second.error
    assert not second.success


def test_prediction_failure_is_safe(approved_artifact, monkeypatch):
    """A prediction error does not reveal internal exception details."""
    from king_county.prediction import PredictionError

    monkeypatch.setattr(ui, "MODEL_PATH", approved_artifact.path)
    app = AppTest.from_file(str(APP)).run()
    with patch.object(
        PredictionService, "predict", side_effect=PredictionError("secret")
    ):
        app.button[0].click().run()
    assert "secret" not in app.error[0].value


def test_nullable_fields_and_leading_zero_zip(
    approved_artifact, monkeypatch, house_payload
):
    """Unknown values and the ZIP string reach the shared service unchanged."""
    monkeypatch.setattr(ui, "MODEL_PATH", approved_artifact.path)
    app = AppTest.from_file(str(APP)).run()
    app.text_input[0].set_value("01234")
    for checkbox in app.checkbox:
        checkbox.set_value(True)
    with patch.object(PredictionService, "predict", autospec=True) as predict:
        from king_county.schemas import PredictionResult

        predict.return_value = PredictionResult(
            predicted_price=100.0, model_version="test"
        )
        app.button[0].click().run()
    house = predict.call_args.args[1]
    expected = dict(
        house_payload, zipcode="01234", waterfront=None, view=None, yr_renovated=None
    )
    assert house.model_dump() == expected
    assert app.success and not app.exception


def test_altered_model_fails_without_caching(approved_artifact, monkeypatch):
    """Modified bytes fail checksum verification without revealing the path."""
    approved_artifact.path.write_bytes(b"tampered")
    monkeypatch.setattr(ui, "MODEL_PATH", approved_artifact.path)
    app = AppTest.from_file(str(APP)).run()
    app.button[0].click().run()
    assert not app.exception
    assert "verified" in app.error[0].value
    assert str(approved_artifact.path) not in app.error[0].value
    assert "prediction_service" not in app.session_state


@pytest.mark.parametrize("content", [None, "{bad", '{"bedrooms": 3}'])
def test_invalid_example_is_safe(tmp_path, monkeypatch, content):
    """Missing, malformed and wrong-shape examples fail without leaking paths."""
    path = tmp_path / "private-example.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(ui, "EXAMPLE_PATH", path)
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert "invalid" in app.error[0].value
    assert str(path) not in app.error[0].value
