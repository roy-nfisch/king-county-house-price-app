"""Shared baseline fixtures; reuse the supplied CSV instead of duplicating data."""

import json
from pathlib import Path

import pandas as pd
import pytest

from king_county.cleaning import HouseCleaner

ROOT = Path(__file__).resolve().parents[1]


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
