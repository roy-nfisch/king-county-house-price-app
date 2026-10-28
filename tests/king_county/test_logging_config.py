"""Unit tests for logging setup without changing pytest's own handlers."""

from unittest.mock import patch

import pytest

from king_county.logging_config import configure_logging
from king_county.settings import AppSettings

pytestmark = pytest.mark.unit


def test_logging_uses_validated_settings():
    """Pass the chosen level and a readable format to Python logging."""
    settings = AppSettings(log_level="DEBUG")

    with patch("king_county.logging_config.logging.basicConfig") as basic_config:
        configure_logging(settings)

    basic_config.assert_called_once_with(
        level="DEBUG",
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
