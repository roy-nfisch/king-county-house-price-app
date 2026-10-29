"""Check the grouped form's labels, raw field keys and coordinate precision."""

import pytest

pytest.importorskip("streamlit", reason="UI tests require the ui extra")
from streamlit.testing.v1 import AppTest  # noqa: E402

from king_county.streamlit.page import ROOT

pytestmark = pytest.mark.integration


@pytest.fixture
def form_app():
    """Render the real page without submitting or loading a model."""
    return AppTest.from_file(str(ROOT / "src/king_county/streamlit/app.py")).run()


def test_form_groups_have_readable_titles(form_app):
    """The page separates details, size, location and nullable information."""
    assert [heading.value for heading in form_app.subheader] == [
        "House details",
        "Property size",
        "Location",
        "Optional information",
    ]
    assert form_app.button[0].label == "Estimate price"
    assert "not a professional valuation" in form_app.info[0].value


def test_form_preserves_all_raw_field_keys(form_app, house_payload):
    """Friendly labels do not rename or omit any of the 17 service inputs."""
    widgets = (
        list(form_app.number_input)
        + list(form_app.text_input)
        + list(form_app.selectbox)
    )
    assert {widget.key for widget in widgets} == set(house_payload)
    assert form_app.text_input[0].label == "ZIP code"
    assert (
        next(w for w in form_app.number_input if w.key == "sqft_living").label
        == "Living area (sq ft)"
    )


@pytest.mark.parametrize("field", ["lat", "long"])
def test_coordinates_keep_example_precision(form_app, house_payload, field):
    """The displayed six-decimal coordinates retain the original input value."""
    widget = next(w for w in form_app.number_input if w.key == field)
    assert widget.value == house_payload[field]
    assert widget.proto.format == "%.6f"
