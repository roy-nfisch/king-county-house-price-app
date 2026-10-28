"""Exercise notebook model/export cells on small data, not the full grid search."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
import skops.io as sio
from numpy.testing import assert_allclose, assert_array_equal
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline

from king_county.cleaning import HouseCleaner
from king_county.features import HouseFeatureEngineer

ROOT = Path(__file__).resolve().parents[2]


def run_step(namespace, name):
    """Run one trusted training/export cell in a supplied namespace; return None."""
    notebook = json.loads((ROOT / "King-County-refactored.ipynb").read_text())
    matching = [
        c for c in notebook["cells"] if c["metadata"].get("training_step") == name
    ]
    assert len(matching) == 1, f"Expected exactly one notebook step: {name}"
    source = "".join(matching[0]["source"])
    exec(compile(source, f"notebook:{name}", "exec"), namespace)


@pytest.fixture(scope="module")
def exported_bundle(tmp_path_factory, baseline):
    """Fit/export through real notebook cells; return their state for checks.

    Reuse six existing CSV records, repeated for a small two-fold check. This
    exercises integration only; its scores are not model-quality evidence.
    """
    raw = pd.read_csv(ROOT / "data/King_County_House_prices_dataset.csv")
    sample = raw.loc[baseline["output_rows"]]
    houses = pd.concat([sample] * 4, ignore_index=True)
    namespace = {
        "pd": pd,
        "Pipeline": Pipeline,
        "kc_data": houses,
        "HouseCleaner": HouseCleaner,
        "HouseFeatureEngineer": HouseFeatureEngineer,
    }
    with pytest.MonkeyPatch.context() as context:
        context.chdir(ROOT)
        for step in ("imports", "inputs", "pipeline"):
            run_step(namespace, step)
        namespace["search"].set_params(
            cv=2,
            verbose=0,
            param_grid={
                "model__regressor__alpha": [0.1],
                "model__regressor__l1_ratio": [0.5],
            },
        )
        for step in ("fit", "evaluate", "metadata", "reload_script"):
            run_step(namespace, step)
        context.chdir(tmp_path_factory.mktemp("model-export"))
        run_step(namespace, "export")
        namespace["artifact_path"] = namespace["artifact_path"].resolve()
        namespace["export_directory"] = namespace["export_directory"].resolve()
        run_step(namespace, "reload")
    return namespace


def test_complete_pipeline_keeps_training_references_only(exported_bundle):
    """The final refit stores training coordinates, not the full-data baseline."""
    state = exported_bundle
    pipeline = state["fitted_pipeline"]
    training = state["X_train"]
    expected = training.loc[training["waterfront"].eq(1), ["long", "lat"]]

    assert list(pipeline.named_steps) == [
        "cleaning",
        "features",
        "polynomial",
        "scaler",
        "model",
    ]
    assert len(state["RAW_INPUT_COLUMNS"]) == 17
    assert "price" not in state["X_train"]
    assert_array_equal(
        pipeline.named_steps["features"].waterfront_locations_,
        expected.to_numpy(),
    )


def test_cross_validation_clones_full_preprocessing_per_fold(exported_bundle):
    """Every CV estimator must fit its own references rather than reuse a fit."""
    state = exported_bundle
    search = state["search"]
    # Recreate GridSearchCV's unshuffled regression folds on the same inputs.
    folds = list(KFold(n_splits=2).split(state["X_train"]))
    result = cross_validate(
        search.best_estimator_,
        state["X_train"],
        state["y_train"],
        cv=folds,
        return_estimator=True,
        error_score="raise",
    )
    for (indices, _), estimator in zip(folds, result["estimator"], strict=True):
        training = state["X_train"].iloc[indices]
        expected = training.loc[training["waterfront"].eq(1), ["long", "lat"]]
        assert_array_equal(
            estimator.named_steps["features"].waterfront_locations_,
            expected.to_numpy(),
        )


def test_bundle_records_input_contract_checksum_and_evaluation(exported_bundle):
    """Metadata describes the actual fitted artifact and measured tiny run."""
    state = exported_bundle
    artifact = state["artifact_path"]
    metadata = json.loads(artifact.with_name("metadata.json").read_text())

    assert metadata["model_sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert metadata["raw_input_columns"] == state["RAW_INPUT_COLUMNS"]
    assert len(metadata["prepared_feature_columns"]) == 19
    assert metadata["split"]["train_rows"] == len(state["X_train"])
    assert metadata["test_metrics"] == state["metrics"]
    assert metadata["versions"]["scikit-learn"]
    assert metadata["target"] == "price"
    assert metadata["currency"] == "USD"
    assert all(np.isfinite(list(metadata["test_metrics"].values())))


def test_own_artifact_requires_only_named_custom_types(exported_bundle):
    """Never turn a loader's unknown-type list into an automatic allowlist."""
    data = exported_bundle["artifact_path"].read_bytes()
    allowed = {
        "king_county.cleaning.HouseCleaner",
        "king_county.features.HouseFeatureEngineer",
    }
    assert set(sio.get_untrusted_types(data=data)) == allowed


def test_reloaded_prediction_never_refits_or_reads_csv(exported_bundle):
    """The artifact is sufficient for inference without the source dataset."""
    state = exported_bundle
    data = state["artifact_path"].read_bytes()
    pipeline = sio.loads(
        data,
        trusted=[
            "king_county.cleaning.HouseCleaner",
            "king_county.features.HouseFeatureEngineer",
        ],
    )
    references = pipeline.named_steps["features"].waterfront_locations_.copy()
    with (
        patch.object(HouseCleaner, "fit", side_effect=AssertionError("No fitting")),
        patch.object(
            HouseFeatureEngineer, "fit", side_effect=AssertionError("No fitting")
        ),
        patch.object(pd, "read_csv", side_effect=AssertionError("No CSV")),
    ):
        actual = pipeline.predict(state["X_test"])
    assert_allclose(actual, state["predictions"], rtol=1e-10, atol=1e-6)
    assert_array_equal(
        pipeline.named_steps["features"].waterfront_locations_, references
    )


def test_fresh_process_reproduces_predictions(exported_bundle):
    """The notebook's isolated subprocess succeeded with only exported files."""
    assert (
        "Fresh-process reload passed for 3 houses" in exported_bundle["reloaded"].stdout
    )


def test_fresh_process_rejects_wrong_checksum(exported_bundle, tmp_path):
    """Checksum rejection happens before the exported artifact is loaded."""
    state = exported_bundle
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            state["reload_script"],
            str(state["artifact_path"]),
            "0" * 64,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode != 0
    assert "Model checksum mismatch" in result.stderr


def test_export_cannot_overwrite_an_existing_bundle(exported_bundle, monkeypatch):
    """Exclusive directory creation preserves the first artifact on rerun."""
    state = exported_bundle.copy()
    directory = state["export_directory"]
    before = state["artifact_path"].read_bytes()
    monkeypatch.chdir(directory.parents[2])

    with pytest.raises(FileExistsError):
        run_step(state, "export")

    assert state["artifact_path"].read_bytes() == before
