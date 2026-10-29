"""Collect raw house fields without loading a model or making predictions."""

import streamlit as st


class HouseForm:
    """Own the example values and grouped widgets for one form render."""

    def __init__(self, example: dict) -> None:
        """Accept validated example fields; start with no submitted values."""
        self.example = example
        self.values = {}

    def _numbers(self, title: str, fields: tuple) -> None:
        """Add two-column numeric widgets and collect their raw field values."""
        st.subheader(title)
        columns = st.columns(2)
        for index, (name, label) in enumerate(fields):
            value = self.example[name]
            minimum = 0 if isinstance(value, int) else 0.0
            maximum = type(value)(1_000_000_000)
            with columns[index % 2]:
                self.values[name] = st.number_input(
                    label, minimum, maximum, value, key=name
                )

    def _location(self) -> None:
        """Keep ZIP codes as strings and coordinates at their original precision."""
        st.subheader("Location")
        self.values["zipcode"] = st.text_input(
            "ZIP code", self.example["zipcode"], max_chars=5, key="zipcode"
        )
        for column, name, label, limit in zip(
            st.columns(2), ("lat", "long"), ("Latitude", "Longitude"), (90.0, 180.0)
        ):
            with column:
                self.values[name] = st.number_input(
                    label,
                    -limit,
                    limit,
                    self.example[name],
                    step=0.0001,
                    format="%.6f",
                    key=name,
                )

    def _unknown_details(self) -> None:
        """Collect nullable fields; Unknown passes None, not an invented value."""
        st.subheader("Optional information")
        st.caption("Select Unknown when a value is unavailable.")
        for name, label in (
            ("waterfront", "Waterfront"),
            ("view", "View rating"),
            ("yr_renovated", "Year renovated"),
        ):
            left, right = st.columns(2)
            with left:
                unknown = st.checkbox(
                    f"{label}: unknown",
                    value=self.example[name] is None,
                    key=f"{name}_unknown",
                )
            with right:
                if name == "waterfront":
                    value = st.selectbox(
                        label,
                        [0, 1],
                        index=self.example[name] or 0,
                        key=name,
                        format_func=lambda option: "Yes" if option else "No",
                    )
                else:
                    default = self.example[name] or (0.0 if name == "view" else 0)
                    value = st.number_input(
                        label,
                        type(default)(0),
                        type(default)(1_000_000_000),
                        default,
                        key=name,
                    )
            self.values[name] = None if unknown else value

    def render(self) -> tuple[dict, bool]:
        """Return all 17 raw values and whether the user submitted the form."""
        with st.form("house"):
            self._numbers(
                "House details",
                (
                    ("bedrooms", "Bedrooms"),
                    ("bathrooms", "Bathrooms"),
                    ("floors", "Floors"),
                    ("grade", "Building grade"),
                    ("condition", "Condition rating"),
                    ("yr_built", "Year built"),
                ),
            )
            self._numbers(
                "Property size",
                (
                    ("sqft_living", "Living area (sq ft)"),
                    ("sqft_lot", "Lot size (sq ft)"),
                    ("sqft_above", "Above-ground area (sq ft)"),
                    ("sqft_living15", "Neighbouring living area (sq ft)"),
                    ("sqft_lot15", "Neighbouring lot size (sq ft)"),
                ),
            )
            self._location()
            self._unknown_details()
            submitted = st.form_submit_button("Estimate price", type="primary")
        return self.values, submitted
