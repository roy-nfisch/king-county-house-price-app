"""Check installed imports and real logging outside the repository folder."""

import os
import subprocess
import sys


def test_installed_package_logs_outside_repository(tmp_path):
    """Import the installed package and exercise settings plus console logging."""
    script = """
import logging
from king_county.logging_config import configure_logging
from king_county.settings import AppSettings

configure_logging(AppSettings.from_environment())
logging.getLogger("king_county").info("Foundation ready")
logging.getLogger("king_county").debug("Hidden debug message")
"""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["LOG_LEVEL"] = "INFO"

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )

    assert "INFO king_county Foundation ready" in result.stderr
    assert "Hidden debug message" not in result.stderr
    assert result.stdout == ""
