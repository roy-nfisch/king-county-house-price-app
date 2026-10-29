"""Check installed imports and real logging outside the repository folder."""

import os
import subprocess
import sys
from importlib.metadata import distribution

import pytest

pytestmark = pytest.mark.integration

# Cold imports on shared CI runners can take longer than local imports.
IMPORT_TIMEOUT_SECONDS = 60


@pytest.mark.parametrize(
    ("field", "expected"),
    [("License-Expression", ["MIT"]), ("License-File", ["LICENSE"])],
)
def test_installed_package_declares_license(field, expected):
    """Declare licensing even in editable installs; Docker checks shipped text."""
    package = distribution("mle-refactoring-project")
    assert package.metadata.get_all(field) == expected


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
        timeout=IMPORT_TIMEOUT_SECONDS,
        check=True,
    )

    assert "INFO king_county Foundation ready" in result.stderr
    assert "Hidden debug message" not in result.stderr
    assert result.stdout == ""


def test_api_package_imports_outside_repository(tmp_path):
    """The installed API package needs neither the checkout nor a model to import."""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from api.main import create_app; print(create_app.__module__)",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=IMPORT_TIMEOUT_SECONDS,
        check=True,
    )
    assert result.stdout.strip() == "api.main"
