"""Small Streamlit form backed by the shared validated prediction service."""

import logging
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

from king_county.artifacts import DEFAULT_MODEL_PATH, ModelArtifact, ModelLoadError
from king_county.prediction import PredictionError, PredictionService
from king_county.schemas import HouseInput

ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = ROOT / DEFAULT_MODEL_PATH
EXAMPLE_PATH = ROOT / "examples/house.json"
logger = logging.getLogger(__name__)


def house_form(example: dict) -> tuple[dict, bool]:
    """Collect the 17 raw fields and return their values and submit state."""
    values = {}
    with st.form("house"):
        st.caption("All fields are required; select Unknown where available.")
        for name in ("bedrooms", "condition", "grade", "yr_built"):
            values[name] = st.number_input(name, 0, 1_000_000_000, example[name])
        for name in (
            "bathrooms",
            "sqft_living",
            "sqft_lot",
            "floors",
            "sqft_above",
            "sqft_living15",
            "sqft_lot15",
        ):
            values[name] = st.number_input(
                name, 0.0, 1_000_000_000.0, float(example[name])
            )
        for name in ("waterfront", "view", "yr_renovated"):
            unknown = st.checkbox(f"{name}: unknown", value=example[name] is None)
            if name == "waterfront":
                value = st.selectbox(name, [0, 1], index=example[name] or 0)
            elif name == "view":
                value = st.number_input(
                    name, 0.0, 1_000_000_000.0, float(example[name] or 0)
                )
            else:
                value = st.number_input(name, 0, 1_000_000_000, example[name] or 0)
            values[name] = None if unknown else value
        values["zipcode"] = st.text_input("zipcode", example["zipcode"], max_chars=5)
        values["lat"] = st.number_input("lat", -90.0, 90.0, example["lat"])
        values["long"] = st.number_input("long", -180.0, 180.0, example["long"])
        submitted = st.form_submit_button("Predict price")
    return values, submitted


class HousePricePage:
    """Own the fixed checkout assets and session's prediction service."""

    def __init__(self) -> None:
        """Select the code-defined example and approved model locations."""
        self.example_path = EXAMPLE_PATH
        self.model_path = MODEL_PATH

    def predict(self, values: dict) -> None:
        """Validate form values and display the prediction or a safe error."""
        try:
            house = HouseInput.model_validate(values)
        except ValidationError as exc:
            fields = sorted(
                {
                    ".".join(str(part) for part in e["loc"]) or "house"
                    for e in exc.errors()
                }
            )
            st.error(
                f"Please check: {', '.join(fields)}. ZIP must have five digits, "
                "and above-ground area cannot exceed living area."
            )
            return
        try:
            if "prediction_service" not in st.session_state:
                st.session_state.prediction_service = PredictionService(
                    ModelArtifact(self.model_path)
                )
            result = st.session_state.prediction_service.predict(house)
        except ModelLoadError:
            st.error("The approved model is unavailable or could not be verified.")
            return
        except PredictionError:
            st.error("The model could not produce a valid price for this house.")
            return
        st.success(f"Estimated price: ${result.predicted_price:,.2f} USD")
        st.caption(f"Model version: {result.model_version}")

    def render(self) -> None:
        """Show the example-filled form and handle a submitted house."""
        st.title("King County house price")
        try:
            example = HouseInput.model_validate_json(
                self.example_path.read_text(encoding="utf-8")
            ).model_dump()
        except (OSError, ValueError):
            logger.error("The bundled house example is unavailable or invalid.")
            st.error("The bundled house example is unavailable or invalid.")
            return
        values, submitted = house_form(example)
        if submitted:
            self.predict(values)
