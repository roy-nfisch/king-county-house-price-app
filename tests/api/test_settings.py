"""API settings select a model path but cannot override the approved checksum."""

from pathlib import Path

import pytest

from api.settings import ApiSettings
from king_county.artifacts import DEFAULT_MODEL_PATH

pytestmark = pytest.mark.unit


def test_default_model_path(monkeypatch):
    """Use the reviewed export unless its local location is explicitly changed."""
    monkeypatch.delenv("MODEL_PATH", raising=False)
    assert ApiSettings.from_environment().model_path == DEFAULT_MODEL_PATH


def test_model_path_can_be_relocated(monkeypatch):
    """Only location changes through the environment, not the artifact identity."""
    monkeypatch.setenv("MODEL_PATH", "/tmp/approved.skops")
    assert ApiSettings.from_environment().model_path == Path("/tmp/approved.skops")
