"""Small Streamlit form backed by the shared validated prediction service."""

import logging
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

from king_county.artifacts import DEFAULT_MODEL_PATH, ModelArtifact, ModelLoadError
from king_county.prediction import PredictionError, PredictionService
from king_county.schemas import HouseInput
from king_county.streamlit.form import HouseForm

ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = ROOT / DEFAULT_MODEL_PATH
EXAMPLE_PATH = ROOT / "examples/house.json"
logger = logging.getLogger(__name__)


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
        with st.container(border=True):
            st.metric("Estimated price (USD)", f"${result.predicted_price:,.2f}")
            st.caption(f"Model version: {result.model_version}")

    def render(self) -> None:
        """Show the example-filled form and handle a submitted house."""
        st.set_page_config(
            page_title="King County | House price", page_icon="🏠", layout="wide"
        )
        st.title("Explore a house price")
        st.caption("KING COUNTY · NOTEBOOK TO APP")
        st.write(
            "Start with the example below, adjust the house details, then estimate its price."
        )
        st.info(
            "Educational estimate from a historical model—not a professional valuation."
        )
        try:
            example = HouseInput.model_validate_json(
                self.example_path.read_text(encoding="utf-8")
            ).model_dump()
        except (OSError, ValueError):
            logger.error("The bundled house example is unavailable or invalid.")
            st.error("The bundled house example is unavailable or invalid.")
            return
        values, submitted = HouseForm(example).render()
        if submitted:
            self.predict(values)
