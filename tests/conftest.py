"""Shared baseline fixtures; reuse the supplied CSV instead of duplicating data."""

import json
from pathlib import Path

import pandas as pd
import pytest
from sklearn.dummy import DummyRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from king_county.cleaning import HouseCleaner
from king_county.features import HouseFeatureEngineer

ROOT = Path(__file__).resolve().parents[1]


def pytest_collection_modifyitems(items):
    """Require exactly one test category; Docker is an additional runtime label."""
    categories = {"unit", "integration", "contract"}
    for item in items:
        assigned = [
            mark.name for mark in item.iter_markers() if mark.name in categories
        ]
        if len(assigned) != 1:
            raise pytest.UsageError(
                f"{item.nodeid}: assign exactly one unit, integration, or contract marker"
            )
        if item.get_closest_marker("docker") and assigned != ["integration"]:
            raise pytest.UsageError(f"{item.nodeid}: docker tests must be integration")


@pytest.fixture(scope="module")
def baseline():
    """Return fixed expected outputs and source-row labels for this module."""
    fixture = ROOT / "tests/fixtures/notebook_baseline.json"
    return json.loads(fixture.read_text())


@pytest.fixture
def raw_houses(baseline):
    """Return a fresh controlled table from the original CSV for each test."""
    dataset = ROOT / "data/King_County_House_prices_dataset.csv"
    return pd.read_csv(dataset).loc[baseline["source_rows"]].copy()


@pytest.fixture
def cleaned_houses(raw_houses, baseline):
    """Return cleaned comparison rows without the notebook's training exclusion."""
    return HouseCleaner().fit_transform(raw_houses.loc[baseline["output_rows"]])


@pytest.fixture
def house_payload():
    """Return the feature-only public CSV example used by API clients."""
    return json.loads((ROOT / "examples/house.json").read_text())


@pytest.fixture
def tiny_pipeline(raw_houses, baseline):
    """Return a small fitted pipeline for plumbing checks, not model evaluation."""
    houses = raw_houses.loc[baseline["output_rows"]]
    pipeline = Pipeline(
        [
            ("cleaning", HouseCleaner()),
            ("features", HouseFeatureEngineer()),
            ("polynomial", PolynomialFeatures(2, include_bias=False)),
            ("scaler", StandardScaler()),
            ("model", DummyRegressor()),
        ]
    )
    return pipeline.fit(houses.drop(columns="price"), houses["price"])


@pytest.fixture
def approved_artifact(tmp_path, monkeypatch, tiny_pipeline):
    """Write our tiny model and patch its approved digest only within this test.

    Production always uses the code-pinned reviewed digest. Tests need neither
    the real model nor external services, and never trust sidecar checksums.
    """
    import hashlib

    import skops.io as sio

    from king_county import artifacts

    data = sio.dumps(tiny_pipeline)
    path = tmp_path / "pipeline.skops"
    path.write_bytes(data)
    monkeypatch.setattr(
        artifacts, "EXPECTED_MODEL_SHA256", hashlib.sha256(data).hexdigest()
    )
    return artifacts.ModelArtifact(path)
