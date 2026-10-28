"""Freeze preprocessing behaviour before extracting it into Python classes."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def baseline():
    """Return the reviewed snapshot; read source rows from the existing CSV."""
    fixture = ROOT / "tests/fixtures/notebook_baseline.json"
    return json.loads(fixture.read_text())


def run_preprocessing(notebook_name, baseline):
    """Execute only our trusted notebook's selected preprocessing cells.

    Args:
        notebook_name: Original or working notebook filename in this repository.
        baseline: Fixed source-cell numbers and controlled dataset row labels.

    Returns:
        Namespace containing the transformed controlled data, without training.
    """
    notebook = json.loads((ROOT / notebook_name).read_text())
    dataset = ROOT / "data/King_County_House_prices_dataset.csv"
    frame = pd.read_csv(dataset).loc[baseline["source_rows"]].copy()
    namespace = {"np": np, "pd": pd, "kc_data": frame}
    for number in baseline["source_cells"]:
        if notebook_name == "King-County.ipynb":
            cell = notebook["cells"][number - 1]
        else:
            cell = next(
                c
                for c in notebook["cells"]
                if c.get("metadata", {}).get("original_cell") == number
            )
        source = "".join(cell["source"])
        exec(compile(source, f"{notebook_name}:cell-{number}", "exec"), namespace)
    return namespace


@pytest.mark.parametrize(
    "notebook_name", ["King-County.ipynb", "King-County-refactored.ipynb"]
)
def test_notebook_preprocessing_matches_snapshot(notebook_name, baseline):
    """Catch changed cleaning values, distances, feature order, or row alignment."""
    result = run_preprocessing(notebook_name, baseline)
    expected = pd.DataFrame(
        baseline["expected_values"],
        index=baseline["output_rows"],
        columns=baseline["output_columns"],
    )
    actual = result["kc_data"][baseline["output_columns"]]

    assert_frame_equal(actual, expected, check_dtype=False, rtol=1e-10, atol=1e-8)
    assert (
        result["X"].drop(columns=["id"]).columns.tolist() == baseline["feature_names"]
    )
    assert actual.index.tolist() == baseline["output_rows"]
    assert result["water_list"].index.tolist() == baseline["reference_rows"]


def test_baseline_dataset_is_unchanged(baseline):
    """Require an intentional baseline review if the bundled data changes."""
    dataset = ROOT / "data/King_County_House_prices_dataset.csv"

    assert (
        hashlib.sha256(dataset.read_bytes()).hexdigest() == baseline["dataset_sha256"]
    )
