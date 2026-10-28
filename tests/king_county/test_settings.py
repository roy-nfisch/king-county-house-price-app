"""Unit tests for explicit, environment-based configuration validation."""

import pytest
from pydantic import ValidationError

from king_county.settings import AppSettings

pytestmark = pytest.mark.unit


def test_default_log_level(monkeypatch):
    """Use INFO when no environment override is supplied."""
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    assert AppSettings.from_environment().log_level == "INFO"


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_environment_log_levels(monkeypatch, level):
    """Accept each documented logging level from the environment."""
    monkeypatch.setenv("LOG_LEVEL", level)

    assert AppSettings.from_environment().log_level == level


@pytest.mark.parametrize("level", ["verbose", "debug", "", "20"])
def test_invalid_log_level(monkeypatch, level):
    """Reject invalid configuration instead of silently using a default."""
    monkeypatch.setenv("LOG_LEVEL", level)

    with pytest.raises(ValidationError, match="log_level"):
        AppSettings.from_environment()


def test_unknown_setting_is_rejected():
    """Catch misspelled keys when settings are built from a dictionary."""
    with pytest.raises(ValidationError, match="log_levle"):
        AppSettings.model_validate({"log_levle": "DEBUG"})
