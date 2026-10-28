"""Check that refactoring changes code structure, not preprocessing results.

For the same controlled input, the original and refactored notebooks must match
the fixed expected values, feature order, and row labels. Only selected
preprocessing cells run; no model is trained or saved.

This is a regression check: it protects the original behaviour, but does not
prove that the original logic was correct or that a model predicts accurately.
Intentional behaviour changes need a separate review, not an automatic update
of the expected values just to make a failing test pass.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[2]


def select_preprocessing_cells(notebook, notebook_name, baseline):
    """Return labelled trusted cells for the original or extracted workflow."""
    if notebook_name == "King-County.ipynb":
        return [
            (number, notebook["cells"][number - 1])
            for number in baseline["source_cells"]
        ]
    return [
        (cell.get("metadata", {}).get("original_cell", "shared-step"), cell)
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
        and (
            cell.get("metadata", {}).get("baseline_step")
            or cell.get("metadata", {}).get("original_cell") in baseline["source_cells"]
        )
    ]


def run_preprocessing(notebook_name, baseline):
    """Execute only our trusted notebook's selected preprocessing cells.

    Args:
        notebook_name: Original or working notebook filename in this repository.
        baseline: Fixed source-cell numbers and controlled dataset row labels.

    Returns:
        Prepared features and waterfront coordinates in the same format for
        either notebook. No model is trained or loaded.
    """
    notebook = json.loads((ROOT / notebook_name).read_text())
    dataset = ROOT / "data/King_County_House_prices_dataset.csv"
    frame = pd.read_csv(dataset).loc[baseline["source_rows"]].copy()
    namespace = {"np": np, "pd": pd, "kc_data": frame}
    for number, cell in select_preprocessing_cells(notebook, notebook_name, baseline):
        source = "".join(cell["source"])
        exec(compile(source, f"{notebook_name}:cell-{number}", "exec"), namespace)
    if notebook_name == "King-County.ipynb":
        return (
            namespace["X"].drop(columns=["id"]),
            namespace["water_list"][["long", "lat"]].to_numpy(),
        )
    engineer = namespace["preprocessor"].named_steps["features"]
    return namespace["X_prepared"], engineer.waterfront_locations_


@pytest.mark.parametrize(
    "notebook_name", ["King-County.ipynb", "King-County-refactored.ipynb"]
)
def test_notebook_preprocessing_matches_snapshot(notebook_name, baseline, raw_houses):
    """Catch changed cleaning values, distances, feature order, or row alignment."""
    prepared, locations = run_preprocessing(notebook_name, baseline)
    expected = pd.DataFrame(
        baseline["expected_values"],
        index=baseline["output_rows"],
        columns=baseline["output_columns"],
    )
    actual = prepared[baseline["output_columns"]]

    assert_frame_equal(actual, expected, check_dtype=False, rtol=1e-10, atol=1e-8)
    assert prepared.columns.tolist() == baseline["feature_names"]
    assert actual.index.tolist() == baseline["output_rows"]
    np.testing.assert_array_equal(
        locations,
        raw_houses.loc[baseline["reference_rows"], ["long", "lat"]].to_numpy(),
    )


def test_baseline_dataset_is_unchanged(baseline):
    """Require an intentional baseline review if the bundled data changes."""
    dataset = ROOT / "data/King_County_House_prices_dataset.csv"

    assert (
        hashlib.sha256(dataset.read_bytes()).hexdigest() == baseline["dataset_sha256"]
    )
